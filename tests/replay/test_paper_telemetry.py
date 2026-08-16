from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from paper_decision_telemetry import install_paper_strategy_telemetry


class FakeFrame:
    empty = True


class FakeStrategy:
    timeframe = "15m"

    def __init__(self, root: Path):
        self.config = {"dry_run": True, "user_data_dir": str(root)}
        self.entry_calls = 0
        self.exit_calls = 0
        self.confirm_calls = 0

    def populate_entry_trend(self, dataframe, metadata):
        self.entry_calls += 1
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        self.exit_calls += 1
        return dataframe

    def confirm_trade_entry(self, **kwargs):
        self.confirm_calls += 1
        return kwargs["pair"] == "BTC/USDT"


def test_wrappers_preserve_original_callback_result_and_call_once(tmp_path: Path) -> None:
    strategy = FakeStrategy(tmp_path)
    install_paper_strategy_telemetry(strategy, "a" * 64)
    frame = FakeFrame()
    assert strategy.populate_entry_trend(frame, {"pair": "BTC/USDT"}) is frame
    assert strategy.populate_exit_trend(frame, {"pair": "BTC/USDT"}) is frame
    allowed = strategy.confirm_trade_entry(
        pair="BTC/USDT",
        order_type="limit",
        amount=1.0,
        rate=100.0,
        time_in_force="GTC",
        current_time=datetime(2026, 1, 1, tzinfo=UTC),
        entry_tag="x",
        side="long",
    )
    assert allowed is True
    assert strategy.entry_calls == 1
    assert strategy.exit_calls == 1
    assert strategy.confirm_calls == 1
    files = list((tmp_path / "paper_telemetry").glob("*.jsonl"))
    assert len(files) == 1
    assert "runtime_entry_confirmation" in files[0].read_text(encoding="utf-8")
