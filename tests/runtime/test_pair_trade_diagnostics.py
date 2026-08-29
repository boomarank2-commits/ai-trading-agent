from __future__ import annotations

import pytest

from runtime.pair_trade_diagnostics import summarize_strategy


def test_chunk_attribution_uses_fee_adjusted_entry_and_exit_cashflows() -> None:
    strategy = {
        "pairlist": ["LINK/USDT"],
        "trades": [
            {
                "pair": "LINK/USDT",
                "stake_amount": 160.0,
                "max_stake_amount": 160.0,
                "open_rate": 10.0,
                "close_rate": 12.0,
                "fee_open": 0.002,
                "fee_close": 0.002,
                "open_date": "2025-01-01 00:00:00+00:00",
                "open_timestamp": 1_000,
                "close_timestamp": 7_201_000,
                "profit_abs": 31.2,
                "profit_ratio": 0.195,
                "trade_duration": 120,
                "min_rate": 9.5,
                "max_rate": 12.2,
                "exit_reason": "signal",
                "enter_tag": "route",
                "orders": [
                    {
                        "amount": 8.0,
                        "safe_price": 10.0,
                        "cost": 80.16,
                        "ft_is_entry": True,
                        "order_filled_timestamp": 1_000,
                    },
                    {
                        "amount": 8.0,
                        "safe_price": 10.0,
                        "cost": 80.16,
                        "ft_is_entry": True,
                        "order_filled_timestamp": 3_601_000,
                    },
                ],
            }
        ],
    }

    summary = summarize_strategy(strategy)

    expected_profit = 8.0 * 12.0 * (1.0 - 0.002) - 80.16
    assert summary["additional_entry_chunks"] == 1
    assert summary["chunk_attribution"]["chunk_1"]["profit_usdt"] == pytest.approx(
        expected_profit, abs=1e-4
    )
    assert summary["chunk_attribution"]["chunk_2"]["profit_usdt"] == pytest.approx(
        expected_profit, abs=1e-4
    )
    assert summary["chunk_attribution"]["chunk_1"]["slot_hours"] == pytest.approx(2.0)
    assert summary["chunk_attribution"]["chunk_2"]["slot_hours"] == pytest.approx(1.0)


def test_chunk_attribution_handles_result_without_orders() -> None:
    summary = summarize_strategy(
        {
            "pairlist": ["LTC/USDT"],
            "trades": [
                {
                    "pair": "LTC/USDT",
                    "profit_abs": -4.0,
                    "open_rate": 100.0,
                    "min_rate": 95.0,
                    "max_rate": 101.0,
                }
            ],
        }
    )

    assert summary["chunk_attribution"] == {}
