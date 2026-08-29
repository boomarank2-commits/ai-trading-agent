# Upload-Manifest fuer GPT Deep Research

## Pflichtdateien

Die portable ZIP-Datei soll diese Gruppen enthalten:

1. Alle Dateien aus research/deep_research_10_coins/.
2. RESEARCH_MASTERPLAN_DE.md, BACKTEST_ANLEITUNG.md und START_HERE_DE.md.
3. research/trial_ledger.csv und
   research/executed_test_fingerprints.csv.
4. research/V12_20_SELECTIVE_PYRAMID_DE.md,
   V12_22_SOL_ADX21_DE.md, V12_23_LTC_EMA_TREND_DE.md,
   V12_24_LTC_SLOT_RESERVE_DE.md, V12_26_BCH_EMA_TREND_FIX_DE.md,
   V12_28_TRX_SINGLE_BLOCK_DE.md, V12_29_BNB_DONCHIAN80_DE.md,
   V12_30_DOGE_SUPERTREND_DE.md,
   V12_31_DOGE_BCH_COMBINATION_DE.md,
   V12_32_LTC_ROUTE_COMBINATION_DE.md und
   PAIR_SCREEN_V2_SOL_LTC_REJECTED_DE.md.
5. runtime/user_data/strategies/CompressionBreakout250.py und
   runtime/user_data/config-public.json.
6. runtime/locked_backtest_freqtrade.py,
   runtime/ten_pair_backtest_api.py und
   research/causal_pair_route_screen.py.
7. Die relevanten Vertrags- und Versions-Tests fuer V12.22 bis V12.32.

## Optionale historische Evidenz

Der alte automatische V12.20-Zehn-Einzeltest-Batch und die gespeicherten
Pair-Historien duerfen als historische Rohquelle mitgegeben werden, wenn ihr
Ordner deutlich HISTORISCH_V12_20 heisst. Sie duerfen nicht als aktueller
V12.31-Lauf bezeichnet werden.

## Ausdruecklich nicht hochladen

- .env, private Konfigurationen oder Exchange-/UI-Zugangsdaten;
- Logs, Datenbanken, Locks, Prozessdateien oder Paper-Telemetrie;
- runtime/user_data/data mit den grossen OHLCV-Dateien;
- komplette backtest_results-Verzeichnisse oder alte Ergebnis-ZIPs;
- .venv, Cache-Verzeichnisse oder generierte Build-Artefakte;
- echte API-Keys, Passwoerter, JWT-Secrets oder WebSocket-Tokens.

Die oeffentliche Konfiguration enthaelt nur Platzhalter. Vor dem Packen muss
trotzdem nach api_key, secret, password, jwt, token und privaten Schluesseln
gesucht werden. Treffer aus Platzhaltertexten werden manuell verifiziert;
echte Werte verhindern die Freigabe des Pakets.

## Aktualitaetsregel

Die ZIP-Datei muss im Namen V12_31 und das Datum tragen. Nach jeder neuen
Strategieversion wird ein neues Paket gebaut. Alte Pakete werden nicht
ueberschrieben und nicht als aktuelle Quelle weitergereicht.
