from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import statistics
import zipfile
from pathlib import Path
from typing import Any, Iterable

EXPERIMENT_ID = "HIXTON-V1-TRADE-DIAGNOSTICS"
STRATEGY_SHA256 = "d43da032ad8aac714da60027702f84b584fc9cbc7e84038ca06847b5c2342290"
PAIRS = (
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT",
    "DOGE/USDT", "LINK/USDT", "TRX/USDT", "LTC/USDT", "BCH/USDT",
)
TAG_MAP = {
    "x": "breakout_excess_atr", "dv": "price_minus_vidya_atr",
    "cb": "candle_body_atr", "cr": "candle_range_atr",
    "av": "atr_vs_median_96", "vr": "volume_ratio_20",
    "r": "rsi14", "a": "adx14", "m": "macd_hist_atr",
    "s1": "vidya_slope_1_atr", "s4": "vidya_slope_4_atr",
    "rb": "prev_phase_bars", "rr": "prev_phase_range_atr",
    "rn": "prev_phase_net_atr", "re": "red_rebound_atr",
    "pg": "prev_green_range_atr", "t1": "trend_up_1h",
    "r1": "rsi14_1h", "a1": "adx14_1h",
    "sv1": "vidya_slope_1_atr_1h", "t4": "trend_up_4h",
    "r4": "rsi14_4h", "a4": "adx14_4h",
    "sv4": "vidya_slope_1_atr_4h",
}
BOOL_FEATURES = {"trend_up_1h", "trend_up_4h"}
CONTINUOUS_FEATURES = tuple(v for v in TAG_MAP.values() if v not in BOOL_FEATURES)


