from pathlib import Path

api = Path('runtime/testbot_backtest_api.py')
s = api.read_text(encoding='utf-8')

s = s.replace(
    '_RESULTS_ROOT = _USERDIR / "backtest_results" / "ui"\n',
    '_RESULTS_ROOT = _USERDIR / "backtest_results" / "ui"\n_DATA_ROOT = _USERDIR / "data" / "binance"\n',
    1,
)

needle = '''def _run_checked(args: list[str], log_path: Path) -> None:\n'''
helpers = '''def _timeframe_delta(timeframe: str) -> timedelta:\n    seconds = {"1m": 60, "15m": 15 * 60, "1h": 60 * 60, "4h": 4 * 60 * 60}\n    try:\n        return timedelta(seconds=seconds[timeframe])\n    except KeyError as exc:\n        raise RuntimeError(f"Unbekannter Backtest-Timeframe: {timeframe}") from exc\n\n\ndef _candle_path(pair: str, timeframe: str) -> Path:\n    return _DATA_ROOT / f"{pair.replace('/', '_')}-{timeframe}.feather"\n\n\ndef _inspect_candle_file(\n    path: Path,\n    timeframe: str,\n    required_start: datetime,\n    required_end: datetime,\n) -> dict[str, Any]:\n    """Validate the exact candle timestamps Freqtrade will read, fail closed on corruption."""\n\n    import pandas as pd\n\n    if not path.is_file():\n        raise RuntimeError(f"Marktdaten-Datei fehlt: {path}")\n    frame = pd.read_feather(path, columns=["date"])\n    if frame.empty:\n        raise RuntimeError(f"Marktdaten-Datei ist leer: {path}")\n\n    dates = pd.to_datetime(frame["date"], utc=True, errors="raise")\n    delta = _timeframe_delta(timeframe)\n    window_start = required_start.astimezone(UTC).replace(\n        hour=0, minute=0, second=0, microsecond=0\n    )\n    in_window = dates[(dates >= window_start) & (dates <= required_end + delta)]\n    if in_window.empty:\n        raise RuntimeError(\n            f"Keine {timeframe}-Kerzen im benoetigten Zeitraum in {path.name}."\n        )\n\n    duplicates = int(in_window.duplicated().sum())\n    diffs = in_window.diff().dropna()\n    non_increasing = int((diffs <= timedelta(0)).sum())\n    gaps = int((diffs > delta).sum())\n    first = in_window.iloc[0].to_pydatetime()\n    last = in_window.iloc[-1].to_pydatetime()\n\n    if duplicates or non_increasing or gaps:\n        raise RuntimeError(\n            "Marktdaten-Integritaet fehlgeschlagen fuer "\n            f"{path.name}: Duplikate={duplicates}, unsortiert={non_increasing}, "\n            f"Luecken={gaps}. Backtest wird nicht gestartet."\n        )\n    if first > window_start + delta:\n        raise RuntimeError(\n            f"Marktdaten beginnen zu spaet fuer {path.name}: {first.isoformat()} "\n            f"statt spaetestens {(window_start + delta).isoformat()}."\n        )\n    # The newest still-open candle need not be present. Two completed intervals\n    # of tolerance cover exchange/update timing without accepting stale history.\n    if last < required_end - (2 * delta):\n        raise RuntimeError(\n            f"Marktdaten enden zu frueh fuer {path.name}: {last.isoformat()} "\n            f"bei Pruefzeit {required_end.isoformat()}."\n        )\n\n    return {\n        "file": path.name,\n        "timeframe": timeframe,\n        "rows_in_required_window": int(len(in_window)),\n        "first": first.isoformat(),\n        "last": last.isoformat(),\n        "duplicates": duplicates,\n        "gaps": gaps,\n    }\n\n\ndef _validate_candle_data(\n    pair: str, download_start: datetime, required_end: datetime\n) -> list[dict[str, Any]]:\n    checks = [\n        _inspect_candle_file(\n            _candle_path(pair, timeframe), timeframe, download_start, required_end\n        )\n        for timeframe in REQUIRED_TIMEFRAMES\n    ]\n    btc_context = _btc_context_pair(pair)\n    if btc_context:\n        context_path = _candle_path(btc_context, "4h")\n        if context_path != _candle_path(pair, "4h"):\n            checks.append(\n                _inspect_candle_file(\n                    context_path, "4h", download_start, required_end\n                )\n            )\n    return checks\n\n\n'''
if helpers not in s:
    s = s.replace(needle, helpers + needle, 1)

old = '''        _set_state(stage="Historische Daten geladen - Backtest startet", progress=45)\n        backtest_args = [\n'''
new = '''        _set_state(stage="Kerzendaten werden auf Luecken und Duplikate geprueft", progress=38)\n        data_integrity = _validate_candle_data(pair, download_start, now)\n\n        _set_state(stage="Historische Daten geladen - Backtest startet", progress=45)\n        backtest_args = [\n'''
s = s.replace(old, new, 1)

old2 = '''        result = _extract_result(result_file, pair, years, strategy_hash)\n        _validate_result_coverage(result, requested_start, now, years)\n'''
new2 = '''        result = _extract_result(result_file, pair, years, strategy_hash)\n        _validate_result_coverage(result, requested_start, now, years)\n        result["data_integrity_validated"] = True\n        result["data_integrity"] = data_integrity\n'''
s = s.replace(old2, new2, 1)
api.write_text(s, encoding='utf-8')

ui = Path('runtime/ui/testbot-backtest.js')
u = ui.read_text(encoding='utf-8')
old_note = '''Tatsächlicher Freqtrade-Zeitraum: ${r.backtest_start || "?"} bis ${r.backtest_end || "?"} (${Number(r.backtest_days || 0)} Tage), serverseitig gegen den angeforderten Zeitraum geprüft.'''
new_note = '''Tatsächlicher Freqtrade-Zeitraum: ${r.backtest_start || "?"} bis ${r.backtest_end || "?"} (${Number(r.backtest_days || 0)} Tage), serverseitig gegen den angeforderten Zeitraum geprüft. Kerzendaten: ${r.data_integrity_validated ? "Lücken/Duplikate/Abdeckung geprüft" : "keine Integritätsbestätigung"}.'''
u = u.replace(old_note, new_note)
ui.write_text(u, encoding='utf-8')
