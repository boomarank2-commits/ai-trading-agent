from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from paper_decision_telemetry import install_paper_strategy_telemetry  # noqa: E402


class FakeFrame:
    empty = True


class FakeStrategy:
    timeframe = "15m"

    def __init__(self, root: Path):
        self.config = {
            "dry_run": True,
            "user_data_dir": str(root),
            "stake_currency": "USDT",
            "stake_amount": 80,
            "dry_run_wallet": 250,
            "max_open_trades": 3,
            "trading_mode": "spot",
            "exchange": {
                "name": "binance",
                "pair_whitelist": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
                "key": "MUST_NOT_BE_LOGGED",
                "secret": "MUST_NOT_BE_LOGGED",
            },
        }
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


def _confirm(strategy: FakeStrategy, pair: str) -> bool:
    return strategy.confirm_trade_entry(
        pair=pair,
        order_type="limit",
        amount=1.0,
        rate=100.0,
        time_in_force="GTC",
        current_time=datetime(2026, 1, 1, tzinfo=UTC),
        entry_tag="x",
        side="long",
    )


def test_wrappers_preserve_original_callback_result_and_call_once(tmp_path: Path) -> None:
    strategy = FakeStrategy(tmp_path)
    install_paper_strategy_telemetry(strategy, "a" * 64)
    frame = FakeFrame()
    assert strategy.populate_entry_trend(frame, {"pair": "BTC/USDT"}) is frame
    assert strategy.populate_exit_trend(frame, {"pair": "BTC/USDT"}) is frame
    assert _confirm(strategy, "BTC/USDT") is True
    assert strategy.entry_calls == 1
    assert strategy.exit_calls == 1
    assert strategy.confirm_calls == 1

    files = list((tmp_path / "paper_telemetry").glob("*.jsonl"))
    assert len(files) == 1
    records = [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]
    confirmation = next(record for record in records if record["type"] == "runtime_entry_confirmation")
    assert confirmation["entry_allowed"] is True
    assert confirmation["entry_rejection_reason"] is None
    assert confirmation["mode"] == "paper"
    assert confirmation["experiment_id"] == "V8-PAPER-FORWARD"
    assert confirmation["strategy_name"] == "FakeStrategy"
    assert confirmation["strategy_sha256_raw"] == "a" * 64
    assert len(confirmation["config_hash"]) == 64
    assert len(confirmation["risk_policy_hash"]) == 64
    assert confirmation["data_manifest_hash"] is None
    assert confirmation["run_id"].startswith("paper-")

    raw = files[0].read_text(encoding="utf-8")
    assert "MUST_NOT_BE_LOGGED" not in raw


def test_rejected_entry_gets_generic_reason_without_reimplementing_risk_logic(tmp_path: Path) -> None:
    strategy = FakeStrategy(tmp_path)
    install_paper_strategy_telemetry(strategy, "b" * 64)
    assert _confirm(strategy, "ETH/USDT") is False

    file = next((tmp_path / "paper_telemetry").glob("*.jsonl"))
    records = [json.loads(line) for line in file.read_text(encoding="utf-8").splitlines()]
    confirmation = next(record for record in records if record["type"] == "runtime_entry_confirmation")
    assert confirmation["entry_allowed"] is False
    assert confirmation["entry_rejection_reason"] == "v8_confirm_trade_entry_rejected"
    assert strategy.confirm_calls == 1
