# Testbot starten und bedienen

## Start

`STARTBOT.bat` startet Freqtrade ausschließlich im **Dry-run** mit öffentlichen Binance-Marktdaten. Es werden keine echten Orders gesendet.

Aktueller Entwicklungszweig: `agent/v12-17-ten-pair-research-ui`.

Die tatsächlich geladene Strategy-Datei ist
`runtime/user_data/strategies/CompressionBreakout250.py` mit
`STRATEGY_VERSION = "V12.31"`. Die eingefrorene V8-Datei unter
`research/baselines/V8/` bleibt ausschließlich Baseline für Replay, Reproduktion
und Research-Governance.

## Aktueller Sicherheitsrahmen

- Binance Spot / USDT
- BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, BNB/USDT, DOGE/USDT,
  LINK/USDT, TRX/USDT, LTC/USDT und BCH/USDT
- long-only, 1x
- 250 virtuelle USDT
- maximal 80 USDT je Position
- maximal drei offene Positionen / 240 USDT Exposition
- kein Verlust-Nachkaufen, kein Martingale, kein Futures/Margin/Short
- Hard-Stop bleibt Bestandteil der Strategy-/Config-Grenzen
- kein automatischer Echtgeld-Release

## Was V12.31 macht

Alle zehn Pairs werden mit ihren eigenen 15m/1h/4h-Daten bewertet. Im laufenden
Paperbot teilen sie sich ein einziges 250-USDT-Wallet und höchstens drei
gleichzeitige 80-USDT-Kapitalblöcke. V12.31 behält den bewährten V12.15-Kern,
die V12.18-Sicherheitsreparatur, die schnelle, fortsetzbare V12.19-Laufzeit
und das selektive V12.20-Gewinn-Pyramiding.

- BTC und ETH behalten ihre separat markierten EMA20-Trend-Reclaims.
- SOL, XRP, BNB, LINK, TRX und LTC verwenden keinen Reclaim-Challenger,
  sondern ihren markierten Donchian-/Trendkern.
- DOGE verwendet den 4h-Supertrend(20, 3)-Wechsel oberhalb einer steigenden
  EMA100 und steigt beim Gegenwechsel aus.
- BCH verwendet die feste EMA30/EMA80-Kreuzung oberhalb einer steigenden
  EMA100 bei ADX mindestens 24 und steigt unter EMA80 aus.
- Nur SOL verlangt beim vorhandenen Donchian-Einstieg zusätzlich einen
  bestätigten 4h-ADX von mindestens 21. Andere SOL-Filter bleiben deaktiviert.
- Nach zwei unprofitablen Trades eines Pairs innerhalb von 14 Tagen sperrt die
  pair-lokale `LowProfitPairs`-Protection dieses Pair für 72 Stunden.
- Nur bei Champion-Donchian-Trades wird nach mindestens +30 % laufendem Gewinn
  ein +5-%-Stopboden gesetzt; Reclaims und normale Bewegungen bleiben unberührt.
- Nur BTC, ETH, LINK und TRX dürfen eine zweite oder dritte 80-USDT-Stufe
  erhalten; weiterhin nur bei positivem Gesamt- und Einstiegsergebnis und zu
  einem Kurs oberhalb aller bisherigen Einstiege. SOL, XRP, BNB, DOGE, LTC und
  BCH handeln weiter mit normalen ersten Entries, aber ohne Zusatzblock.
- Der feste Stop-Loss bleibt bei −5,5 %; Verlust-DCA und Shorting bleiben
  deaktiviert.
- Gewinner werden nicht durch den verworfenen SOL-Ratchet abgeschnitten.

V12.31 ist ein Research-/Paper-Kandidat und **kein Profitversprechen**. Die
Änderung erhöht weder Positionsgröße noch Maximalengagement.

## FreqUI

Nach dem Start öffnet der lokale Supervisor die FreqUI auf `127.0.0.1:8080` und überwacht den Prozessbaum. Der Benutzername `testbot` darf angezeigt werden; das Passwort wird ausschließlich aus der ignorierten lokalen Passwortdatei gelesen und nicht im Startfenster ausgegeben. Beim ersten Start mit `PASSWORT_AENDERN.bat` ein eigenes Passwort setzen und den Bot danach neu starten. Diese Anleitung enthält absichtlich keine fest kopierten Zugangsdaten.

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
- `TESTBOT_AUSWERTUNG.bat` – Dry-run-Datenbank sowie alle alten und neuen
  UI-Backtests gemeinsam auswerten.
