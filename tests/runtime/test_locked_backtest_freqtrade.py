from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import freqtrade.strategy.interface as interface_module
import freqtrade.strategy.strategy_wrapper as wrapper_module
import pytest
from freqtrade.exceptions import StrategyError
from freqtrade.optimize.backtesting import Backtesting

from runtime.locked_backtest_freqtrade import (
    _install_candle_cadenced_position_adjustment,
    _install_readonly_trade_callback_fastpath,
)

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"


def test_position_adjustment_runs_only_on_strategy_candle_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[datetime] = []

    def original(_backtesting, trade, _row, current_time):
        calls.append(current_time)
        return trade

    monkeypatch.setattr(Backtesting, "_check_adjust_trade_for_candle", original)

    class OptInStrategy:
        position_adjustment_on_new_strategy_candle_only = True

    assert _install_candle_cadenced_position_adjustment(OptInStrategy) is True
    runner = SimpleNamespace(timeframe_td=timedelta(minutes=15))
    trade = object()
    off_boundary = datetime(2026, 8, 23, 12, 14, tzinfo=UTC)
    boundary = datetime(2026, 8, 23, 12, 15, tzinfo=UTC)

    assert Backtesting._check_adjust_trade_for_candle(runner, trade, (), off_boundary) is trade
    assert calls == []
    assert Backtesting._check_adjust_trade_for_candle(runner, trade, (), boundary) is trade
    assert calls == [boundary]


def test_readonly_fastpath_skips_deepcopy_but_keeps_freqtrade_error_handling() -> None:
    original_wrapper = wrapper_module.strategy_safe_wrapper
    original_interface_wrapper = interface_module.strategy_safe_wrapper

    class NoCopyTrade:
        def __deepcopy__(self, _memo):
            raise AssertionError("trade must not be copied")

    class OptInStrategy:
        backtest_readonly_trade_callbacks = ("callback", "failing")

        def callback(self, *, trade):
            return trade

        def failing(self, *, trade):
            del trade
            raise ValueError("covered failure")

    try:
        assert _install_readonly_trade_callback_fastpath(OptInStrategy) == (
            "callback",
            "failing",
        )
        strategy = OptInStrategy()
        trade = NoCopyTrade()
        wrapped = interface_module.strategy_safe_wrapper(strategy.callback)
        assert wrapped(trade=trade) is trade
        failing = interface_module.strategy_safe_wrapper(strategy.failing)
        with pytest.raises(StrategyError, match="covered failure"):
            failing(trade=trade)
    finally:
        wrapper_module.strategy_safe_wrapper = original_wrapper
        interface_module.strategy_safe_wrapper = original_interface_wrapper


def test_fastpath_callbacks_do_not_mutate_the_trade_object() -> None:
    def rooted_in_trade(node: ast.AST) -> bool:
        while isinstance(node, (ast.Attribute, ast.Subscript)):
            node = node.value
        return isinstance(node, ast.Name) and node.id == "trade"

    source = STRATEGY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    strategy = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "CompressionBreakout250"
    )
    callback_names = {"adjust_trade_position", "custom_stoploss", "custom_exit"}
    allowed_trade_methods = {"select_filled_orders", "get_custom_data", "split"}
    for callback in (
        node
        for node in strategy.body
        if isinstance(node, ast.FunctionDef) and node.name in callback_names
    ):
        for node in ast.walk(callback):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert not (
                    rooted_in_trade(node.func.value)
                    and node.func.attr not in allowed_trade_methods
                ), callback.name
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    assert not (
                        isinstance(target, ast.Attribute)
                        and rooted_in_trade(target.value)
                    ), callback.name
