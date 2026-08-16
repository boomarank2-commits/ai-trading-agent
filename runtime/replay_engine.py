"""Order execution and position lifecycle for the historical V8 replay."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Mapping

from replay_models import ClosedTrade, MinuteBar, PendingOrder, Position, iso
from replay_risk_engine import ReplayRiskEngine


class ReplayEngine(ReplayRiskEngine):
    def on_minute(self, bars: Mapping[str, MinuteBar]) -> None:
        if not bars:
            return
        close_times = {bar.close_time for bar in bars.values()}
        if len(close_times) != 1:
            raise RuntimeError("minute bars must share one close time")
        when = self._assert_monotone(next(iter(close_times)))
        for pair, bar in bars.items():
            if pair != bar.pair:
                raise RuntimeError("bar mapping key/pair mismatch")
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
            if bar is None or bar.open_time < order.requested_at:
                continue
            if order.side == "buy" and bar.low <= order.limit_price:
                self._fill_entry(order, when)
            elif order.side == "sell" and bar.high >= order.limit_price:
                reason = order.kind.partition(":")[2] or "exit_signal"
                self._close_position(order.pair, when, order.limit_price, reason)
                self.state.orders.pop(order_id, None)

    def _fill_entry(self, order: PendingOrder, when: datetime) -> None:
        self.state.orders.pop(order.order_id, None)
        risk = self.entry_allowed(order.pair, when, order.stake)
        if not risk.allowed:
            self.sink.event(
                {
                    "time": iso(when),
                    "type": "order_cancelled",
                    "order_id": order.order_id,
                    "reason": f"fill_time_{risk.reason}",
                }
            )
            return
        slippage = self.policy.slippage_bps / 10_000.0
        price = order.limit_price * (1.0 + slippage)
        stake = order.stake
        fee = stake * self.policy.fee_per_side
        amount = stake / price
        self.state.cash -= stake + fee
        position = Position(
            trade_id=self._next_id("trade"),
            pair=order.pair,
            opened_at=when,
            entry_price=price,
            stake=stake,
            amount=amount,
            entry_fee=fee,
            enter_tag=order.enter_tag,
            breakout_level=order.breakout_level,
            atr_4h=order.atr_4h,
            highest_rate=price,
            lowest_rate=price,
        )
        self.state.positions[order.pair] = position
        self.sink.event(
            {
                "time": iso(when),
                "type": "order_filled",
                "order_id": order.order_id,
                "trade_id": position.trade_id,
                "pair": order.pair,
                "side": "buy",
                "price": price,
                "stake": stake,
                "fee": fee,
            }
        )

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
            if self.custom_exit is not None:
                current_profit = (bar.close / position.entry_price) - 1.0
                reason = self.custom_exit(position, when, bar.close, current_profit)
                if reason:
                    self._close_position(pair, when, bar.close, reason)

    def _expire_orders(self, when: datetime) -> None:
        for order_id in list(self.state.orders):
            order = self.state.orders.get(order_id)
            if order is None or when < order.expires_at:
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
                }
            )

    def _close_position(
        self, pair: str, when: datetime, raw_price: float, reason: str
    ) -> None:
        position = self.state.positions.get(pair)
        if position is None:
            return
        slippage = self.policy.slippage_bps / 10_000.0
        price = float(raw_price) * (1.0 - slippage)
        gross_value = position.amount * price
        exit_fee = gross_value * self.policy.fee_per_side
        self.state.cash += gross_value - exit_fee
        pnl_abs = gross_value - position.stake - position.entry_fee - exit_fee
        pnl_ratio = pnl_abs / position.stake
        duration = int((when - position.opened_at).total_seconds() // 60)
        mae_ratio = (position.lowest_rate / position.entry_price) - 1.0
        mfe_ratio = (position.highest_rate / position.entry_price) - 1.0
        trade = ClosedTrade(
            trade_id=position.trade_id,
            pair=pair,
            opened_at=position.opened_at,
            closed_at=when,
            entry_price=position.entry_price,
            exit_price=price,
            stake=position.stake,
            amount=position.amount,
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
            if order.pair == pair and order.side == "sell":
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
                "exit_price": price,
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
