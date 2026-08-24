from __future__ import annotations

import ast
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME = REPO_ROOT / "runtime"
USER_DATA = RUNTIME / "user_data"
CONFIG_PATH = USER_DATA / "config.json"
LIVE_OVERLAY_PATH = USER_DATA / "config-live.example.json"
PUBLIC_OVERLAY_PATH = USER_DATA / "config-public.json"
STRATEGY_PATH = USER_DATA / "strategies" / "CompressionBreakout250.py"

TEN_PAIRS = [
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
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _strategy_class() -> tuple[str, ast.ClassDef]:
    source = STRATEGY_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(STRATEGY_PATH))
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "CompressionBreakout250"
    )
    return source, cls


def _literal_assignment(cls: ast.ClassDef, name: str):
    for node in cls.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f"Class assignment {name!r} not found")


def test_active_paper_config_is_ten_pair_spot_and_three_80_chunks() -> None:
    config = load_json(CONFIG_PATH)
    assert config["dry_run"] is True
    assert config["dry_run_wallet"] == 250
    assert config["available_capital"] == 250
    assert config["stake_amount"] == 80
    assert config["max_open_trades"] == 3
    assert config["stake_amount"] * config["max_open_trades"] == 240
    assert config["stake_currency"] == "USDT"
    assert config["trading_mode"] == "spot"
    assert config["margin_mode"] == ""
    assert config["position_adjustment_enable"] is True
    assert config["max_entry_position_adjustment"] == 2
    assert config["exchange"]["name"] == "binance"
    assert config["exchange"]["pair_whitelist"] == TEN_PAIRS
    assert config["exchange"]["pair_blacklist"] == []
    assert config["pairlists"] == [{"method": "StaticPairList"}]


def test_v12_22_preserves_v12_20_cap_and_adjustment_contract() -> None:
    source, cls = _strategy_class()
    assert _literal_assignment(cls, "STRATEGY_VERSION") == "V12.30"
    assert _literal_assignment(cls, "PYRAMIDING_PAIRS") == {
        "BTC/USDT",
        "ETH/USDT",
        "LINK/USDT",
        "TRX/USDT",
    }
    assert _literal_assignment(cls, "position_adjustment_on_new_strategy_candle_only") is True
    assert _literal_assignment(cls, "can_short") is False
    assert _literal_assignment(cls, "position_adjustment_enable") is True
    assert _literal_assignment(cls, "max_entry_position_adjustment") == 2
    assert _literal_assignment(cls, "MAX_STAKE_USDT") == 80.0
    assert _literal_assignment(cls, "MAX_TOTAL_CAPITAL_USDT") == 250.0
    assert _literal_assignment(cls, "MAX_TOTAL_EXPOSURE_USDT") == 240.0
    assert _literal_assignment(cls, "MAX_OPEN_POSITIONS") == 3
    assert _literal_assignment(cls, "MAX_ENTRIES_PER_PAIR") == 3
    assert "def adjust_trade_position(" in source
    assert "Trade.total_open_trades_stakes()" in source
    assert "Trade.get_open_trade_count()" in source
    assert "date_last_filled_utc" in source
    assert "selective_pyramid_chunk" in source
    assert "current_profit <= 0.0" in source
    assert "select_filled_orders" in source
    assert "enter_short" not in source


def test_strategy_signal_generation_remains_causal() -> None:
    source, cls = _strategy_class()
    signal_methods = {
        "populate_indicators",
        "populate_indicators_1h",
        "populate_indicators_4h",
        "populate_entry_trend",
        "populate_exit_trend",
    }
    for node in cls.body:
        if not isinstance(node, ast.FunctionDef) or node.name not in signal_methods:
            continue
        method = ast.get_source_segment(source, node) or ""
        compact = method.replace(" ", "")
        assert "shift(-" not in compact, node.name
        assert "iloc[-1]" not in compact, node.name
        assert "iat[-1]" not in compact, node.name
        assert "center=True" not in compact, node.name


