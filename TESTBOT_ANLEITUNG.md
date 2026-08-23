# Testbot starten und bedienen

## Start

`STARTBOT.bat` startet Freqtrade ausschließlich im **Dry-run** mit öffentlichen Binance-Marktdaten. Es werden keine echten Orders gesendet.

Aktueller Entwicklungszweig: `agent/v12-17-ten-pair-research-ui`.

Die tatsächlich geladene Strategy-Datei ist
`runtime/user_data/strategies/CompressionBreakout250.py` mit
`STRATEGY_VERSION = "V12.18"`. Die eingefrorene V8-Datei unter
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

## Was V12.18 macht

Alle zehn Pairs werden mit ihren eigenen 15m/1h/4h-Daten bewertet. Im laufenden
Paperbot teilen sie sich ein einziges 250-USDT-Wallet und höchstens drei
gleichzeitige 80-USDT-Kapitalblöcke. V12.18 behält den bewährten
V12.15-Kern und repariert den Zehn-Paare-/Backtest-Ausbau von V12.17.

- BTC und ETH behalten ihre separat markierten EMA20-Trend-Reclaims.
- SOL, XRP, BNB, DOGE, LINK, TRX, LTC und BCH verwenden keinen
  Reclaim-Challenger, sondern ihren markierten Donchian-/Trendkern.
- Nach zwei unprofitablen Trades eines Pairs innerhalb von 14 Tagen sperrt die
  pair-lokale `LowProfitPairs`-Protection dieses Pair für 72 Stunden.
- Nur bei Champion-Donchian-Trades wird nach mindestens +30 % laufendem Gewinn
  ein +5-%-Stopboden gesetzt; Reclaims und normale Bewegungen bleiben unberührt.
- Eine zweite oder dritte 80-USDT-Stufe ist nur bei positivem Gesamt- und
  Einstiegsergebnis und zu einem Kurs oberhalb aller bisherigen Einstiege
  zulässig. Maximal bleiben es 240 USDT. Ein fallender/verlierender Trade wird
  niemals aufgestockt.
- Der feste Stop-Loss bleibt bei −5,5 %; Verlust-DCA und Shorting bleiben
  deaktiviert.
- Gewinner werden nicht durch den verworfenen SOL-Ratchet abgeschnitten.

V12.18 ist ein Research-/Paper-Kandidat und **kein Profitversprechen**. Die
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

Für die Frage, wie sinnvoll die 250 USDT tatsächlich eingesetzt werden, ist
`Alle 10 zusammen` maßgeblich: alle zehn Pairs teilen dort genau ein
250-USDT-Konto mit höchstens drei 80-USDT-Blöcken. `Gewählten Coin testen`
startet einen Einzeltest. `10 Einzeltests` führt zehn voneinander unabhängige
Diagnosen aus, wobei jede Diagnose erneut mit 250 USDT beginnt; diese 2.500
USDT dürfen nicht als gemeinsames Portfolioergebnis interpretiert werden. Die
Oberfläche zeigt zusätzlich Kapitalzeit, Zeit ohne Position sowie
durchschnittlich und maximal gleichzeitig offene Positionen, Entry-Blöcke und
das maximal gebundene Kapital. Der Dateiaudit
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