- `HISTORISCHE_DATEN_LADEN.bat` – historische Daten für Replay/Research vorbereiten.
- `HISTORISCHER_LIVE_REPLAY.bat` – Full-System-Replay.
- `HISTORISCHE_AUSWERTUNG.bat` – Replay-/Research-Diagnostik.
- `STATISTIK_AUDIT.bat` – Trial-/Statistikdiagnostik.

Diese Helfer sind keine alternativen Trading-Strategien.

## Backtest

Der integrierte Backtest verwendet die tatsächlich aktive Strategy-Quelle. Details stehen in `BACKTEST_ANLEITUNG.md`.

`Gewählten Coin testen` startet einen Lauf für die aktuelle Auswahl.
`Alle 10 einzeln testen` führt automatisch zehn voneinander unabhängige Läufe
nacheinander aus, wobei jeder Coin erneut mit 250 USDT beginnt; diese 2.500 USDT
dürfen nicht als gemeinsames Portfolioergebnis interpretiert werden. Der
Batch wird nach jedem Coin lokal gespeichert und läuft beim Verlassen der
Backtest-Seite weiter. Ein unterbrochener Batch kann nach einem Neustart
fortgesetzt werden, ohne fertige identische Coin-Tests erneut zu rechnen. Der
gemeinsame Portfolio-Lauf bleibt intern für Replay/Audit verfügbar und wird
nicht als dritter UI-Knopf gezeigt. Die Oberfläche zeigt zusätzlich Kapitalzeit,
Zeit ohne Position sowie durchschnittlich und maximal gleichzeitig offene
Positionen, Entry-Blöcke und das maximal gebundene Kapital. Der Dateiaudit
stoppt einen Lauf, sobald eine unerwartete Strategy-, Config-, Candle- oder
Repo-Datei beziehungsweise ein Kindprozess verwendet wird.

V12-Optimizer- und Family-League-Runs sind davon getrennte Research-Werkzeuge. Ein Research-Gewinner wird nicht automatisch in den laufenden Bot übernommen.

## Lokale Daten

Marktdaten, Backtest-/Replay-Artefakte, Logs, lokale Datenbanken und Zugangsdaten bleiben lokal und gehören nicht in Git.

Automatisch erzeugte Dateien bleiben geordnet unter `runtime/user_data/`:

- `data/` – notwendige lokale Kerzendaten
- `backtest_results/` – nachvollziehbare Backtest-Rohresultate
- `logs/sessions/` – Laufprotokolle, Manifest und Abschlussbericht je Sitzung
- `paper_telemetry/` und `replay_results/` – Paritäts-/Auditdaten
- `tradesv8.dryrun.sqlite*` – persistenter aktueller Dry-run-Zustand

Die beim ersten Setup erzeugte `.venv/` im Repository-Stamm ist die benötigte,
gelockte Python-/Freqtrade-Umgebung und bleibt von Git ausgeschlossen. Bot und
UI schreiben dort keine Sitzungs-, Markt- oder Ergebnisdateien.
Wegwerfbarer Python-Bytecode-Cache wird in den Startpfaden deaktiviert.
Audit-, Replay-, Backtest- und Dry-run-Daten werden nicht automatisch gelöscht.
Nach jedem neuen UI-Backtest wird eine Gesamtauswertung aller erhaltenen Läufe
als Markdown und JSON unter `runtime/user_data/backtest_results/ui/` erneuert.
Historische Datenbanken aus älteren Strategiephasen werden vom aktuellen
Testbot nicht neu erzeugt; eine Entfernung darf nur bei beendetem Bot und nach
bewusster Prüfung erfolgen.

## Maßgebliche Projektunterlagen

- `START_HERE_DE.md`
- `RESEARCH_MASTERPLAN_DE.md`
- `docs/DEEP_RESEARCH_GAP_AUDIT_DE.md`
- `research/trial_ledger.csv`

Ältere V8/V9/V10/V11-Statusberichte sind historische Evidenz und keine parallelen aktuellen Anweisungen.
