"""Behavior-preserving paper decision capture for later replay parity checks.

All wrappers call the original V8 callbacks exactly once and return their exact
result. Telemetry failures are swallowed so observability can never place or
block an order. No credentials or full config are written.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import types
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_WRITE_LOCK = threading.Lock()

_SAFE_CONFIG_FIELDS = (
    "dry_run",
    "trading_mode",
    "margin_mode",
    "stake_currency",
    "stake_amount",
    "dry_run_wallet",
    "max_open_trades",
    "timeframe",
    "fee",
    "order_types",
    "order_time_in_force",
    "unfilledtimeout",
)

_RISK_CONFIG_FIELDS = (
    "stake_currency",
    "stake_amount",
    "dry_run_wallet",
    "max_open_trades",
    "trading_mode",
    "margin_mode",
)


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _iso(value: Any) -> str | None:
    try:
        stamp = value.to_pydatetime() if hasattr(value, "to_pydatetime") else value
        if not isinstance(stamp, datetime):
            return None
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)
        return stamp.astimezone(UTC).isoformat()
    except Exception:
        return None


def _candle_close_iso(value: Any, *, minutes: int = 15) -> str | None:
    try:
        stamp = value.to_pydatetime() if hasattr(value, "to_pydatetime") else value
        if not isinstance(stamp, datetime):
            return None
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)
        return (stamp.astimezone(UTC) + timedelta(minutes=minutes)).isoformat()
    except Exception:
        return None


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return str(value)


def _hash_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        _jsonable(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_config_fingerprint(config: dict[str, Any]) -> str:
    payload = {
        name: config.get(name) for name in _SAFE_CONFIG_FIELDS if name in config
    }
    exchange = config.get("exchange")
    if isinstance(exchange, dict):
        payload["exchange_name"] = exchange.get("name")
        payload["pair_whitelist"] = exchange.get("pair_whitelist")
    return _hash_payload(payload)


def _risk_policy_fingerprint(config: dict[str, Any], strategy_sha256: str) -> str:
    payload = {
        "policy_version": "v8-paper-risk-observation-v1",
        "strategy_sha256_raw": strategy_sha256,
        **{
            name: config.get(name)
            for name in _RISK_CONFIG_FIELDS
            if name in config
        },
    }
    return _hash_payload(payload)


def _git_sha() -> str | None:
    try:
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
        value = result.stdout.strip().lower()
        is_hex_sha = len(value) == 40 and all(
            character in "0123456789abcdef" for character in value
        )
        if result.returncode == 0 and is_hex_sha:
            return value
    except Exception:
        return None
    return None


class PaperDecisionRecorder:
    def __init__(
        self, config: dict[str, Any], strategy_sha256: str, strategy_name: str
    ) -> None:
        root = Path(str(config.get("user_data_dir", "user_data"))) / "paper_telemetry"
        root.mkdir(parents=True, exist_ok=True)
        session = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.run_id = f"paper-{session}-{uuid.uuid4().hex[:12]}"
        self.path = root / (
            f"paper-decisions-{self.run_id}-{strategy_sha256[:12]}.jsonl"
        )
        self.strategy_sha256 = strategy_sha256
        self.strategy_name = strategy_name
        configured_experiment = os.environ.get(
            "AI_TRADING_EXPERIMENT_ID", "V8-PAPER-FORWARD"
        ).strip()
        self.experiment_id = configured_experiment or "V8-PAPER-FORWARD"
        self.git_sha = _git_sha()
        self.config_hash = _safe_config_fingerprint(config)
        self.risk_policy_hash = _risk_policy_fingerprint(config, strategy_sha256)
        self._last_signal_candle: dict[tuple[str, str], str | None] = {}

    def write(self, payload: dict[str, Any]) -> None:
        try:
            record = {
                "recorded_at_utc": datetime.now(UTC).isoformat(),
                "experiment_id": self.experiment_id,
                "run_id": self.run_id,
                "git_sha": self.git_sha,
                "strategy_name": self.strategy_name,
                "strategy_sha256_raw": self.strategy_sha256,
                "config_hash": self.config_hash,
                "risk_policy_hash": self.risk_policy_hash,
                "data_manifest_hash": None,
                "mode": "paper",
                **payload,
            }
            raw = json.dumps(record, sort_keys=True, ensure_ascii=False)
            with _WRITE_LOCK, self.path.open(
                "a", encoding="utf-8", newline="\n"
            ) as stream:
                stream.write(raw + "\n")
        except Exception:
            return

    def signal_row(self, *, kind: str, pair: str, frame: Any) -> None:
        try:
            if frame is None or frame.empty:
                return
            row = frame.iloc[-1]
            candle_open = _iso(row.get("date"))
            key = (kind, pair)
            if self._last_signal_candle.get(key) == candle_open:
                return
            self._last_signal_candle[key] = candle_open
            fields = (
                "fresh_breakout_4h",
                "donchian_entry_4h",
                "atr_4h",
                "adx_4h",
                "rsi_4h",
                "momentum_30d_4h",
                "ema_fast_rising_4h",
                "ema_exec",
                "ema_fast",
                "atr_pct",
                "rsi",
                "volume",
                "volume_ratio",
                "btc_close_4h",
                "btc_ema_fast_4h",
                "btc_ema_slow_4h",
                "btc_ema_fast_rising_4h",
                "btc_momentum_30d_4h",
                "close_4h",
            )
            features = {
                name: number
                for name in fields
                if (number := _safe_float(row.get(name))) is not None
            }
            breakout = features.get("donchian_entry_4h")
            atr_4h = features.get("atr_4h")
            close_4h = features.get("close_4h")
            if (
                breakout is not None
                and atr_4h is not None
                and atr_4h > 0
                and close_4h is not None
            ):
                features["breakout_distance_atr"] = (close_4h - breakout) / atr_4h
            btc_values = [
                features.get("btc_close_4h"),
                features.get("btc_ema_fast_4h"),
                features.get("btc_ema_slow_4h"),
                features.get("btc_ema_fast_rising_4h"),
                features.get("btc_momentum_30d_4h"),
            ]
            if all(value is not None for value in btc_values):
                btc_close, btc_fast, btc_slow, btc_rising, btc_momentum = btc_values
                features["btc_regime_up"] = float(
                    btc_close > btc_fast > btc_slow
                    and btc_rising > 0
                    and btc_momentum > 0
                )
            enter_long = bool(row.get("enter_long", 0) == 1)
            exit_long = bool(row.get("exit_long", 0) == 1)
            self.write(
                {
                    "type": "strategy_signal_decision",
                    "kind": kind,
                    "pair": pair,
                    "candle_open_utc": candle_open,
                    "candle_close_utc": _candle_close_iso(row.get("date")),
                    "reference_price": _safe_float(row.get("close")),
                    "entry_candidate": enter_long,
                    "enter_long": enter_long,
                    "exit_long": exit_long,
                    "enter_tag": str(row.get("enter_tag")) if enter_long else None,
                    "exit_tag": str(row.get("exit_tag")) if exit_long else None,
                    "features": features,
                }
            )
        except Exception:
            return


def install_paper_strategy_telemetry(instance: Any, strategy_sha256: str) -> None:
    """Instrument one dry-run strategy instance without changing decisions."""
    if os.environ.get("AI_TRADING_PAPER_TELEMETRY", "1").strip().lower() in {
        "0",
        "false",
        "off",
    }:
        return
    if not bool(instance.config.get("dry_run", False)):
        return
    if getattr(instance, "__paper_replay_telemetry_installed__", False):
        return

    recorder = PaperDecisionRecorder(
        instance.config, strategy_sha256, type(instance).__name__
    )
    original_entry = instance.populate_entry_trend
    original_exit = instance.populate_exit_trend
    original_confirm = instance.confirm_trade_entry

    def entry_wrapper(self: Any, dataframe: Any, metadata: dict[str, Any]) -> Any:
        del self
        result = original_entry(dataframe, metadata)
        recorder.signal_row(
            kind="entry", pair=str(metadata.get("pair", "")), frame=result
        )
        return result

    def exit_wrapper(self: Any, dataframe: Any, metadata: dict[str, Any]) -> Any:
        del self
        result = original_exit(dataframe, metadata)
        recorder.signal_row(
            kind="exit", pair=str(metadata.get("pair", "")), frame=result
        )
        return result

    def confirm_wrapper(
        self: Any,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str | None,
        side: str,
        **kwargs: Any,
    ) -> bool:
        del self
        result = bool(
            original_confirm(
                pair=pair,
                order_type=order_type,
                amount=amount,
                rate=rate,
                time_in_force=time_in_force,
                current_time=current_time,
                entry_tag=entry_tag,
                side=side,
                **kwargs,
            )
        )
        recorder.write(
            {
                "type": "runtime_entry_confirmation",
                "pair": pair,
                "time_utc": _iso(current_time),
                "order_type": order_type,
                "time_in_force": time_in_force,
                "side": side,
                "rate": _safe_float(rate),
                "amount": _safe_float(amount),
                "entry_tag": entry_tag,
                "entry_allowed": result,
                "entry_rejection_reason": (
                    None if result else "v8_confirm_trade_entry_rejected"
                ),
                "allowed": result,
            }
        )
        return result

    instance.populate_entry_trend = types.MethodType(entry_wrapper, instance)
    instance.populate_exit_trend = types.MethodType(exit_wrapper, instance)
    instance.confirm_trade_entry = types.MethodType(confirm_wrapper, instance)
    instance.__paper_replay_telemetry_installed__ = True
    recorder.write(
        {
            "type": "paper_telemetry_started",
            "strategy": type(instance).__name__,
            "dry_run": True,
            "timeframe": getattr(instance, "timeframe", None),
        }
    )
