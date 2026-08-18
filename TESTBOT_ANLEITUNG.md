# Testbot starten und bedienen

## Start

`STARTBOT.bat` startet Freqtrade ausschließlich im **Dry-run** mit öffentlichen Binance-Marktdaten. Es werden keine echten Orders gesendet.

Aktueller Entwicklungszweig: `agent/v12-adaptive-league`.

Wichtig: V12 ist Research-Infrastruktur. Die tatsächlich geladene Strategy-Datei ist aktuell weiterhin `runtime/user_data/strategies/CompressionBreakout250.py` mit `STRATEGY_VERSION = "V11"`.

## Aktueller Sicherheitsrahmen

- Binance Spot / USDT
- BTC/USDT, ETH/USDT, SOL/USDT
- long-only, 1x
- 250 virtuelle USDT
- maximal 80 USDT je Position
- maximal drei offene Positionen / 240 USDT Exposition
- kein DCA, kein Martingale, kein Futures/Margin/Short
- Hard-Stop bleibt Bestandteil der Strategy-/Config-Grenzen
- kein automatischer Echtgeld-Release

## Was V11 macht

BTC, ETH und SOL werden unabhängig voneinander bewertet. Jedes Pair nutzt nur seine eigenen 15m/1h/4h-Daten und klassifiziert den Markt in:

- `TREND/BREAKOUT`
- `RANGE/MEAN_REVERSION`
- `NO_TRADE`

Danach kann V11 zwischen den deterministischen Familien `ORB_RETEST`, `ICHIMOKU_TREND` und `BOLLINGER_MR` routen.

V11 ist ein Research-/Paper-Kandidat und **kein Profitversprechen**.

## FreqUI

Nach dem Start öffnet der lokale Supervisor die FreqUI auf `127.0.0.1:8080` und überwacht den Prozessbaum. Zugangsdaten werden vom Starter selbst angezeigt bzw. aus der lokalen Passwortdatei gelesen. Diese Anleitung enthält absichtlich keine fest kopierten Zugangsdaten.

Für einen unveränderten Beobachtungstest sollten keine manuellen Force-Entry-/Force-Exit-Aktionen verwendet werden.

## Beenden

- `Strg+C` im Konsolenfenster: kontrollierter Shutdown.
- Konsolenfenster schließen: fail-closed; der überwachte Prozessbaum soll beendet werden.
- überwachte Testbot-UI schließen: Supervisor beendet den Bot.
- nach Neustart von Windows startet der Bot nicht automatisch; `STARTBOT.bat` erneut ausführen.

## Hilfsdateien

Diese Dateien bleiben bewusst erhalten, weil sie unterschiedliche Betriebs-/Research-Aufgaben haben:

- `STOP_NEUE_TESTTRADES.bat` – neue simulierte Entries sperren.
- `TESTTRADES_FREIGEBEN.bat` – Test-Entry-Sperre wieder entfernen.
- `TESTBOT_AUSWERTUNG.bat` – lokale Dry-run-Auswertung.
- `HISTORISCHE_DATEN_LADEN.bat` – historische Daten für Replay/Research vorbereiten.
- `HISTORISCHER_LIVE_REPLAY.bat` – Full-System-Replay.
- `HISTORISCHE_AUSWERTUNG.bat` – Replay-/Research-Diagnostik.
- `STATISTIK_AUDIT.bat` – Trial-/Statistikdiagnostik.

Diese Helfer sind keine alternativen Trading-Strategien.

## Backtest

Der integrierte Backtest verwendet die tatsächlich aktive Strategy-Quelle. Details stehen in `BACKTEST_ANLEITUNG.md`.

V12-Optimizer- und Family-League-Runs sind davon getrennte Research-Werkzeuge. Ein Research-Gewinner wird nicht automatisch in den laufenden Bot übernommen.

## Lokale Daten

Marktdaten, Backtest-/Replay-Artefakte, Logs, lokale Datenbanken und Zugangsdaten bleiben lokal und gehören nicht in Git.

Historische Datenbanken aus älteren Strategiephasen dürfen zur Nachvollziehbarkeit erhalten bleiben, müssen aber klar von neuen Kandidaten getrennt werden. Eine Änderung des aktiven DB-Pfads ist eine bewusste Runtime-Migration und kein reiner Dokumentations-Cleanup.

## Maßgebliche Projektunterlagen

- `START_HERE_DE.md`
- `RESEARCH_MASTERPLAN_DE.md`
- `docs/DEEP_RESEARCH_GAP_AUDIT_DE.md`
- `research/trial_ledger.csv`

Ältere V8/V9/V10/V11-Statusberichte sind historische Evidenz und keine parallelen aktuellen Anweisungen.
