"""Order execution and position lifecycle for the historical V8 replay."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from replay_models import ClosedTrade, MinuteBar, PendingOrder, Position, iso
from replay_risk_engine import ReplayRiskEngine

_EPS = 1e-12


class ReplayEngine(ReplayRiskEngine):
    @staticmethod
    def _minute_fingerprint(bars: Mapping[str, MinuteBar]) -> str:
        payload = [
            {
                "pair": pair,
                "open_time": iso(bar.open_time),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
            for pair, bar in sorted(bars.items())
        ]
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _execution_price(self, raw_price: float, side: str) -> float:
        """Apply a deterministic adverse execution-cost proxy.

        `spread_bps` is interpreted as a quoted round-trip spread proxy, so half
        is charged on each side. This is deliberately deterministic and is not a
        claim to reconstruct historical order books.
        """

        adverse_bps = self.policy.slippage_bps + (self.policy.spread_bps / 2.0)
        adverse = adverse_bps / 10_000.0
        if side == "buy":
            return float(raw_price) * (1.0 + adverse)
        if side == "sell":
            return float(raw_price) * (1.0 - adverse)
        raise ValueError(f"unsupported execution side: {side}")

    def on_minute(self, bars: Mapping[str, MinuteBar]) -> None:
        if not bars:
            return
        close_times = {bar.close_time for bar in bars.values()}
        if len(close_times) != 1:
            raise RuntimeError("minute bars must share one close time")
        close_time = next(iter(close_times))
        for pair, bar in bars.items():
            if pair != bar.pair:
                raise RuntimeError("bar mapping key/pair mismatch")

        fingerprint = self._minute_fingerprint(bars)
        previous_time = self.state.last_minute_close_time
        if previous_time is not None and close_time == previous_time:
            if fingerprint == self.state.last_minute_fingerprint:
                self.sink.event(
                    {
                        "time": iso(close_time),
                        "type": "duplicate_minute_ignored",
                        "fingerprint": fingerprint,
                    }
                )
                return
            raise RuntimeError("conflicting duplicate minute batch")

        when = self._assert_monotone(close_time)
        self.state.last_minute_close_time = when
        self.state.last_minute_fingerprint = fingerprint
        for pair, bar in bars.items():
            self.state.last_prices[pair] = bar.close

        self._process_pending_orders(bars, when)
        self._process_positions(bars, when)
        self._expire_orders(when)
        self._refresh_global_guards(when)
        self.sink.equity(
            {
                "time": iso(when),
                "cash": self.state.cash,
                "equity": self.mark_to_market(),
                "open_positions": len(self.state.positions),
                "open_exposure": self._open_exposure(),
            }
        )

    def _process_pending_orders(
        self, bars: Mapping[str, MinuteBar], when: datetime
    ) -> None:
        for order_id in list(self.state.orders):
            order = self.state.orders.get(order_id)
            if order is None:
                continue
            bar = bars.get(order.pair)
            eligible_at = order.requested_at + timedelta(
                minutes=self.policy.execution_delay_minutes
            )
            if bar is None or bar.open_time < eligible_at:
                continue
            if order.side == "buy" and bar.low <= order.limit_price:
                self._fill_entry(order, when)
            elif order.side == "sell" and bar.high >= order.limit_price:
                reason = order.kind.partition(":")[2] or "exit_signal"
                self._fill_exit(order, when, reason)

    def _fill_entry(self, order: PendingOrder, when: datetime) -> None:
        remaining = order.remaining_stake
        if remaining <= _EPS:
            self.state.orders.pop(order.order_id, None)
            return

        position = self.state.positions.get(order.pair)
        if position is None:
            # Temporarily remove the very order being re-checked so the normal
            # pending-order guard does not reject itself.
            self.state.orders.pop(order.order_id, None)
            risk = self.entry_allowed(order.pair, when, remaining)
            if risk.allowed:
                self.state.orders[order.order_id] = order
        else:
            if position.entry_order_id != order.order_id:
                raise RuntimeError("entry fill conflicts with unrelated open position")
            risk = self.partial_entry_continuation_allowed(order.pair, when, remaining)

        if not risk.allowed:
            self.state.orders.pop(order.order_id, None)
            self.sink.event(
                {
                    "time": iso(when),
                    "type": "order_cancelled",
                    "order_id": order.order_id,
                    "reason": f"fill_time_{risk.reason}",
                    "filled_stake": order.filled_stake,
                    "unfilled_stake": remaining,
                }
            )
            return

        slice_target = order.stake * self.policy.fill_fraction_per_touch
        slice_stake = min(remaining, slice_target)
        price = self._execution_price(order.limit_price, "buy")
        fee = slice_stake * self.policy.fee_per_side
        amount = slice_stake / price
        self.state.cash -= slice_stake + fee
        order.filled_stake += slice_stake
        order.filled_amount += amount

        if position is None:
            position = Position(
                trade_id=self._next_id("trade"),
                pair=order.pair,
                opened_at=when,
                entry_price=price,
                stake=slice_stake,
                amount=amount,
                entry_fee=fee,
                enter_tag=order.enter_tag,
                breakout_level=order.breakout_level,
                atr_4h=order.atr_4h,
                highest_rate=price,
                lowest_rate=price,
                entry_order_id=order.order_id,
                initial_stake=slice_stake,
                initial_amount=amount,
            )
            self.state.positions[order.pair] = position
        else:
            position.stake += slice_stake
            position.amount += amount
            position.entry_fee += fee
            position.initial_stake += slice_stake
            position.initial_amount += amount
            position.entry_price = position.initial_stake / position.initial_amount
            position.highest_rate = max(position.highest_rate, price)
            position.lowest_rate = min(position.lowest_rate, price)

        completed = order.remaining_stake <= _EPS
        if completed:
            self.state.orders.pop(order.order_id, None)
        event_type = "order_filled" if completed else "order_partial_fill"
        self.sink.event(
            {
                "time": iso(when),
                "type": event_type,
                "order_id": order.order_id,
                "trade_id": position.trade_id,
                "pair": order.pair,
                "side": "buy",
                "price": price,
                "slice_stake": slice_stake,
                "filled_stake": order.filled_stake,
                "remaining_stake": order.remaining_stake,
                "fee": fee,
                "spread_bps": self.policy.spread_bps,
                "slippage_bps": self.policy.slippage_bps,
            }
        )

    def _fill_exit(self, order: PendingOrder, when: datetime, reason: str) -> None:
        position = self.state.positions.get(order.pair)
        if position is None:
            self.state.orders.pop(order.order_id, None)
            return
        if order.target_amount <= 0:
            order.target_amount = position.amount + order.filled_amount
        remaining = min(order.remaining_amount, position.amount)
        if remaining <= _EPS:
            self.state.orders.pop(order.order_id, None)
            return

        slice_target = order.target_amount * self.policy.fill_fraction_per_touch
        amount = min(remaining, slice_target)
        price = self._execution_price(order.limit_price, "sell")
        self._apply_exit_slice(position, amount, price)
        order.filled_amount += amount

        completed = order.remaining_amount <= _EPS or position.amount <= _EPS
        if completed:
            self.state.orders.pop(order.order_id, None)
            self._finalize_position(order.pair, when, reason)
            return

        self.sink.event(
            {
                "time": iso(when),
                "type": "order_partial_fill",
                "order_id": order.order_id,
                "trade_id": position.trade_id,
                "pair": order.pair,
                "side": "sell",
                "price": price,
                "filled_amount": order.filled_amount,
                "remaining_amount": order.remaining_amount,
                "spread_bps": self.policy.spread_bps,
                "slippage_bps": self.policy.slippage_bps,
            }
        )

    def _apply_exit_slice(self, position: Position, amount: float, price: float) -> None:
        if amount <= 0 or amount > position.amount + _EPS:
            raise RuntimeError("invalid exit fill amount")
        amount = min(amount, position.amount)
        remaining_amount_before = position.amount
        cost_fraction = amount / remaining_amount_before
        cost_basis_slice = position.stake * cost_fraction
        gross_value = amount * price
        fee = gross_value * self.policy.fee_per_side

        self.state.cash += gross_value - fee
        position.exit_value_accumulated += gross_value
        position.exit_fee_accumulated += fee
        position.exit_amount_accumulated += amount
        position.amount = max(0.0, position.amount - amount)
        position.stake = max(0.0, position.stake - cost_basis_slice)

    def _process_positions(self, bars: Mapping[str, MinuteBar], when: datetime) -> None:
        for pair in list(self.state.positions):
            position = self.state.positions.get(pair)
            bar = bars.get(pair)
            if position is None or bar is None:
                continue
            position.highest_rate = max(position.highest_rate, bar.high)
            position.lowest_rate = min(position.lowest_rate, bar.low)

            if bar.low <= position.stop_price:
                self._close_position(pair, when, position.stop_price, "stop_loss")
                continue
            if bar.high >= position.roi_price:
                self._close_position(pair, when, position.roi_price, "roi")
                continue
            pending_sell = any(
                order.pair == pair and order.side == "sell"
                for order in self.state.orders.values()
            )
            if self.custom_exit is not None and not pending_sell:
                current_profit = (bar.close / position.entry_price) - 1.0
                reason = self.custom_exit(position, when, bar.close, current_profit)
                if reason:
                    self._close_position(pair, when, bar.close, reason)

    def _expire_orders(self, when: datetime) -> None:
        for order_id in list(self.state.orders):
            order = self.state.orders.get(order_id)
            if order is None or when < order.expires_at:
                continue

            if order.cancel_reject_count < self.policy.cancel_rejects_before_cancel:
                order.cancel_reject_count += 1
                timeout_minutes = (
                    self.policy.entry_timeout_minutes
                    if order.side == "buy"
                    else self.policy.exit_timeout_minutes
                )
                order.expires_at = when + timedelta(minutes=timeout_minutes)
                self.sink.event(
                    {
                        "time": iso(when),
                        "type": "cancel_rejected",
                        "order_id": order.order_id,
                        "cancel_reject_count": order.cancel_reject_count,
                    }
                )
                continue

            retry_exit = (
                order.side == "sell"
                and order.timeout_count + 1 < self.policy.exit_timeout_count
            )
            if retry_exit:
                order.timeout_count += 1
                order.expires_at = when + timedelta(
                    minutes=self.policy.exit_timeout_minutes
                )
                self.sink.event(
                    {
                        "time": iso(when),
                        "type": "order_timeout_retry",
                        "order_id": order.order_id,
                        "timeout_count": order.timeout_count,
                        "filled_amount": order.filled_amount,
                        "remaining_amount": order.remaining_amount,
                    }
                )
                continue
            self.state.orders.pop(order_id, None)
            self.sink.event(
                {
                    "time": iso(when),
                    "type": "order_cancelled",
                    "order_id": order.order_id,
                    "reason": "unfilled_timeout",
                    "filled_stake": order.filled_stake,
                    "filled_amount": order.filled_amount,
                }
            )

    def _close_position(
        self, pair: str, when: datetime, raw_price: float, reason: str
    ) -> None:
        position = self.state.positions.get(pair)
        if position is None:
            return
        if position.amount > _EPS:
            price = self._execution_price(raw_price, "sell")
            self._apply_exit_slice(position, position.amount, price)
        self._finalize_position(pair, when, reason)

    def _finalize_position(self, pair: str, when: datetime, reason: str) -> None:
        position = self.state.positions.get(pair)
        if position is None:
            return
        initial_stake = position.initial_stake or position.stake
        initial_amount = position.initial_amount or (
            position.exit_amount_accumulated + position.amount
        )
        if initial_stake <= 0 or initial_amount <= 0:
            raise RuntimeError("cannot finalize invalid position")
        if position.exit_amount_accumulated + _EPS < initial_amount:
            raise RuntimeError("cannot finalize position with unclosed amount")

        exit_price = position.exit_value_accumulated / position.exit_amount_accumulated
        exit_fee = position.exit_fee_accumulated
        pnl_abs = (
            position.exit_value_accumulated
            - initial_stake
            - position.entry_fee
            - exit_fee
        )
        pnl_ratio = pnl_abs / initial_stake
        duration = int((when - position.opened_at).total_seconds() // 60)
        mae_ratio = (position.lowest_rate / position.entry_price) - 1.0
        mfe_ratio = (position.highest_rate / position.entry_price) - 1.0
        trade = ClosedTrade(
            trade_id=position.trade_id,
            pair=pair,
            opened_at=position.opened_at,
            closed_at=when,
            entry_price=position.entry_price,
            exit_price=exit_price,
            stake=initial_stake,
            amount=initial_amount,
            entry_fee=position.entry_fee,
            exit_fee=exit_fee,
            pnl_abs=pnl_abs,
            pnl_ratio=pnl_ratio,
            exit_reason=reason,
            enter_tag=position.enter_tag,
            duration_minutes=duration,
            mae_ratio=mae_ratio,
            mfe_ratio=mfe_ratio,
        )
        self.state.closed_trades.append(trade)
        self.state.positions.pop(pair, None)
        for order_id, order in list(self.state.orders.items()):
            if order.pair == pair:
                self.state.orders.pop(order_id, None)
        self.state.pair_cooldown_until[pair] = when + timedelta(
            minutes=self.policy.cooldown_minutes
        )
        self.sink.event(
            {
                "time": iso(when),
                "type": "trade_closed",
                "trade_id": trade.trade_id,
                "pair": pair,
                "exit_reason": reason,
                "exit_price": exit_price,
                "pnl_abs": pnl_abs,
                "pnl_ratio": pnl_ratio,
                "fee_total": position.entry_fee + exit_fee,
            }
        )

    def mark_to_market(self) -> float:
        equity = self.state.cash
        for pair, position in self.state.positions.items():
            price = self.state.last_prices.get(pair, position.entry_price)
            equity += position.amount * price
        return equity


def final_metrics(engine: ReplayEngine) -> dict[str, Any]:
    trades = engine.state.closed_trades
    wins = [trade for trade in trades if trade.pnl_abs > 0]
    losses = [trade for trade in trades if trade.pnl_abs < 0]
    gross_profit = sum(trade.pnl_abs for trade in wins)
    gross_loss = -sum(trade.pnl_abs for trade in losses)
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = math.inf
    else:
        profit_factor = 0.0
    net = sum(trade.pnl_abs for trade in trades)
    longest_loss = 0
    current_loss = 0
    equity = engine.policy.start_capital
    peak = equity
    maxdd = 0.0
    for trade in trades:
        if trade.pnl_abs < 0:
            current_loss += 1
            longest_loss = max(longest_loss, current_loss)
        else:
            current_loss = 0
        equity += trade.pnl_abs
        peak = max(peak, equity)
        if peak > 0:
            maxdd = max(maxdd, (peak - equity) / peak)
    return {
        "start_capital": engine.policy.start_capital,
        "end_equity_marked": engine.mark_to_market(),
        "closed_net_pnl": net,
        "closed_return_pct": (net / engine.policy.start_capital) * 100.0,
        "trade_count": len(trades),
        "win_rate_pct": (len(wins) / len(trades) * 100.0) if trades else 0.0,
        "profit_factor": profit_factor,
        "max_closed_equity_drawdown_pct": maxdd * 100.0,
        "longest_losing_streak": longest_loss,
        "avg_trade_pnl": (net / len(trades)) if trades else 0.0,
        "total_fees": sum(trade.entry_fee + trade.exit_fee for trade in trades),
        "open_positions": len(engine.state.positions),
        "open_exposure": engine._open_exposure(),
        "checkpoint_hash": engine.checkpoint_hash(),
    }
