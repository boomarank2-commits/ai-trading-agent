"""Checkpoint serialization/restart mixin for the V8 replay engine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

from replay_models import (
    ClosedTrade,
    CustomExit,
    PendingOrder,
    Position,
    ReplayPolicy,
    ReplaySink,
    iso,
    utc,
)

CHECKPOINT_SCHEMA = 2
SUPPORTED_CHECKPOINT_SCHEMAS = {1, CHECKPOINT_SCHEMA}


class ReplayCheckpointMixin:
    def checkpoint_payload(self) -> dict[str, Any]:
        def dt(value: datetime | None) -> str | None:
            return None if value is None else iso(value)

        return {
            "schema": CHECKPOINT_SCHEMA,
            "now": dt(self.state.now),
            "cash": self.state.cash,
            "sequence": self.state.sequence,
            "kill_switch": self.state.kill_switch,
            "data_healthy": self.state.data_healthy,
            "last_prices": self.state.last_prices,
            "last_minute_close_time": dt(self.state.last_minute_close_time),
            "last_minute_fingerprint": self.state.last_minute_fingerprint,
            "pair_cooldown_until": {
                pair: dt(value) for pair, value in self.state.pair_cooldown_until.items()
            },
            "stoploss_guard_until": dt(self.state.stoploss_guard_until),
            "maxdd_guard_until": dt(self.state.maxdd_guard_until),
            "positions": [
                {
                    **asdict(position),
                    "opened_at": dt(position.opened_at),
                }
                for position in self.state.positions.values()
            ],
            "orders": [
                {
                    **asdict(order),
                    "requested_at": dt(order.requested_at),
                    "expires_at": dt(order.expires_at),
                    "decision_candle_open": dt(order.decision_candle_open),
                }
                for order in self.state.orders.values()
            ],
            "closed_trades": [
                {
                    **asdict(trade),
                    "opened_at": dt(trade.opened_at),
                    "closed_at": dt(trade.closed_at),
                }
                for trade in self.state.closed_trades
            ],
        }

    def checkpoint_hash(self) -> str:
        raw = json.dumps(
            self.checkpoint_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def save_checkpoint(self, path: Path) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.checkpoint_payload()
        raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(raw)
        tmp.replace(path)
        digest = hashlib.sha256(raw).hexdigest()
        self.sink.event(
            {"time": iso(self.state.now), "type": "checkpoint", "sha256": digest}
        )
        return digest

    @classmethod
    def from_checkpoint(
        cls,
        path: Path,
        *,
        policy: ReplayPolicy | None = None,
        sink: ReplaySink | None = None,
        custom_exit: CustomExit | None = None,
    ) -> Self:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"invalid replay checkpoint: {path}") from exc
        schema = int(payload.get("schema", 0))
        if schema not in SUPPORTED_CHECKPOINT_SCHEMAS:
            raise RuntimeError("unsupported replay checkpoint schema")

        def parsed(value: str | None) -> datetime | None:
            if value is None:
                return None
            return utc(datetime.fromisoformat(value.replace("Z", "+00:00")))

        engine = cls(
            start_time=parsed(payload["now"]) or datetime.now(UTC),
            policy=policy,
            sink=sink,
            custom_exit=custom_exit,
        )
        state = engine.state
        state.cash = float(payload["cash"])
        state.sequence = int(payload["sequence"])
        state.kill_switch = bool(payload["kill_switch"])
        state.data_healthy = bool(payload.get("data_healthy", True))
        state.last_prices = {
            key: float(value) for key, value in payload.get("last_prices", {}).items()
        }
        state.last_minute_close_time = parsed(payload.get("last_minute_close_time"))
        fingerprint = payload.get("last_minute_fingerprint")
        state.last_minute_fingerprint = str(fingerprint) if fingerprint else None
        state.pair_cooldown_until = {}
        for pair, value in payload.get("pair_cooldown_until", {}).items():
            parsed_value = parsed(value)
            if parsed_value is not None:
                state.pair_cooldown_until[pair] = parsed_value
        state.stoploss_guard_until = parsed(payload.get("stoploss_guard_until"))
        state.maxdd_guard_until = parsed(payload.get("maxdd_guard_until"))
        state.positions = {}
        for item in payload.get("positions", []):
            item = dict(item)
            item["opened_at"] = parsed(item["opened_at"])
            position = Position(**item)
            if position.initial_stake <= 0:
                position.initial_stake = position.stake
            if position.initial_amount <= 0:
                position.initial_amount = position.amount
            state.positions[position.pair] = position
        state.orders = {}
        for item in payload.get("orders", []):
            item = dict(item)
            item["requested_at"] = parsed(item["requested_at"])
            item["expires_at"] = parsed(item["expires_at"])
            item["decision_candle_open"] = parsed(item.get("decision_candle_open"))
            order = PendingOrder(**item)
            state.orders[order.order_id] = order
        state.closed_trades = []
        for item in payload.get("closed_trades", []):
            item = dict(item)
            item["opened_at"] = parsed(item["opened_at"])
            item["closed_at"] = parsed(item["closed_at"])
            state.closed_trades.append(ClosedTrade(**item))
        if hasattr(engine, "reconcile_state"):
            engine.reconcile_state("checkpoint_restore")
        return engine
