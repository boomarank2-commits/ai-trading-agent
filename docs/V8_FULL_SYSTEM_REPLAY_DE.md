# V8 Full-System-Replay und Paper-Parität

Stand: 16.08.2026

## Ziel

Der eingefrorene V8-Champion `CompressionBreakout250` bleibt in seiner Signaldatei unverändert. Der neue Replay-Pfad ist **keine zweite Handelsstrategie**. Er lädt die exakt gehashte V8-Quelle, ruft deren eigene Indicator-/Entry-/Exit-/`custom_exit`-Callbacks auf und setzt die Entscheidungen anschließend in einer separaten historischen State-Machine um.

Der Replay dient ausschließlich Research und Robustheitsprüfung. Er sendet keine Exchange-Order und benötigt keine API-Keys.

## Sicherheitsvertrag

- Binance Spot / USDT
- long-only / 1x
- Startkapital 250 USDT
- maximal 80 USDT je Position
- maximal drei Positionen / 240 USDT Exposure
- Hard-Stop -5,5 %
- effektives ROI-Ziel aus der Runtime-Config: +50 %
- 0,2 % Fee je Seite als Standard; per CLI stressbar
- Daily-Closed-Loss-Guard 10 USDT
- Cooldown, StoplossGuard und MaxDrawdown-Lock werden im Replay als deterministischer Portfoliozustand geführt
- Kill-Switch und Data-Health sind fail-closed für neue Entries
- `STARTBOT.bat` und der Windows-Kill-on-close-Lebenszyklus werden nicht verändert
- Replay-, Paper-Telemetrie- und Backtest-Artefakte bleiben getrennt

## Zeitmodell

Die Simulationsuhr ist monoton. Eine 15m-Strategieentscheidung wird erst nach Abschluss der Signal-Candle sichtbar. Ein Signal aus der 00:00-Candle ist damit frühestens um 00:15 bekannt; eine simulierte Order darf frühestens in der 1m-Candle ab 00:15 gefüllt werden.

1h- und 4h-Informative-Candles werden mit ihrer **Close-Zeit** as-of gemerged. Eine 4h-Candle mit Open 00:00 darf folglich erst ab 04:00 in einer abgeschlossenen 15m-Entscheidung auftauchen.

Wenn Stop und ROI in derselben 1m-Detail-Candle berührt werden, wird konservativ zuerst der adverse Stop ausgewertet.

## Komponenten

- `runtime/replay_core.py` – öffentliche Replay-Fassade
- `runtime/replay_models.py` – immutable/serialisierbare Replay-Wertobjekte und Safety-Policy
- `runtime/replay_checkpoint.py` – Checkpoint-Hash, atomisches Speichern und Restart
- `runtime/replay_risk_engine.py` – gemeinsames Wallet, Entry-Gates, Daily-Loss-/Protection-Zustand
- `runtime/replay_engine.py` – 1m-Order-/Fill-/Stop-/ROI-/Positions-Lifecycle
- `runtime/v8_replay_adapter.py` – lädt die exakte V8-Quelle und erzeugt Signalsnapshots ohne zweite Signalformel
- `runtime/replay_data.py` – Feather-Integrität, Gaps/Duplikate, SHA-256-Datenmanifest
- `runtime/replay_prepare_data.py` – lädt/ergänzt öffentliche Binance-Daten für BTC/ETH/SOL und 1m/15m/1h/4h
- `runtime/historical_live_replay.py` – chronologischer Full-System-Runner
- `runtime/replay_telemetry.py` – `manifest.json`, `metrics.json`, `trades.csv`, `decisions.jsonl`, `events.jsonl`, `errors.jsonl`, `equity.jsonl`
- `runtime/paper_decision_telemetry.py` – behavior-preserving Shadow-Telemetrie für den echten V8-Dry-run
- `runtime/replay_parity.py` – Paper-vs-Replay-Signal-/Risk-Comparison
- `runtime/replay_analysis.py` – Pair-/Jahr-/Monat-/Exit- und PnL-Konzentrationsanalyse
- `runtime/replay_research_analysis.py` – read-only `failed_4h_breakout`-/Volumen-/Breakout-/Regime-Attribution
- `runtime/statistical_audit.py` – Multiple-Testing-Audit mit CSCV/PBO- und Deflated-Sharpe-Diagnostik
- `research/trial_ledger.csv` – auch negative/pausierte Experimente bleiben dokumentiert

## Windows-Nutzung

Zuerst die historischen Daten laden/aktualisieren:

```text
HISTORISCHE_DATEN_LADEN.bat
```

Danach den gemeinsamen BTC/ETH/SOL-Replay starten:

```text
HISTORISCHER_LIVE_REPLAY.bat
```

Der Standard ist sechs Jahre. Damit deckt der normale Research-Lauf die langfristige V8-Gate-Historie ab; 1, 3 und 4 Jahre bleiben als schnellere Diagnosefenster verfügbar. Explizite UTC-Zeiträume können direkt über Python angegeben werden:

