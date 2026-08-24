from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"


def test_v12_30_doge_route_is_preserved_by_the_active_challenger() -> None:
    source = STRATEGY.read_text(encoding="utf-8")
    pyramid_set = source.split("PYRAMIDING_PAIRS", 1)[1].split("}", 1)[0]

    assert 'STRATEGY_VERSION = "V12.33"' in source
    assert "period=20, multiplier=3.0" in source
    assert 'dataframe["close_4h"] > dataframe["ema_macro100_4h"]' in source
    assert 'dataframe["ema_macro100_rising_12_4h"] > 0' in source
    assert '"v12_30_doge_supertrend20x3"' in source
    assert '"v12_30_doge_supertrend_exit"' in source
    assert '"DOGE/USDT",' not in pyramid_set


def test_v12_30_preserves_v12_22_sol_and_capital_contracts() -> None:
    source = STRATEGY.read_text(encoding="utf-8")

    assert 'elif pair == "SOL/USDT":' in source
    assert 'self.PAIR_PROFILES[pair]["adx_min"]' in source
    assert "MAX_STAKE_USDT = 80.0" in source
    assert "MAX_TOTAL_CAPITAL_USDT = 250.0" in source
    assert "MAX_TOTAL_EXPOSURE_USDT = 240.0" in source
    assert "MAX_OPEN_POSITIONS = 3" in source
    assert '"BTC/USDT",' in source
    assert '"BCH/USDT",' in source
