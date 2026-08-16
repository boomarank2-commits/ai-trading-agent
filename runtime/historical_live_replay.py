"""Command-line historical live replay for the frozen V8 testbot.

This runner intentionally does not start Freqtrade's trading loop and never
loads exchange credentials. It loads public local candles, executes the exact
hashed V8 strategy callbacks for signals, then feeds those decisions into a
chronological shared-wallet risk/execution state machine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import uuid
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import pandas as pd

from replay_core import MinuteBar, ReplayEngine, ReplayPolicy, StrategyDecision, final_metrics
from replay_data import build_manifest, feather_path, sha256_file
from replay_telemetry import JsonlReplaySink, finalize_run, write_json_atomic
from v8_replay_adapter import V8ReplayAdapter

RUNTIME_ROOT = Path(__file__).resolve().parent
REPO_ROOT = RUNTIME_ROOT.parent
USER_DATA = RUNTIME_ROOT / "user_data"
DEFAULT_DATA_ROOT = USER_DATA / "data" / "binance"
DEFAULT_OUTPUT_ROOT = USER_DATA / "replay_results"
CONFIG = USER_DATA / "config.json"
STRATEGY = USER_DATA / "strategies" / "CompressionBreakout250.py"
STRATEGY_CLASS = "CompressionBreakout250"
PAIRS = ("BTC/USDT", "ETH/USDT", "SOL/USDT")
WARMUP_DAYS = 75


def _sha256_json(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True, timeout=10
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _parse_time(value: str) -> datetime:
    text = value.strip()
    if len(text) == 10:
        text += "T00:00:00+00:00"
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _latest_common_end(data_root: Path) -> datetime:
    latest: list[datetime] = []
    for pair in PAIRS:
        path = feather_path(data_root, pair, "1m")
        if not path.is_file():
            raise RuntimeError(f"missing 1m data: {path}")
        dates = pd.read_feather(path, columns=["date"])["date"]
        if dates.empty:
            raise RuntimeError(f"empty 1m data: {path}")
        last = pd.to_datetime(dates.iloc[-1], utc=True).to_pydatetime()
        latest.append(last + timedelta(minutes=1))
    return min(latest).astimezone(UTC)


def _resolve_window(args: argparse.Namespace) -> tuple[datetime, datetime]:
    end = _parse_time(args.end) if args.end else _latest_common_end(args.data_root)
    if args.start:
        start = _parse_time(args.start)
    else:
        start = end - timedelta(days=365 * args.years)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    if end <= start:
        raise RuntimeError("replay end must be after start")
    return start, end


def _safe_runtime_config(config: dict[str, Any]) -> dict[str, Any]:
    exchange = config.get("exchange", {}) if isinstance(config.get("exchange"), dict) else {}
    return {
        "strategy": config.get("strategy"),
        "dry_run": config.get("dry_run"),
        "dry_run_wallet": config.get("dry_run_wallet"),
        "available_capital": config.get("available_capital"),
        "stake_currency": config.get("stake_currency"),
        "stake_amount": config.get("stake_amount"),
        "max_open_trades": config.get("max_open_trades"),
        "minimal_roi": config.get("minimal_roi"),
        "stoploss": config.get("stoploss"),
        "trailing_stop": config.get("trailing_stop"),
        "trading_mode": config.get("trading_mode"),
        "margin_mode": config.get("margin_mode"),
        "pair_whitelist": exchange.get("pair_whitelist"),
    }


def _validate_contract(config: dict[str, Any]) -> None:
    safe = _safe_runtime_config(config)
    expected = {
        "strategy": STRATEGY_CLASS,
        "dry_run": True,
        "dry_run_wallet": 250,
        "available_capital": 250,
        "stake_currency": "USDT",
        "stake_amount": 80,
        "max_open_trades": 3,
        "minimal_roi": {"0": 0.50},
        "stoploss": -0.055,
        "trailing_stop": False,
        "trading_mode": "spot",
        "margin_mode": "",
        "pair_whitelist": list(PAIRS),
    }
    if safe != expected:
        raise RuntimeError(
            "replay safety contract mismatch; refusing run:\n"
            + json.dumps({"actual": safe, "expected": expected}, indent=2, sort_keys=True)
        )


def _load_frame(path: Path, start: datetime, end: datetime) -> pd.DataFrame:
    frame = pd.read_feather(path)
    frame["date"] = pd.to_datetime(frame["date"], utc=True, errors="raise")
    return frame.loc[(frame["date"] >= start) & (frame["date"] < end)].copy()


def _decision_index(
    decisions: list[StrategyDecision],
) -> dict[datetime, list[StrategyDecision]]:
    indexed: dict[datetime, list[StrategyDecision]] = {}
    for decision in decisions:
        indexed.setdefault(decision.known_at, []).append(decision)
    for values in indexed.values():
        values.sort(key=lambda item: PAIRS.index(item.pair))
    return indexed


def _minute_iter(frames: dict[str, pd.DataFrame], start: datetime, end: datetime):
    prepared: dict[str, Any] = {}
    for pair, frame in frames.items():
        selected = frame.loc[(frame["date"] >= start) & (frame["date"] < end)]
        prepared[pair] = selected.itertuples(index=False)
    iterators = [prepared[pair] for pair in PAIRS]
    while True:
        rows = []
        for iterator in iterators:
            try:
                rows.append(next(iterator))
            except StopIteration:
                return
        dates = [pd.Timestamp(row.date).to_pydatetime().astimezone(UTC) for row in rows]
        if len(set(dates)) != 1:
            raise RuntimeError(f"1m pair streams lost timestamp parity: {dates}")
        bars = {
            pair: MinuteBar(
                pair=pair,
                open_time=dates[index],
                open=float(rows[index].open),
                high=float(rows[index].high),
                low=float(rows[index].low),
                close=float(rows[index].close),
                volume=float(rows[index].volume),
            )
            for index, pair in enumerate(PAIRS)
        }
        yield dates[0], bars


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Strict historical live replay for frozen V8"
    )
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--years", type=int, choices=[1, 3, 4, 6], default=6)
    parser.add_argument("--start", help="UTC inclusive, YYYY-MM-DD or ISO timestamp")
    parser.add_argument("--end", help="UTC exclusive, YYYY-MM-DD or ISO timestamp")
    parser.add_argument("--fee", type=float, default=0.002, help="fee per side")
    parser.add_argument("--slippage-bps", type=float, default=0.0)
    parser.add_argument("--checkpoint-every-days", type=int, default=7)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--run-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    _validate_contract(config)
    start, end = _resolve_window(args)
    warmup_start = start - timedelta(days=WARMUP_DAYS)

    data_manifest = build_manifest(
        args.data_root, start=warmup_start, end=end, pairs=PAIRS
    )
    data_manifest_hash = _sha256_json(data_manifest)
    strategy_hash = sha256_file(STRATEGY)
    config_hash = sha256_file(CONFIG)
    safe_config = _safe_runtime_config(config)
    policy = ReplayPolicy(
        start_capital=250.0,
        stake_amount=80.0,
        max_total_exposure=240.0,
        max_open_positions=3,
        max_daily_loss=10.0,
        fee_per_side=args.fee,
        slippage_bps=args.slippage_bps,
    )
    run_id = args.run_id or (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )
    run_dir = args.output_root / run_id
    if run_dir.exists():
        raise RuntimeError(f"run directory already exists (immutable run id): {run_dir}")
    sink = JsonlReplaySink(run_dir)

    adapter = V8ReplayAdapter(
        strategy_source=STRATEGY,
        strategy_sha256=strategy_hash,
        strategy_class=STRATEGY_CLASS,
        config=config,
    )
    if args.resume:
        engine = ReplayEngine.from_checkpoint(
            args.resume, policy=policy, sink=sink, custom_exit=adapter.custom_exit
        )
        replay_start = max(start, engine.state.now)
    else:
        engine = ReplayEngine(
            start_time=start, policy=policy, sink=sink, custom_exit=adapter.custom_exit
        )
        replay_start = start

    btc_4h = _load_frame(
        feather_path(args.data_root, "BTC/USDT", "4h"), warmup_start, end
    )
    decisions: list[StrategyDecision] = []
    minute_frames: dict[str, pd.DataFrame] = {}
    for pair in PAIRS:
        frame15 = _load_frame(
            feather_path(args.data_root, pair, "15m"), warmup_start, end
        )
        frame1h = _load_frame(
            feather_path(args.data_root, pair, "1h"), warmup_start, end
        )
        frame4h = _load_frame(
            feather_path(args.data_root, pair, "4h"), warmup_start, end
        )
        decisions.extend(
            adapter.decisions(
                pair=pair,
                candles_15m=frame15,
                candles_1h=frame1h,
                candles_4h=frame4h,
                btc_4h=btc_4h,
                decision_start=replay_start,
                decision_end=end,
            )
        )
        minute_frames[pair] = _load_frame(
            feather_path(args.data_root, pair, "1m"), replay_start, end
        )
    indexed = _decision_index(decisions)

    manifest = {
        "schema": 1,
        "run_id": run_id,
        "mode": "RETROSPECTIVE_FULL_SYSTEM_REPLAY",
        "warning": "retrospective stress test; not an out-of-sample or profit guarantee",
        "start_utc": start.isoformat(),
        "end_utc_exclusive": end.isoformat(),
        "replay_started_from_utc": replay_start.isoformat(),
        "warmup_start_utc": warmup_start.isoformat(),
        "git_commit_sha": _git_sha(),
        "strategy_name": STRATEGY_CLASS,
        "strategy_sha256_raw": strategy_hash,
        "config_sha256": config_hash,
        "safe_config": safe_config,
        "risk_policy": asdict(policy),
        "risk_policy_hash": _sha256_json(asdict(policy)),
        "data_manifest_hash": data_manifest_hash,
        "data_manifest": data_manifest,
        "python_version": platform.python_version(),
        "freqtrade_version": _package_version("freqtrade"),
        "seed": 0,
        "fee_per_side": args.fee,
        "slippage_bps": args.slippage_bps,
        "signal_source": "exact frozen strategy callbacks; no second strategy formula",
        "execution_note": (
            "signals become actionable only after 15m close; limit entry/exit can fill "
            "no earlier than the next 1m bar; adverse stop is evaluated before ROI within "
            "the same 1m bar"
        ),
    }
    write_json_atomic(run_dir / "data_manifest.json", data_manifest)
    write_json_atomic(run_dir / "manifest.partial.json", manifest)

    checkpoint_days = max(1, int(args.checkpoint_every_days))
    next_checkpoint = replay_start + timedelta(days=checkpoint_days)
    processed_minutes = 0
    try:
        for minute_open, bars in _minute_iter(minute_frames, replay_start, end):
            for decision in indexed.get(minute_open, []):
                engine.submit_decision(decision)
            engine.on_minute(bars)
            processed_minutes += 1
            if engine.state.now >= next_checkpoint:
                engine.save_checkpoint(run_dir / "checkpoint.json")
                next_checkpoint += timedelta(days=checkpoint_days)
    except BaseException as exc:
        sink.error(
            {
                "time": engine.state.now.isoformat(),
                "type": type(exc).__name__,
                "message": str(exc),
            }
        )
        engine.save_checkpoint(run_dir / "checkpoint.failed.json")
        raise

    manifest["processed_minutes"] = processed_minutes
    manifest["decision_rows"] = len(decisions)
    manifest["final_checkpoint_hash"] = engine.checkpoint_hash()
    engine.save_checkpoint(run_dir / "checkpoint.final.json")
    finalize_run(run_dir, engine, manifest)
    (run_dir / "manifest.partial.json").unlink(missing_ok=True)
    print(
        json.dumps(
            {"run_dir": str(run_dir), "metrics": final_metrics(engine)}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
