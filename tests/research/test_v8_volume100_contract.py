from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
CONFIG = REPO_ROOT / "runtime" / "user_data" / "config.json"


def _class_constants() -> dict[str, object]:
    tree = ast.parse(STRATEGY.read_text(encoding="utf-8"), filename=str(STRATEGY))
    strategy = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "CompressionBreakout250"
    )
    values: dict[str, object] = {}
    for node in strategy.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name):
            try:
                values[target.id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return values


def test_b1_changes_exactly_the_preregistered_entry_dimension() -> None:
    text = STRATEGY.read_text(encoding="utf-8")
    constants = _class_constants()

    assert constants["RESEARCH_BACKTEST_ONLY"] is True
    assert constants["VOLUME_RATIO_MIN"] == 1.0
    assert '(dataframe["volume_ratio"] >= self.VOLUME_RATIO_MIN)' in text
    assert 'slow_20d_donchian_breakout_vr100' in text

    # The original V8 trend/exit/failure structure must still be present.
    for marker in (
        'rolling(120, min_periods=120).max()',
        'rolling(60, min_periods=60).min()',
        'buy_momentum_30d',
        'buy_adx_4h_min',
        'failed_4h_breakout',
        'slow_trend_exit',
        'stoploss = -0.055',
        'trailing_stop = False',
    ):
        assert marker in text


def test_b1_cannot_place_dryrun_or_live_entries() -> None:
    text = STRATEGY.read_text(encoding="utf-8")
    assert "self.RESEARCH_BACKTEST_ONLY" in text
    assert 'self._runmode_value(self.config) in {' in text
    assert '"live"' in text
    assert '"dry_run"' in text
    assert "return False" in text


def test_b1_does_not_mutate_the_v8_execution_config() -> None:
    # Research B1 is a one-variable strategy experiment. Configuration remains
    # the same frozen 250-USDT spot/long-only envelope used by V8 B0.
    import json

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["dry_run"] is True
    assert config["dry_run_wallet"] == 250
    assert config["available_capital"] == 250
    assert config["stake_amount"] == 80
    assert config["max_open_trades"] == 3
    assert config["minimal_roi"] == {"0": 0.50}
    assert config["stoploss"] == -0.055
    assert config["trailing_stop"] is False
    assert config["trading_mode"] == "spot"
    assert config["margin_mode"] == ""
    assert config["exchange"]["pair_whitelist"] == [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
    ]
