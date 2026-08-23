from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "runtime" / "user_data" / "config.json"
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
BACKTEST_API = ROOT / "runtime" / "ten_pair_backtest_api.py"
LOCKED_RUNTIME = ROOT / "runtime" / "locked_freqtrade.py"
BACKTEST_UI = ROOT / "runtime" / "ui" / "testbot-backtest.js"

TEN_PAIRS = (
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "BNB/USDT",
    "DOGE/USDT",
    "LINK/USDT",
    "TRX/USDT",
    "LTC/USDT",
    "BCH/USDT",
)
NEW_FOUR = TEN_PAIRS[6:]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_active_v12_17_python_files_are_syntax_valid() -> None:
    for path in (STRATEGY, BACKTEST_API, LOCKED_RUNTIME):
        ast.parse(_text(path), filename=str(path))


def test_active_paper_config_is_exact_ten_pair_250_80_3_contract() -> None:
    config = json.loads(_text(CONFIG))
    assert config["strategy"] == "CompressionBreakout250"
    assert tuple(config["exchange"]["pair_whitelist"]) == TEN_PAIRS
    assert config["available_capital"] == 250
    assert config["dry_run_wallet"] == 250
    assert config["stake_amount"] == 80
    assert config["max_open_trades"] == 3
    assert config["position_adjustment_enable"] is True
    assert config["max_entry_position_adjustment"] == 2
    assert config["trading_mode"] == "spot"
    assert config["margin_mode"] == ""


def test_active_strategy_expands_broad_core_and_keeps_btc_eth_special_paths() -> None:
    text = _text(STRATEGY)
    assert 'STRATEGY_VERSION = "V12.17"' in text
    for pair in TEN_PAIRS:
        assert f'"{pair}"' in text
    assert '"ADA/USDT"' not in text

    broad_core = text.split("BROAD_CORE_PAIRS", maxsplit=1)[1].split(
        "buy_momentum_30d", maxsplit=1
    )[0]
    for pair in ("SOL/USDT", "XRP/USDT", "BNB/USDT", "DOGE/USDT", *NEW_FOUR):
        assert f'"{pair}"' in broad_core
    assert '"BTC/USDT"' not in broad_core
    assert '"ETH/USDT"' not in broad_core

    reclaim = text.split("RECLAIM_PROFILES", maxsplit=1)[1].split(
        "REGIME_TREND", maxsplit=1
    )[0]
    assert '"BTC/USDT"' in reclaim
    assert '"ETH/USDT"' in reclaim
    for pair in ("SOL/USDT", "XRP/USDT", "BNB/USDT", "DOGE/USDT", *NEW_FOUR):
        assert f'"{pair}"' not in reclaim


def test_three_chunk_same_pair_logic_is_signal_gated_and_globally_capped() -> None:
    text = _text(STRATEGY)
    for required in (
        "MAX_STAKE_USDT = 80.0",
        "MAX_TOTAL_CAPITAL_USDT = 250.0",
        "MAX_TOTAL_EXPOSURE_USDT = 240.0",
        "MAX_OPEN_POSITIONS = 3",
        "MAX_ENTRIES_PER_PAIR = 3",
        "position_adjustment_enable = True",
        "max_entry_position_adjustment = 2",
        "def adjust_trade_position(",
        'candle.get("enter_long", 0)',
        "date_last_filled_utc",
        "Trade.total_open_trades_stakes()",
        "> self.MAX_TOTAL_EXPOSURE_USDT + 1e-6",
        "new_signal_chunk",
        "stoploss = -0.055",
        "can_short = False",
    ):
        assert required in text
    assert "current_profit < 0" not in text.split("def adjust_trade_position(", 1)[1].split(
        "def custom_stoploss(", 1
    )[0]


def test_backtest_ui_is_independent_250_wallet_per_pair_and_selected_period_batch() -> None:
    ui = _text(BACKTEST_UI)
    for pair in TEN_PAIRS:
        assert pair in ui
    assert "Alle 10 nacheinander" in ui
    assert "eigenen 250-USDT-Testwallet" in ui
    assert "kein gemeinsames 2.500-USDT-Portfolio" in ui
    assert "const years = Number(yearsSelect.value);" in ui
    assert "PAIRS.map(([pair]) => ({ pair, years }))" in ui
    assert 'value="1"' in ui
    assert 'value="2"' in ui
    assert 'value="3"' in ui
    assert 'value="PORTFOLIO"' not in ui
    assert "Alle 22 Backtests" not in ui


def test_backtest_adapter_uses_active_strategy_config_and_keeps_portfolio_internal_only() -> None:
    api = _text(BACKTEST_API)
    assert "CompressionBreakout250TenPair" not in api
    assert "config-ten-pair-research.json" not in api
    assert "TEN_PAIR_UNIVERSE" in api
    assert "base.ALLOWED_PAIRS = TEN_PAIR_UNIVERSE" in api
    assert "base.PORTFOLIO_TARGET" in api
    assert "shared 250-USDT 3x80 system backtest" in api
    assert "ten sequential independent tests" in api


def test_locked_paper_runtime_serves_ten_pair_adapter_without_replacing_strategy_loader() -> None:
    runtime = _text(LOCKED_RUNTIME)
    assert "from ten_pair_backtest_api import build_router" in runtime
    assert "_load_exact_strategy(" in runtime
    assert "args.strategy_source" in runtime
    assert "args.strategy_sha256" in runtime
