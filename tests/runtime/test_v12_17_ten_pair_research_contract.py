from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE_CONFIG = ROOT / "runtime" / "user_data" / "config.json"
RESEARCH_CONFIG = ROOT / "runtime" / "user_data" / "config-ten-pair-research.json"
LIVE_STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
RESEARCH_STRATEGY = (
    ROOT
    / "runtime"
    / "user_data"
    / "strategies"
    / "CompressionBreakout250TenPair.py"
)
RESEARCH_API = ROOT / "runtime" / "ten_pair_backtest_api.py"
LOCKED_RUNTIME = ROOT / "runtime" / "locked_freqtrade.py"
RESEARCH_UI = ROOT / "runtime" / "ui" / "testbot-backtest-ten-pair.js"

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
LIVE_SIX = TEN_PAIRS[:6]
NEW_FOUR = TEN_PAIRS[6:]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_research_python_files_are_syntax_valid() -> None:
    for path in (RESEARCH_STRATEGY, RESEARCH_API, LOCKED_RUNTIME):
        ast.parse(_text(path), filename=str(path))


def test_live_v12_15_config_remains_on_exact_existing_six_pairs() -> None:
    config = json.loads(_text(LIVE_CONFIG))
    assert config["strategy"] == "CompressionBreakout250"
    assert tuple(config["exchange"]["pair_whitelist"]) == LIVE_SIX
    assert config["available_capital"] == 250
    assert config["stake_amount"] == 80
    assert config["max_open_trades"] == 3
    assert config["position_adjustment_enable"] is False


def test_ten_pair_research_config_keeps_250_80_3_contract() -> None:
    config = json.loads(_text(RESEARCH_CONFIG))
    assert config["strategy"] == "CompressionBreakout250TenPair"
    assert tuple(config["exchange"]["pair_whitelist"]) == TEN_PAIRS
    assert config["available_capital"] == 250
    assert config["dry_run_wallet"] == 250
    assert config["stake_amount"] == 80
    assert config["max_open_trades"] == 3
    assert config["position_adjustment_enable"] is False
    assert config["max_entry_position_adjustment"] == 0
    assert config["trading_mode"] == "spot"
    assert config["margin_mode"] == ""


def test_v12_17_research_strategy_adds_only_four_new_broad_core_pairs() -> None:
    live = _text(LIVE_STRATEGY)
    research = _text(RESEARCH_STRATEGY)
    assert 'STRATEGY_VERSION = "V12.15"' in live
    assert 'STRATEGY_VERSION = "V12.17"' in research
    assert "class CompressionBreakout250TenPair(IStrategy):" in research
    for pair in TEN_PAIRS:
        assert f'"{pair}"' in research
    for pair in NEW_FOUR:
        assert f'"{pair}"' not in live
    broad_core = research.split("BROAD_CORE_PAIRS", maxsplit=1)[1].split(
        "buy_momentum_30d", maxsplit=1
    )[0]
    for pair in ("SOL/USDT", "XRP/USDT", "BNB/USDT", "DOGE/USDT", *NEW_FOUR):
        assert f'"{pair}"' in broad_core
    assert '"BTC/USDT"' not in broad_core
    assert '"ETH/USDT"' not in broad_core
    assert '"ADA/USDT"' not in research


def test_v12_17_keeps_v12_15_capital_and_no_dca_safety_contract() -> None:
    research = _text(RESEARCH_STRATEGY)
    for required in (
        "MAX_STAKE_USDT = 80.0",
        "MAX_TOTAL_CAPITAL_USDT = 250.0",
        "MAX_TOTAL_EXPOSURE_USDT = 240.0",
        "MAX_OPEN_POSITIONS = 3",
        "position_adjustment_enable = False",
        "max_entry_position_adjustment = 0",
        "stoploss = -0.055",
        "can_short = False",
    ):
        assert required in research
    assert 'RECLAIM_PROFILES: ClassVar' in research
    reclaim = research.split("RECLAIM_PROFILES", maxsplit=1)[1].split(
        "REGIME_TREND", maxsplit=1
    )[0]
    assert '"BTC/USDT"' in reclaim
    assert '"ETH/USDT"' in reclaim
    for pair in ("SOL/USDT", "XRP/USDT", "BNB/USDT", "DOGE/USDT", *NEW_FOUR):
        assert f'"{pair}"' not in reclaim


def test_research_ui_exposes_all_ten_pairs_and_22_core_cells() -> None:
    ui = _text(RESEARCH_UI)
    for pair in TEN_PAIRS:
        assert pair in ui
    assert "Chainlink · LINK/USDT · Research" in ui
    assert "TRON · TRX/USDT · Research" in ui
    assert "Litecoin · LTC/USDT · Research" in ui
    assert "Bitcoin Cash · BCH/USDT · Research" in ui
    assert "Alle 22 Backtests" in ui
    assert "Gesamtportfolio · 10 Spot-Pairs" in ui
    assert "maximal eine Position je Paar" in ui
    assert "Alle zehn Märkte konkurrieren chronologisch um dieselben drei Slots" in ui


def test_research_api_is_separate_from_live_strategy_and_results() -> None:
    api = _text(RESEARCH_API)
    assert 'RESEARCH_STRATEGY_NAME = "CompressionBreakout250TenPair"' in api
    assert '"LINK/USDT"' in api
    assert '"TRX/USDT"' in api
    assert '"LTC/USDT"' in api
    assert '"BCH/USDT"' in api
    assert 'base._CONFIG = base._USERDIR / "config-ten-pair-research.json"' in api
    assert '"backtest_results" / "ten_pair_research"' in api
    assert "PLANNED_RESEARCH_ONLY" in api
    assert "current_twenty_cell_matrix" in api


def test_paper_launcher_routes_only_ui_backtests_to_research_facade() -> None:
    runtime = _text(LOCKED_RUNTIME)
    assert "from ten_pair_backtest_api import build_router" in runtime
    # The locked launcher still loads the strategy source explicitly supplied by
    # STARTBOT; the research facade therefore does not replace the running V12.15.
    assert "_load_exact_strategy(" in runtime
    assert "args.strategy_source" in runtime
    assert "args.strategy_sha256" in runtime
