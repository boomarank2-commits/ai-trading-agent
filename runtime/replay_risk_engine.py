"""Shared-wallet and runtime-like entry risk gates for V8 replay."""

from __future__ import annotations

from datetime import datetime, timedelta

from replay_checkpoint import ReplayCheckpointMixin
from replay_models import (
    PAIRS,
    ClosedTrade,
    CustomExit,
    NullSink,
    PendingOrder,
    ReplayPolicy,
    ReplaySink,
    ReplayState,
    RiskDecision,
    StrategyDecision,
    iso,
    utc,
)


class ReplayRiskEngine(ReplayCheckpointMixin):
    """Chronological portfolio/execution state machine.

    Signal generation is intentionally injected. This keeps the validated V8
    source authoritative while this engine applies the runtime-like portfolio,
    daily-loss, cooldown and protection state on a shared 250-USDT wallet.
    """

    def __init__(
        self,
        *,
        start_time: datetime,
        policy: ReplayPolicy | None = None,
        sink: ReplaySink | None = None,
        custom_exit: CustomExit | None = None,
    ) -> None:
        self.policy = policy or ReplayPolicy()
        self.sink = sink or NullSink()
        self.custom_exit = custom_exit
        self.state = ReplayState(now=utc(start_time), cash=self.policy.start_capital)

    def _next_id(self, prefix: str) -> str:
        self.state.sequence += 1
        return f"{prefix}-{self.state.sequence:08d}"

    def _assert_monotone(self, when: datetime) -> datetime:
        when = utc(when)
        if when < self.state.now:
            raise RuntimeError(
                f"replay clock moved backwards: {iso(when)} < {iso(self.state.now)}"
            )
        self.state.now = when
        return when

    def _open_exposure(self) -> float:
        return sum(position.stake for position in self.state.positions.values())

    def _daily_closed_pnl(self, when: datetime) -> float:
        day = utc(when).date()
        return sum(
            trade.pnl_abs
            for trade in self.state.closed_trades
            if utc(trade.closed_at).date() == day
        )

    def _recent_stoplosses(self, when: datetime) -> list[ClosedTrade]:
        floor = utc(when) - timedelta(hours=self.policy.stoploss_guard_lookback_hours)
        return [
            trade
            for trade in self.state.closed_trades
            if trade.closed_at >= floor and trade.exit_reason == "stop_loss"
        ]

    def _maxdd_recent(self, when: datetime) -> float:
        floor = utc(when) - timedelta(hours=self.policy.maxdd_lookback_hours)
        trades = [trade for trade in self.state.closed_trades if trade.closed_at >= floor]
        if len(trades) < self.policy.maxdd_trade_limit:
            return 0.0
        equity = self.policy.start_capital
        peak = equity
        maxdd = 0.0
        for trade in trades:
            equity += trade.pnl_abs
            peak = max(peak, equity)
            if peak > 0:
                maxdd = max(maxdd, (peak - equity) / peak)
        return maxdd

    def _refresh_global_guards(self, when: datetime) -> None:
        when = utc(when)
        if self.state.stoploss_guard_until and when >= self.state.stoploss_guard_until:
            self.state.stoploss_guard_until = None
        if self.state.maxdd_guard_until and when >= self.state.maxdd_guard_until:
            self.state.maxdd_guard_until = None

        if (
            self.state.stoploss_guard_until is None
            and len(self._recent_stoplosses(when)) >= self.policy.stoploss_guard_trade_limit
        ):
            self.state.stoploss_guard_until = when + timedelta(
                hours=self.policy.stoploss_guard_block_hours
            )
            self.sink.event(
                {
                    "time": iso(when),
                    "type": "risk_lock",
                    "lock": "StoplossGuard",
                    "until": iso(self.state.stoploss_guard_until),
                }
            )

        if (
            self.state.maxdd_guard_until is None
            and self._maxdd_recent(when) > self.policy.maxdd_threshold
        ):
            self.state.maxdd_guard_until = when + timedelta(
                hours=self.policy.maxdd_block_hours
            )
            self.sink.event(
                {
                    "time": iso(when),
                    "type": "risk_lock",
                    "lock": "MaxDrawdown",
                    "until": iso(self.state.maxdd_guard_until),
                }
            )

    def entry_allowed(self, pair: str, when: datetime, stake: float) -> RiskDecision:
        when = self._assert_monotone(when)
        self._refresh_global_guards(when)
        if pair not in PAIRS:
            return RiskDecision(False, "pair_not_allowed")
        if self.state.kill_switch:
            return RiskDecision(False, "kill_switch")
        if not self.state.data_healthy:
            return RiskDecision(False, "data_unhealthy")
        if self._daily_closed_pnl(when) <= -self.policy.max_daily_loss:
            return RiskDecision(False, "daily_closed_loss")
        cooldown = self.state.pair_cooldown_until.get(pair)
        if cooldown and when < cooldown:
            return RiskDecision(False, "pair_cooldown")
        if self.state.stoploss_guard_until and when < self.state.stoploss_guard_until:
            return RiskDecision(False, "stoploss_guard")
        if self.state.maxdd_guard_until and when < self.state.maxdd_guard_until:
            return RiskDecision(False, "maxdrawdown_guard")
        if pair in self.state.positions:
            return RiskDecision(False, "pair_already_open")
        if any(
            order.pair == pair and order.side == "buy"
            for order in self.state.orders.values()
        ):
            return RiskDecision(False, "entry_order_pending")
        if len(self.state.positions) >= self.policy.max_open_positions:
            return RiskDecision(False, "max_open_positions")
        if stake > self.policy.stake_amount + 1e-9:
            return RiskDecision(False, "stake_too_large")
        if self._open_exposure() + stake > self.policy.max_total_exposure + 1e-9:
            return RiskDecision(False, "max_total_exposure")
        required_cash = stake * (1.0 + self.policy.fee_per_side)
        if self.state.cash + 1e-9 < required_cash:
            return RiskDecision(False, "insufficient_cash")
        return RiskDecision(True, "allowed")

    def partial_entry_continuation_allowed(
        self, pair: str, when: datetime, additional_stake: float
    ) -> RiskDecision:
        """Re-check safety before filling the remainder of one existing entry order.

        This is not DCA: only the unfilled remainder of the original immutable
        entry order may continue. If safety state changed after the first partial
        fill, the remainder is cancelled while the already filled position stays
        subject to the normal exit rules.
        """

        when = self._assert_monotone(when)
        self._refresh_global_guards(when)
        if pair not in self.state.positions:
            return RiskDecision(False, "partial_position_missing")
        if self.state.kill_switch:
            return RiskDecision(False, "kill_switch")
        if not self.state.data_healthy:
            return RiskDecision(False, "data_unhealthy")
        if self._daily_closed_pnl(when) <= -self.policy.max_daily_loss:
            return RiskDecision(False, "daily_closed_loss")
        if self.state.stoploss_guard_until and when < self.state.stoploss_guard_until:
            return RiskDecision(False, "stoploss_guard")
        if self.state.maxdd_guard_until and when < self.state.maxdd_guard_until:
            return RiskDecision(False, "maxdrawdown_guard")
        if self._open_exposure() + additional_stake > self.policy.max_total_exposure + 1e-9:
            return RiskDecision(False, "max_total_exposure")
        required_cash = additional_stake * (1.0 + self.policy.fee_per_side)
        if self.state.cash + 1e-9 < required_cash:
            return RiskDecision(False, "insufficient_cash")
        return RiskDecision(True, "allowed")

    def submit_decision(self, decision: StrategyDecision) -> None:
        when = self._assert_monotone(decision.known_at)
        payload = {
            "time": iso(when),
            "pair": decision.pair,
            "candle_open": iso(decision.candle_open),
            "enter_candidate": bool(decision.enter_long),
            "exit_candidate": bool(decision.exit_long),
            "enter_tag": decision.enter_tag,
            "exit_tag": decision.exit_tag,
            "reference_price": decision.reference_price,
            "features": dict(decision.features),
        }

        if decision.exit_long and decision.pair in self.state.positions:
            self._submit_exit_order(
                decision.pair,
                when,
                decision.reference_price,
                decision.exit_tag or "exit_signal",
            )

        risk = RiskDecision(False, "not_an_entry_candidate")
        entry_order_id: str | None = None
        if decision.enter_long:
            risk = self.entry_allowed(decision.pair, when, self.policy.stake_amount)
            if risk.allowed:
                entry_order_id = self._submit_entry_order(decision, when)
        payload["entry_allowed"] = risk.allowed
        payload["entry_order_id"] = entry_order_id
        payload["entry_rejection_reason"] = None if risk.allowed else risk.reason
        payload["open_positions"] = len(self.state.positions)
        payload["open_exposure"] = self._open_exposure()
        payload["daily_closed_pnl"] = self._daily_closed_pnl(when)
        self.sink.decision(payload)

    def _submit_entry_order(self, decision: StrategyDecision, when: datetime) -> str:
        order = PendingOrder(
            order_id=self._next_id("order"),
            pair=decision.pair,
            side="buy",
            kind="entry_limit",
            requested_at=when,
            limit_price=decision.reference_price,
            expires_at=when + timedelta(minutes=self.policy.entry_timeout_minutes),
            stake=self.policy.stake_amount,
            decision_candle_open=decision.candle_open,
            enter_tag=decision.enter_tag,
            breakout_level=decision.breakout_level,
            atr_4h=decision.atr_4h,
        )
        self.state.orders[order.order_id] = order
        self.sink.event(
            {
                "time": iso(when),
                "type": "order_requested",
                "order_id": order.order_id,
                "pair": order.pair,
                "side": order.side,
                "kind": order.kind,
                "price": order.limit_price,
                "execution_delay_minutes": self.policy.execution_delay_minutes,
            }
        )
        return order.order_id

    def _submit_exit_order(
        self, pair: str, when: datetime, price: float, reason: str
    ) -> None:
        if any(
            order.pair == pair and order.side == "sell"
            for order in self.state.orders.values()
        ):
            return
        position = self.state.positions.get(pair)
        if position is None:
            return
        for order_id, order in list(self.state.orders.items()):
            if order.pair == pair and order.side == "buy":
                self.state.orders.pop(order_id, None)
                self.sink.event(
                    {
                        "time": iso(when),
                        "type": "order_cancelled",
                        "order_id": order_id,
                        "reason": "entry_remainder_cancelled_for_exit",
                    }
                )
        order = PendingOrder(
            order_id=self._next_id("order"),
            pair=pair,
            side="sell",
            kind=f"exit_limit:{reason}",
            requested_at=when,
            limit_price=float(price),
            expires_at=when + timedelta(minutes=self.policy.exit_timeout_minutes),
            target_amount=position.amount,
        )
        self.state.orders[order.order_id] = order
        self.sink.event(
            {
                "time": iso(when),
                "type": "order_requested",
                "order_id": order.order_id,
                "pair": pair,
                "side": "sell",
                "kind": order.kind,
                "price": order.limit_price,
                "target_amount": order.target_amount,
                "execution_delay_minutes": self.policy.execution_delay_minutes,
            }
        )

    def reconcile_state(self, reason: str = "manual") -> None:
        """Fail closed on impossible restored/boot state.

        A valid checkpoint containing an already open position is accepted. This
        is the replay equivalent of a boot reconciliation boundary: unknown
        pairs, orphan exits or exposure beyond the immutable safety envelope are
        rejected rather than guessed away.
        """

        if self.state.cash < -1e-9:
            raise RuntimeError("reconciliation failed: negative cash")
        if self._open_exposure() > self.policy.max_total_exposure + 1e-9:
            raise RuntimeError("reconciliation failed: exposure above safety cap")
        if len(self.state.positions) > self.policy.max_open_positions:
            raise RuntimeError("reconciliation failed: too many open positions")

        for pair, position in self.state.positions.items():
            if pair not in PAIRS or position.pair != pair:
                raise RuntimeError("reconciliation failed: invalid position pair")
            if position.stake <= 0 or position.amount <= 0:
                raise RuntimeError("reconciliation failed: invalid open position")
            if position.initial_stake <= 0:
                position.initial_stake = position.stake
            if position.initial_amount <= 0:
                position.initial_amount = position.amount
            if position.initial_stake + 1e-9 < position.stake:
                raise RuntimeError("reconciliation failed: remaining stake exceeds initial")
            if position.initial_amount + 1e-12 < position.amount:
                raise RuntimeError("reconciliation failed: remaining amount exceeds initial")

        for order_id, order in self.state.orders.items():
            if order.order_id != order_id or order.pair not in PAIRS:
                raise RuntimeError("reconciliation failed: invalid pending order")
            if order.side not in {"buy", "sell"} or order.limit_price <= 0:
                raise RuntimeError("reconciliation failed: invalid order contract")
            position = self.state.positions.get(order.pair)
            if order.side == "sell":
                if position is None:
                    raise RuntimeError("reconciliation failed: orphan sell order")
                if order.target_amount <= 0:
                    order.target_amount = position.amount + order.filled_amount
            elif position is not None and position.entry_order_id != order.order_id:
                raise RuntimeError("reconciliation failed: unrelated buy beside position")

        self.sink.event(
            {
                "time": iso(self.state.now),
                "type": "reconciliation_ok",
                "reason": reason,
                "cash": self.state.cash,
                "open_positions": len(self.state.positions),
                "open_exposure": self._open_exposure(),
                "pending_orders": len(self.state.orders),
            }
        )

    def set_data_health(self, healthy: bool, when: datetime, reason: str = "") -> None:
        when = self._assert_monotone(when)
        self.state.data_healthy = bool(healthy)
        self.sink.event(
            {
                "time": iso(when),
                "type": "data_health",
                "healthy": self.state.data_healthy,
                "reason": reason,
            }
        )

    def set_kill_switch(self, active: bool, when: datetime) -> None:
        when = self._assert_monotone(when)
        self.state.kill_switch = bool(active)
        self.sink.event(
            {"time": iso(when), "type": "kill_switch", "active": self.state.kill_switch}
        )