```bat
.\.venv\Scripts\python.exe runtime\historical_live_replay.py --start 2020-11-15 --end 2026-08-16 --fee 0.002
```

Kostenstress:

```bat
.\.venv\Scripts\python.exe runtime\historical_live_replay.py --start 2020-11-15 --end 2026-08-16 --fee 0.004
```

Auswertung des letzten Runs:

```text
HISTORISCHE_AUSWERTUNG.bat
```

Paper-/Replay-Parität nach einem überlappenden Paper-Zeitraum:

```text
PAPER_REPLAY_PARITAET.bat
```

## Checkpoint / Restart

Der Replay schreibt regelmäßig `checkpoint.json`. Bei Abbruch wird zusätzlich `checkpoint.failed.json` erzeugt. Ein Run kann mit einer neuen, separaten Run-ID fortgesetzt werden:

```bat
.\.venv\Scripts\python.exe runtime\historical_live_replay.py --start 2020-11-15 --end 2026-08-16 --resume "runtime\user_data\replay_results\<RUN>\checkpoint.json"
```

Ein beschädigter oder unbekannter Checkpoint wird fail-closed abgelehnt. Die Golden-/Restart-Tests verlangen identischen State-Hash vor und nach kontrolliertem Neustart.

## Paper-Telemetrie

Der gelockte `trade`-Bootstrap instrumentiert nur Dry-run-Strategieinstanzen. Der klassische gelockte Backtest importiert denselben Loader, aktiviert diese Telemetrie aber **nicht**. Damit werden Backtest- und Paper-Daten nicht vermischt.

Die Wrapper rufen die Originalcallbacks exakt einmal auf und geben deren Originalresultat unverändert zurück. Fehler in der Telemetrie werden geschluckt und dürfen weder einen Entry erlauben noch blockieren.

Lokale Dateien:

```text
runtime/user_data/paper_telemetry/
```

## Was Parität bedeutet

Ein grüner Unit-/Golden-Test beweist die Replay-State-Machine, nicht automatisch historische Gleichheit mit einem echten Dry-run. Die empirische Paper-/Replay-Parität wird erst dann als bestanden markiert, wenn ein überlappender Candle-Zeitraum vorliegt und `PAPER_REPLAY_PARITAET.bat` die gleichen V8-Signalentscheidungen nach Pair + Candle-Open bestätigt. Entry- und Exit-Callbacks werden dabei getrennt verglichen; Risk-Confirmation wird zusätzlich paarweise in Reihenfolge verglichen.

Abweichungen sind **Blocker** und werden nicht durch Parameteränderungen kaschiert.

## Fault-Injection / Fail Closed

CI prüft mindestens:

- rückwärts laufende Simulationsuhr
- beschädigten Checkpoint
- Restart mit offener Position
- stale/fehlgeschlagene Datenquelle → keine neuen Entries
- Kill-Switch bei offener Position → Position bleibt verwaltet, neue Entries blockiert
- Same-Bar Stop + ROI → konservativer Stop
- gemeinsames 240-USDT-Exposure statt drei unabhängigen Wallets
- unveränderten normalisierten V8-Strategy-Hash

Die vorhandene Candle-Integritätsprüfung blockiert fehlende, duplizierte oder unsortierte historische Kerzen vor dem Run.

## Research-Gate

Der Replay ist **retrospektive Belastungsprüfung**, kein neues OOS-Fenster. Er darf bekannte historische Daten benutzen, aber ein gutes Ergebnis ist kein Echtgeld-Beweis. Ein Kandidat wird nicht anhand eines einzelnen End-PnL promotet.

`runtime/replay_research_analysis.py` erzeugt zusätzlich eine rein deskriptive Attribution für `failed_4h_breakout`, 15m-`volume_ratio`, Breakout-Distanz in ATR, ADX, Momentum, ATR-Prozent und BTC-Regime. Daraus darf **keine neue Schwelle rückwirkend ausgewählt** werden; eine Änderung benötigt eine neue vorregistrierte Experiment-ID.

`runtime/statistical_audit.py` erwartet Return-Serien aller vergleichbaren Trials. PBO/DSR werden ausdrücklich als Diagnose und nicht als automatischer Echtgeldschalter behandelt.

## Bekannte Grenzen

- 1m-OHLC kann die echte Tick-/Orderbook-Reihenfolge nicht vollständig rekonstruieren.
- Limit-Fills sind bewusst deterministisch und konservativ modelliert, nicht als exakte Binance-Matching-Engine.
- Die MaxDrawdown-Protection wird als deterministische, dokumentierte Replay-Näherung über geschlossene Trades rekonstruiert; Paper-/Replay-Telemetrie muss mögliche Abweichungen sichtbar machen.
- Vollständige empirische Parität kann nur mit einem überlappenden echten Paper-Datenstrom bewiesen werden.

Status dieser Infrastruktur: **RESEARCH / PAPER-SAFETY INFRASTRUCTURE – NOT REAL MONEY**.
