from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
REPORT = ROOT / "research" / "V12_33_LTC_NO_TRADE_DE.md"


def test_v12_33_disables_only_ltc_entries() -> None:
    source = STRATEGY.read_text(encoding="utf-8")
    ltc_branch = source.split('if pair == "LTC/USDT":', 1)[1].split(
        'if pair == "DOGE/USDT":', 1
    )[0]

    assert 'STRATEGY_VERSION = "V12.33"' in source
    assert 'dataframe["enter_long"] = 0' in ltc_branch
    assert '"v12_33_ltc_no_validated_edge"' in ltc_branch
    assert '"v12_30_doge_supertrend20x3"' in source
    assert '"v12_31_bch_ema30_80_trend"' in source


def test_v12_33_preregistered_capital_and_acceptance_contract() -> None:
    source = STRATEGY.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")

    assert "MAX_STAKE_USDT = 80.0" in source
    assert "MAX_TOTAL_CAPITAL_USDT = 250.0" in source
    assert "MAX_TOTAL_EXPOSURE_USDT = 240.0" in source
    assert "MAX_OPEN_POSITIONS = 3" in source
    assert "+419,8571 USDT" in report
    assert "mindestens 2,4358" in report
    assert "höchstens 12,5447 Prozent" in report
    assert "erst nach vollständig geschlossenem Trade" in report