def test_runtime_entry_and_protection_callbacks_remain_present() -> None:
    source, cls = _strategy_class()
    methods = {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}
    assert {
        "populate_indicators",
        "populate_entry_trend",
        "populate_exit_trend",
        "adjust_trade_position",
        "custom_stake_amount",
        "confirm_trade_entry",
        "bot_start",
        "custom_stoploss",
        "custom_exit",
    }.issubset(methods)
    assert '"method": "CooldownPeriod"' in source
    assert '"method": "StoplossGuard"' in source
    assert '"method": "MaxDrawdown"' in source
    assert '"method": "LowProfitPairs"' in source
    assert '"max_allowed_drawdown": 0.08' in source
    assert "STOP_ENTRIES" in source
    assert "execution safety contract failed" in source


def test_real_money_overlay_remains_paused_and_not_promoted_with_new_paper_rules() -> None:
    live = load_json(LIVE_OVERLAY_PATH)
    assert live["dry_run"] is False
    assert live["initial_state"] == "paused"
    assert live["cancel_open_orders_on_exit"] is False
    assert live["position_adjustment_enable"] is False
    assert live["max_entry_position_adjustment"] == 0
    assert live["exchange"].get("key", "") == ""
    assert live["exchange"].get("secret", "") == ""
    assert "FREQTRADE__EXCHANGE__KEY" in live["_comment"]
    assert "FREQTRADE__EXCHANGE__SECRET" in live["_comment"]
    trust = load_json(RUNTIME / "trusted-live-artifacts.json")
    assert trust == {"schema_version": 1, "artifacts": []}


def test_public_overlay_keeps_exchange_discovery_public_and_api_local() -> None:
    public = load_json(PUBLIC_OVERLAY_PATH)
    exchange = public["exchange"]
    assert exchange["enable_ws"] is False
    assert exchange["ccxt_config"]["apiKey"] is None
    assert exchange["ccxt_async_config"]["apiKey"] is None
    assert "secret" not in exchange["ccxt_config"]
    assert "secret" not in exchange["ccxt_async_config"]
    api = public["api_server"]
    assert api["enabled"] is True
    assert api["listen_ip_address"] == "127.0.0.1"
    assert api["listen_port"] == 8080
    assert api["enable_openapi"] is False
    assert api["CORS_origins"] == []


def test_dependency_and_image_are_pinned_to_freqtrade_2026_7() -> None:
    requirement_text = (RUNTIME / "requirements-freqtrade.txt").read_text(
        encoding="utf-8"
    )
    requirement_lines = [
        line.strip()
        for line in requirement_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert requirement_lines == ["freqtrade==2026.7"]
    compose = (RUNTIME / "docker-compose.yml").read_text(encoding="utf-8")
    assert "image: freqtradeorg/freqtrade:2026.7" in compose


def test_native_scripts_keep_public_overlay_and_locked_runtime_path() -> None:
    scripts = RUNTIME / "scripts"
    for filename in ("download-data.ps1", "backtest.ps1", "start-dryrun.ps1"):
        source = (scripts / filename).read_text(encoding="utf-8")
        assert "$script:PublicOverlayPath" in source
    launcher = (scripts / "start-testbot-24x7.ps1").read_text(encoding="utf-8")
    assert "locked_freqtrade.py" in launcher
    assert "validate_dryrun_config.py" in launcher
    assert "tradesv8.dryrun.sqlite" in launcher

    cleanup = (scripts / "cleanup-stale-testbot.ps1").read_text(encoding="utf-8")
    assert "Close-StaleSessionManifests" in cleanup
    assert '$manifest.status = "interrupted"' in cleanup
    assert '"not_created_for_forced_shutdown"' in cleanup


def test_long_financial_e2e_is_manual_and_not_duplicated_in_fast_ci() -> None:
    workflows = REPO_ROOT / ".github" / "workflows"
    fast_ci = (workflows / "windows-backtest-ui-ci.yml").read_text(encoding="utf-8")
    manual_e2e = (workflows / "v12-17-link-3y-e2e.yml").read_text(encoding="utf-8")
    trigger_block = manual_e2e.split("permissions:", maxsplit=1)[0]

    assert "link-3y-e2e:" not in fast_ci
    assert "workflow_dispatch:" in trigger_block
    assert "\n  push:" not in trigger_block
    assert "\n  pull_request:" not in trigger_block
