from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRATEGY = ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
LEDGER = ROOT / "research" / "trial_ledger.csv"
REPORT = ROOT / "research" / "V12_31_DOGE_BCH_COMBINATION_DE.md"
API = ROOT / "runtime" / "ten_pair_backtest_api.py"


def test_v12_31_combines_fixed_doge_and_bch_routes() -> None:
    source = STRATEGY.read_text(encoding="utf-8")

    assert 'STRATEGY_VERSION = "V12.33"' in source
    assert '"v12_30_doge_supertrend20x3"' in source
    assert '"v12_30_doge_supertrend_exit"' in source
    assert 'dataframe["bch_ema_fast"] = ta.EMA(dataframe, timeperiod=30)' in source
    assert 'dataframe["bch_ema_slow"] = ta.EMA(dataframe, timeperiod=80)' in source
    assert 'dataframe["bch_ema_macro"] = ta.EMA(dataframe, timeperiod=100)' in source
    assert 'dataframe["adx_4h"] >= 24' in source
    assert '"v12_31_bch_ema30_80_trend"' in source
    assert '"v12_31_bch_ema30_80_exit"' in source


def test_v12_31_preserves_single_block_bch_and_global_capital_rules() -> None:
    source = STRATEGY.read_text(encoding="utf-8")
    pyramid_set = source.split("PYRAMIDING_PAIRS", 1)[1].split("}", 1)[0]

    assert '"BCH/USDT",' not in pyramid_set
    assert "MAX_STAKE_USDT = 80.0" in source
    assert "MAX_TOTAL_CAPITAL_USDT = 250.0" in source
    assert "MAX_TOTAL_EXPOSURE_USDT = 240.0" in source
    assert "MAX_OPEN_POSITIONS = 3" in source


def test_v12_31_exact_result_and_active_api_are_documented() -> None:
    ledger = LEDGER.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    api = API.read_text(encoding="utf-8")

    assert '"V12.31-DOGE-BCH-FIXED-ROUTE-COMBINATION"' in ledger
    assert '"KEEP_BETTER_TEN_PAIR_PAPER_CANDIDATE"' in ledger
    assert "669,857 USDT" in report
    assert "+419,8571 USDT" in report
    assert "12,5447 Prozent" in report
    assert 'base.STRATEGY_VERSION = "V12.33"' in api
    assert 'ACTIVE_EXPERIMENT_ID = "V12.33-LTC-NO-TRADE-COUNTERFACTUAL"' in api