def fnum(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.nan
    return number if math.isfinite(number) else math.nan


def parse_enter_tag(tag: str | None) -> dict[str, float]:
    values = {name: math.nan for name in TAG_MAP.values()}
    if not tag or not tag.startswith("v1d|"):
        return values
    for token in tag.split("|")[1:]:
        if "=" not in token:
            continue
        key, raw = token.split("=", 1)
        if key in TAG_MAP:
            values[TAG_MAP[key]] = fnum(raw)
    return values


def break_even_mfe_ratio(fee_open: float, fee_close: float) -> float:
    if fee_close >= 1.0:
        return math.inf
    return (1.0 + fee_open) / (1.0 - fee_close) - 1.0


def quantile(values: Iterable[float], q: float) -> float:
    data = sorted(v for v in values if math.isfinite(v))
    if not data:
        return math.nan
    if len(data) == 1:
        return data[0]
    pos = (len(data) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return data[lo]
    frac = pos - lo
    return data[lo] * (1.0 - frac) + data[hi] * frac


def profit_factor(rows: Iterable[dict[str, Any]]) -> float:
    wins = sum(float(r["profit_abs"]) for r in rows if float(r["profit_abs"]) > 0)
    losses = sum(-float(r["profit_abs"]) for r in rows if float(r["profit_abs"]) < 0)
    if losses == 0:
        return math.inf if wins > 0 else math.nan
    return wins / losses


def load_diagnostic_trades(results_root: Path) -> list[dict[str, Any]]:
    by_pair: dict[str, list[dict[str, Any]]] = {}
    for experiment_path in results_root.glob("*/experiment-result.json"):
        experiment_result = json.loads(experiment_path.read_text(encoding="utf-8"))
        experiment = experiment_result.get("experiment") or {}
        identity = experiment_result.get("test_identity") or {}
        pair = str(experiment_result.get("pair") or "")
        if experiment.get("experiment_id") != EXPERIMENT_ID:
            continue
        if identity.get("strategy_sha256") != STRATEGY_SHA256:
            continue
        if pair not in PAIRS:
            continue
        zips = list(experiment_path.parent.glob("backtest-result-*.zip"))
        if len(zips) != 1:
            raise RuntimeError(f"{experiment_path.parent.name}: expected one result zip, got {len(zips)}")
        with zipfile.ZipFile(zips[0]) as archive:
            result_names = [
                n for n in archive.namelist()
                if n.endswith(".json") and "_config" not in n and not n.startswith("audit/")
            ]
            if len(result_names) != 1:
                raise RuntimeError(f"{zips[0].name}: ambiguous result JSON: {result_names}")
            payload = json.loads(archive.read(result_names[0]))
        strategy = payload.get("strategy", {}).get("CompressionBreakout250")
        if not isinstance(strategy, dict) or not isinstance(strategy.get("trades"), list):
            raise RuntimeError(f"{zips[0].name}: missing strategy trades")
        by_pair[pair] = strategy["trades"]
    missing = [pair for pair in PAIRS if pair not in by_pair]
    if missing:
        raise RuntimeError("Missing V1 diagnostic results: " + ", ".join(missing))

    rows: list[dict[str, Any]] = []
    for pair in PAIRS:
        pair_rows: list[dict[str, Any]] = []
        for trade_index, trade in enumerate(by_pair[pair]):
            open_rate = float(trade["open_rate"])
            close_rate = float(trade["close_rate"])
            max_rate = float(trade["max_rate"])
            min_rate = float(trade["min_rate"])
            amount = float(trade["amount"])
            fee_open = float(trade.get("fee_open") or 0.0)
            fee_close = float(trade.get("fee_close") or 0.0)
            profit_abs = float(trade["profit_abs"])
            mfe = max_rate / open_rate - 1.0
            row: dict[str, Any] = {
                "pair": pair,
                "coin": pair.split("/", 1)[0],
                "trade_index": trade_index,
                "open_date": trade["open_date"],
                "close_date": trade["close_date"],
                "open_timestamp": int(trade["open_timestamp"]),
                "close_timestamp": int(trade["close_timestamp"]),
                "open_rate": open_rate,
                "close_rate": close_rate,
                "min_rate": min_rate,
                "max_rate": max_rate,
                "amount": amount,
                "stake_amount": float(trade["stake_amount"]),
                "fee_open": fee_open,
                "fee_close": fee_close,
                "gross_abs": amount * (close_rate - open_rate),
                "fee_abs": amount * open_rate * fee_open + amount * close_rate * fee_close,
                "profit_abs": profit_abs,
                "profit_ratio": float(trade["profit_ratio"]),
                "mfe_ratio": mfe,
                "mae_ratio": min_rate / open_rate - 1.0,
                "break_even_mfe_ratio": break_even_mfe_ratio(fee_open, fee_close),
                "giveback_from_mfe_ratio": mfe - float(trade["profit_ratio"]),
                "trade_duration_min": int(trade["trade_duration"]),
                "enter_tag": trade.get("enter_tag") or "",
                "entry_year": int(str(trade["open_date"])[:4]),
            }
            row.update(parse_enter_tag(trade.get("enter_tag")))
            pair_rows.append(row)

        positive = [float(r["profit_abs"]) for r in pair_rows if float(r["profit_abs"]) > 0]
        q90, q95 = quantile(positive, 0.90), quantile(positive, 0.95)
        for row in pair_rows:
            pnl = float(row["profit_abs"])
            if pnl <= 0:
                row["outcome_class"] = (
                    "FAILED_START"
                    if float(row["mfe_ratio"]) < float(row["break_even_mfe_ratio"])
                    else "PROFITABLE_THEN_LOST"
                )
                row["one_percent_then_lost"] = int(float(row["mfe_ratio"]) >= 0.01)
                row["winner_class"] = ""
                row["is_fat_tail"] = 0
            else:
                row["outcome_class"] = "WINNER"
                row["one_percent_then_lost"] = 0
                row["winner_class"] = (
                    "FAT_TAIL_WINNER" if pnl >= q95
                    else "LARGE_WINNER" if pnl >= q90
                    else "NORMAL_WINNER"
                )
                row["is_fat_tail"] = int(row["winner_class"] == "FAT_TAIL_WINNER")
        rows.extend(pair_rows)
    return rows


def metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    losers = [r for r in rows if float(r["profit_abs"]) < 0]
    winners = [r for r in rows if float(r["profit_abs"]) > 0]
    return {
        "trades": len(rows),
        "net_pnl": sum(float(r["profit_abs"]) for r in rows),
        "gross_pnl": sum(float(r["gross_abs"]) for r in rows),
        "fees": sum(float(r["fee_abs"]) for r in rows),
        "loss_damage": sum(-float(r["profit_abs"]) for r in losers),
        "winner_profit": sum(float(r["profit_abs"]) for r in winners),
        "fat_tail_count": sum(int(r["is_fat_tail"]) for r in rows),
        "profit_factor": profit_factor(rows),
    }


def chronological_segments(rows: list[dict[str, Any]]) -> dict[int, str]:
    ordered = sorted(rows, key=lambda r: int(r["open_timestamp"]))
    result: dict[int, str] = {}
    for index, row in enumerate(ordered):
        fraction = (index + 0.5) / max(1, len(ordered))
        result[id(row)] = "discovery" if fraction < 0.60 else "validation" if fraction < 0.80 else "holdout"
    return result


def screen_entry_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pair in PAIRS:
        pair_rows = [r for r in rows if r["pair"] == pair]
        segment_map = chronological_segments(pair_rows)
        for row in pair_rows:
            row["segment"] = segment_map[id(row)]
        discovery = [r for r in pair_rows if r["segment"] == "discovery"]

        rules: list[tuple[str, str, float]] = []
        for feature in CONTINUOUS_FEATURES:
            values = [float(r[feature]) for r in discovery if math.isfinite(float(r[feature]))]
            if len(values) >= 50:
                rules.extend(((feature, "low20", quantile(values, 0.20)), (feature, "high20", quantile(values, 0.80))))
        for feature in BOOL_FEATURES:
            rules.extend(((feature, "equals", 0.0), (feature, "equals", 1.0)))

        for feature, direction, threshold in rules:
            def remove(row: dict[str, Any]) -> bool:
                value = float(row[feature])
                if not math.isfinite(value):
                    return False
                if direction == "low20":
                    return value <= threshold
                if direction == "high20":
                    return value >= threshold
                return int(round(value)) == int(threshold)

            record: dict[str, Any] = {
                "pair": pair, "feature": feature, "direction": direction,
                "threshold_from_discovery": threshold,
            }
            segment_stats: dict[str, dict[str, float]] = {}
            for segment in ("discovery", "validation", "holdout"):
                universe = [r for r in pair_rows if r["segment"] == segment]
                removed = [r for r in universe if remove(r)]
                kept = [r for r in universe if not remove(r)]
                u, rm, kp = metrics(universe), metrics(removed), metrics(kept)
                trade_share = rm["trades"] / u["trades"] if u["trades"] else math.nan
                loss_share = rm["loss_damage"] / u["loss_damage"] if u["loss_damage"] else math.nan
                winner_share = rm["winner_profit"] / u["winner_profit"] if u["winner_profit"] else math.nan
                fat_share = rm["fat_tail_count"] / u["fat_tail_count"] if u["fat_tail_count"] else math.nan
                s = {
                    "removed_trades": rm["trades"], "removed_net_pnl": rm["net_pnl"],
                    "trade_share": trade_share, "loss_damage_share": loss_share,
                    "winner_profit_share": winner_share, "fat_tail_removed_share": fat_share,
                    "damage_efficiency": loss_share / trade_share if trade_share else math.nan,
                    "winner_cost_efficiency": winner_share / trade_share if trade_share else math.nan,
                    "universe_pf": u["profit_factor"], "kept_pf": kp["profit_factor"],
                }
                segment_stats[segment] = s
                for key, value in s.items():
                    record[f"{segment}_{key}"] = value

            d, v, h = segment_stats["discovery"], segment_stats["validation"], segment_stats["holdout"]
            discovery_ok = (
                d["removed_trades"] >= 15 and d["removed_net_pnl"] < 0
                and d["trade_share"] <= 0.35 and d["damage_efficiency"] >= 1.35
                and (math.isnan(d["winner_cost_efficiency"]) or d["winner_cost_efficiency"] <= 0.85)
                and (math.isnan(d["fat_tail_removed_share"]) or d["fat_tail_removed_share"] <= 0.15)
                and d["kept_pf"] > d["universe_pf"]
            )
            validation_ok = (
                v["removed_trades"] >= 5 and v["removed_net_pnl"] < 0
                and v["damage_efficiency"] >= 1.10
                and (math.isnan(v["fat_tail_removed_share"]) or v["fat_tail_removed_share"] <= 0.25)
                and v["kept_pf"] >= v["universe_pf"]
            )
            record["candidate_selected_without_holdout"] = int(discovery_ok and validation_ok)
            record["holdout_supports_candidate"] = int(
                h["removed_trades"] > 0 and h["removed_net_pnl"] < 0
                and h["damage_efficiency"] >= 1.0 and h["kept_pf"] >= h["universe_pf"]
            )
            output.append(record)
    return sorted(output, key=lambda r: (-int(r["candidate_selected_without_holdout"]), -fnum(r["validation_damage_efficiency"])))


def build_coin_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for pair in PAIRS:
        group = [r for r in rows if r["pair"] == pair]
        base = metrics(group)
        failed = [r for r in group if r["outcome_class"] == "FAILED_START"]
        dead = [r for r in group if r["outcome_class"] == "PROFITABLE_THEN_LOST"]
        output.append({
            "pair": pair, **base,
            "failed_start_count": len(failed),
            "failed_start_loss_damage": sum(-float(r["profit_abs"]) for r in failed),
            "profitable_then_lost_count": len(dead),
            "profitable_then_lost_loss_damage": sum(-float(r["profit_abs"]) for r in dead),
            "one_percent_then_lost_count": sum(int(r["one_percent_then_lost"]) for r in dead),
            "theoretical_pnl_without_failed_starts": base["net_pnl"] + sum(-float(r["profit_abs"]) for r in failed),
        })
    return output


def build_dead_trend_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for pair in PAIRS:
        dead = [r for r in rows if r["pair"] == pair and r["outcome_class"] == "PROFITABLE_THEN_LOST"]
        output.append({
            "pair": pair,
            "profitable_then_lost_trades": len(dead),
            "one_percent_then_lost_trades": sum(int(r["one_percent_then_lost"]) for r in dead),
            "loss_damage": sum(-float(r["profit_abs"]) for r in dead),
            "median_mfe_pct": 100.0 * statistics.median(float(r["mfe_ratio"]) for r in dead) if dead else math.nan,
            "median_giveback_pct": 100.0 * statistics.median(float(r["giveback_from_mfe_ratio"]) for r in dead) if dead else math.nan,
        })
    return sorted(output, key=lambda r: -float(r["loss_damage"]))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, summary: list[dict[str, Any]], candidates: list[dict[str, Any]], queue: list[dict[str, Any]]) -> None:
    selected = [r for r in candidates if int(r["candidate_selected_without_holdout"]) == 1]
    lines = [
        "# Hixton V1 – Causal Analysis Screen", "",
        f"Experiment: `{EXPERIMENT_ID}`", f"Strategy SHA256: `{STRATEGY_SHA256}`", "",
        "## Methodik", "",
        "- Exakte Fee-Break-even-MFE trennt FAILED_START von PROFITABLE_THEN_LOST.",
        "- MFE/MAE sind Outcomes, keine Entry-Features.",
        "- Pro Coin chronologisch 60 % Discovery / 20 % Validation / 20 % Holdout.",
        "- Entry-Screen testet nur vorab definierte q20/q80-Tails und boolesche 1h/4h-Zustände.",
        "- Holdout beeinflusst die Kandidatenauswahl nicht.",
        "- Kein Dead-Trend-Exit wird ohne zeitliche Candle-Sequenz konstruiert.", "",
        "## Coin-Summary", "",
        "| Pair | Trades | Net P/L | PF | Failed starts | Dead trends | Failed damage | Dead-trend damage |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summary:
        lines.append(
            f"| {s['pair']} | {s['trades']} | {s['net_pnl']:.2f} | {s['profit_factor']:.3f} | "
            f"{s['failed_start_count']} | {s['profitable_then_lost_count']} | "
            f"{s['failed_start_loss_damage']:.2f} | {s['profitable_then_lost_loss_damage']:.2f} |"
        )
    lines.extend(["", "## Entry-Screen", ""])
    if not selected:
        lines.append("**Kein einfacher Einzelfeature-Entryfilter erfüllt gleichzeitig die konservativen Discovery- und Validation-Kriterien.**")
        lines.append("Das ist ein valider negativer Befund; Schwellen dürfen jetzt nicht nachoptimiert werden.")
    else:
        for row in selected:
            lines.append(f"- {row['pair']}: {row['feature']} {row['direction']} {row['threshold_from_discovery']:.6g}")
    lines.extend(["", "## Dead-Trend-Priorität", "",
                  "| Pair | Dead trends | davon >=1 % MFE | Verlustschaden | Median MFE | Median Giveback |",
                  "|---|---:|---:|---:|---:|---:|"])
    for row in queue:
        lines.append(
            f"| {row['pair']} | {row['profitable_then_lost_trades']} | {row['one_percent_then_lost_trades']} | "
            f"{row['loss_damage']:.2f} | {row['median_mfe_pct']:.2f} % | {row['median_giveback_pct']:.2f} % |"
        )
    lines.extend(["", "## Nächster Schritt vor V6", "",
                  "Die tatsächliche 1m/15m-Candle-Sequenz von PROFITABLE_THEN_LOST und Fat-Tail-Gewinnern muss rekonstruiert werden. Erst danach darf ein Dead-Trend-Exit präregistriert und einmalig auf Holdout geprüft werden.", "",
                  "**Kein V6-Tradingcode allein aus diesem Entry-Screen.**", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze completed Hixton V1 diagnostic trades without rerunning Freqtrade.")
    parser.add_argument("--results-root", type=Path, default=Path("runtime/user_data/backtest_results/hixton"))
    parser.add_argument("--output-dir", type=Path, default=Path("research/reports/hixton_v1_causal"))
    args = parser.parse_args()

    rows = load_diagnostic_trades(args.results_root)
    summary = build_coin_summary(rows)
    candidates = screen_entry_features(rows)
    queue = build_dead_trend_queue(rows)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "all_v1_trade_features.csv", rows)
    write_csv(out / "coin_summary.csv", summary)
    write_csv(out / "entry_feature_tail_screen.csv", candidates)
    write_csv(out / "entry_filter_candidates.csv", [r for r in candidates if int(r["candidate_selected_without_holdout"]) == 1])
    write_csv(out / "dead_trend_research_queue.csv", queue)
    write_report(out / "V1_CAUSAL_ANALYSIS.md", summary, candidates, queue)
    (out / "analysis_manifest.json").write_text(json.dumps({
        "experiment_id": EXPERIMENT_ID,
        "strategy_sha256": STRATEGY_SHA256,
        "trades": len(rows),
        "candidate_count_before_holdout": sum(int(r["candidate_selected_without_holdout"]) for r in candidates),
        "split": "chronological 60/20/20 per coin",
        "dead_trend_exit": "not simulated without candle path",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Analyzed {len(rows)} trades; output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
