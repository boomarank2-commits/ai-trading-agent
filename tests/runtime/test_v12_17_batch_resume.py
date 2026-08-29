from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from runtime import ten_pair_backtest_api as adapter


def test_duplicate_completed_pair_reuses_existing_result(monkeypatch) -> None:
    request = SimpleNamespace(pair="ETH/USDT", years=3)
    state: dict[str, object] = {}
    existing = {
        "run_id": "old-eth-run",
        "pair": "ETH/USDT",
        "years": 3,
        "profit_usdt": 12.5,
        "trades": 7,
        "reused_existing_result": True,
    }

    def duplicate(_request: object) -> dict[str, object]:
        raise HTTPException(status_code=409, detail="Doppeltest blockiert: bereits vorhanden")

    monkeypatch.setattr(adapter.base, "start_backtest", duplicate)
    monkeypatch.setattr(adapter, "_existing_completed_result", lambda _request: dict(existing))
    monkeypatch.setattr(adapter.base, "_set_state", lambda **values: state.update(values))
    monkeypatch.setattr(adapter.base, "get_state", lambda: dict(state))

    result = adapter.start_backtest(request)

    assert result["status"] == "completed"
    assert result["stage"].startswith("Vorhandenes identisches Ergebnis geladen")
    assert result["run_id"] == "old-eth-run"
    assert result["pair"] == "ETH/USDT"
    assert result["years"] == 3
    assert result["result"] == existing


def test_duplicate_without_completed_archive_remains_blocked(monkeypatch) -> None:
    request = SimpleNamespace(pair="BTC/USDT", years=3)

    def duplicate(_request: object) -> dict[str, object]:
        raise HTTPException(status_code=409, detail="Doppeltest blockiert: kein fertiges Archiv")

    monkeypatch.setattr(adapter.base, "start_backtest", duplicate)
    monkeypatch.setattr(adapter, "_existing_completed_result", lambda _request: None)

    with pytest.raises(HTTPException) as exc_info:
        adapter.start_backtest(request)

    assert exc_info.value.status_code == 409
