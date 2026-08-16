"""Multiple-testing aware research audit helpers (PBO/DSR-style diagnostics).

These metrics are research gates, not profitability proofs. The module expects
periodic return series for *all* tried variants, including rejected variants.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
from pathlib import Path
from statistics import NormalDist, fmean, pstdev
from typing import Any, Sequence

NORMAL = NormalDist()
EULER_GAMMA = 0.5772156649015329


def _moments(values: Sequence[float]) -> tuple[float, float, float, float]:
    n = len(values)
    if n < 3:
        raise ValueError("at least 3 returns are required")
    mean = fmean(values)
    centered = [x - mean for x in values]
    variance = sum(x * x for x in centered) / n
    if variance <= 0:
        return mean, 0.0, 0.0, 3.0
    std = math.sqrt(variance)
    skew = sum((x / std) ** 3 for x in centered) / n
    kurt = sum((x / std) ** 4 for x in centered) / n
    return mean, std, skew, kurt


def annualized_sharpe(values: Sequence[float], periods_per_year: float = 365.0) -> float:
    mean, std, _, _ = _moments(values)
    return 0.0 if std == 0 else mean / std * math.sqrt(periods_per_year)


def probabilistic_sharpe_probability(
    values: Sequence[float], *, benchmark_sharpe: float, periods_per_year: float = 365.0
) -> float:
    n = len(values)
    sr = annualized_sharpe(values, periods_per_year)
    _, _, skew, kurt = _moments(values)
    scale = math.sqrt(periods_per_year)
    sr_p = sr / scale
    benchmark_p = benchmark_sharpe / scale
    denominator = math.sqrt(
        max(1e-15, 1.0 - skew * sr_p + ((kurt - 1.0) / 4.0) * sr_p * sr_p)
    )
    z = (sr_p - benchmark_p) * math.sqrt(max(1, n - 1)) / denominator
    return NORMAL.cdf(z)


def expected_max_sharpe(sharpes: Sequence[float]) -> float:
    """Expected maximum under multiple trials using Bailey/Lopez de Prado approximation."""
    trials = len(sharpes)
    if trials <= 1:
        return 0.0
    sigma = pstdev(sharpes)
    if sigma == 0:
        return sharpes[0]
    a = NORMAL.inv_cdf(1.0 - 1.0 / trials)
    b = NORMAL.inv_cdf(1.0 - 1.0 / (trials * math.e))
    return sigma * ((1.0 - EULER_GAMMA) * a + EULER_GAMMA * b)


def deflated_sharpe_probability(
    selected_returns: Sequence[float],
    *,
    all_trial_sharpes: Sequence[float],
    periods_per_year: float = 365.0,
) -> dict[str, float]:
    benchmark = expected_max_sharpe(all_trial_sharpes)
    return {
        "selected_sharpe": annualized_sharpe(selected_returns, periods_per_year),
        "multiple_trial_benchmark_sharpe": benchmark,
        "deflated_sharpe_probability": probabilistic_sharpe_probability(
            selected_returns,
            benchmark_sharpe=benchmark,
            periods_per_year=periods_per_year,
        ),
    }


def _sharpe_no_annual(values: Sequence[float]) -> float:
    mean, std, _, _ = _moments(values)
    return 0.0 if std == 0 else mean / std


def pbo_cscv(return_matrix: Sequence[Sequence[float]], partitions: int = 8) -> dict[str, Any]:
    """Estimate Probability of Backtest Overfitting via symmetric CV.

    Rows are chronological periods, columns are tested strategies. The method
    chooses the IS-best strategy for each half-partition split and records its
    relative OOS rank. PBO is the fraction whose OOS rank falls below median.
    """
    rows = [list(map(float, row)) for row in return_matrix]
    if not rows or len(rows) < partitions:
        raise ValueError("not enough rows for requested CSCV partitions")
    width = len(rows[0])
    if width < 2 or any(len(row) != width for row in rows):
        raise ValueError("matrix must have at least two equal-width strategy columns")
    if partitions < 4 or partitions % 2:
        raise ValueError("partitions must be an even integer >= 4")

    cut_points = [round(i * len(rows) / partitions) for i in range(partitions + 1)]
    blocks = [rows[cut_points[i] : cut_points[i + 1]] for i in range(partitions)]
    half = partitions // 2
    logits: list[float] = []
    for chosen in itertools.combinations(range(partitions), half):
        chosen_set = set(chosen)
        if 0 not in chosen_set:
            continue
        insample = [
            row for i, block in enumerate(blocks) if i in chosen_set for row in block
        ]
        outsample = [
            row for i, block in enumerate(blocks) if i not in chosen_set for row in block
        ]
        is_scores = [_sharpe_no_annual([row[j] for row in insample]) for j in range(width)]
        winner = max(range(width), key=is_scores.__getitem__)
        oos_scores = [
            _sharpe_no_annual([row[j] for row in outsample]) for j in range(width)
        ]
        ordered = sorted(range(width), key=oos_scores.__getitem__)
        rank = ordered.index(winner) + 1
        omega = rank / (width + 1.0)
        logits.append(math.log(omega / (1.0 - omega)))
    pbo = (
        sum(1 for value in logits if value <= 0.0) / len(logits)
        if logits
        else math.nan
    )
    return {
        "partitions": partitions,
        "strategy_count": width,
        "period_count": len(rows),
        "split_count": len(logits),
        "pbo": pbo,
        "median_logit": sorted(logits)[len(logits) // 2] if logits else None,
    }


def load_returns_csv(path: Path) -> tuple[list[str], list[list[float]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if len(header) < 3:
            raise ValueError("CSV must have period plus at least two strategy columns")
        names = header[1:]
        matrix = [[float(value) for value in row[1:]] for row in reader if row]
    return names, matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("returns_csv", type=Path)
    parser.add_argument("--selected", required=True)
    parser.add_argument("--partitions", type=int, default=8)
    parser.add_argument("--periods-per-year", type=float, default=365.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    names, matrix = load_returns_csv(args.returns_csv)
    if args.selected not in names:
        raise SystemExit(f"unknown selected strategy: {args.selected}")
    idx = names.index(args.selected)
    columns = [[row[j] for row in matrix] for j in range(len(names))]
    sharpes = [annualized_sharpe(col, args.periods_per_year) for col in columns]
    result = {
        "warning": "research diagnostic only; incomplete trial universes bias these metrics",
        "strategies": names,
        "sharpes": dict(zip(names, sharpes, strict=True)),
        "dsr": deflated_sharpe_probability(
            columns[idx], all_trial_sharpes=sharpes, periods_per_year=args.periods_per_year
        ),
        "pbo": pbo_cscv(matrix, partitions=args.partitions),
    }
    raw = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8", newline="\n")
    print(raw, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
