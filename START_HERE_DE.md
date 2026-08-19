# Start hier: V8-Paperbot und Deep-Research-System

## Aktueller Stand

Der aktuelle Champion ist `CompressionBreakout250` / V8.

V8 bleibt eingefroren und läuft ausschließlich im simulierten Paper-/Dry-run-Betrieb mit:

- Binance Spot / USDT
- BTC/USDT, ETH/USDT, SOL/USDT
- long-only, 1x
- 250 virtuelle USDT
- maximal 80 USDT je Position
- maximal drei Positionen / 240 USDT Gesamtengagement

Status: **READY FOR EXTENDED PAPER TEST – NOT READY FOR REAL MONEY.**

Der verbindliche Weiterentwicklungsplan steht in [`RESEARCH_MASTERPLAN_DE.md`](RESEARCH_MASTERPLAN_DE.md). Ältere Codex-Phasen sind keine aktive Sollvorgabe mehr.

Der konkrete Soll/Ist-Abgleich gegen die aktuellen Deep-Research-Berichte steht in [`docs/DEEP_RESEARCH_GAP_AUDIT_DE.md`](docs/DEEP_RESEARCH_GAP_AUDIT_DE.md). Dort werden vorhandene, teilweise vorhandene und noch fehlende Teile ausdrücklich getrennt. Ein vorhandenes Grundgerüst darf nicht als fertige Umsetzung ausgegeben werden.

## Zielbild

Langfristig entsteht kein einzelner ständig handelnder Bot, sondern eine deterministische Multi-Strategy Execution Engine mit separater AI Research Plane.

```text
Market Data
→ Normalizer / Data Quality
→ Features
→ Regime
   ├─ TREND/BREAKOUT → separater Trend-Challenger
   │                   ├─ ORB-Retest
   │                   └─ Ichimoku
   ├─ RANGE/MEAN_REVERSION → Bollinger MR
   └─ unklar → NO_TRADE
→ Signal Validator
→ Portfolio/Risk
→ Execution/OMS
→ Reconciliation
→ Telemetrie
```

`NO_TRADE` ist die Default-Aktion bei unklarer Datenqualität, unklarem Regime oder Risk-Reject.

Die beiden Deep-Research-Berichte setzen bei der Trendkomponente unterschiedliche Schwerpunkte. Deshalb werden **ORB-Retest und Ichimoku nicht miteinander vermischt und nicht stillschweigend gegeneinander entschieden**. Beide sind spätere eigenständige Trend-Challenger; Bollinger MR ist die separate Range-/Mean-Reversion-Familie. Ein Hybrid kommt erst nach Einzelvalidierung.

Der spätere Research-Router ist bereits als fail-closed Contract in `runtime/research_strategy_contract.py` formalisiert. Er ist **nicht** in V8 verdrahtet und verändert deshalb keine aktuelle Paper-Handelsentscheidung.

Der AI-/LLM-Teil liegt ausschließlich im Cold Path:

```text
Trades + Logs + Regime + Execution-Daten
→ AI Research
→ falsifizierbare Hypothese
→ separater Candidate
→ Backtest / Walk-Forward / PBO / DSR / Stress
→ Registry
→ Shadow / Forward
→ manuelle Freigabe
```

Der LLM-Agent erhält keine freie Exchange-Orderfunktion und verändert nicht spontan aktive Risk-/Trading-Parameter.

## Testbot starten

Für den 24/7-Paper-Test:

```bat
STARTBOT.bat
```

Der sichtbare STARTBOT-Prozess bleibt Teil des Sicherheitsvertrags: Wird die überwachte Konsole geschlossen, muss der zugehörige Bot-Prozessbaum beendet werden.

Die Bedienung des Paperbots steht in [`TESTBOT_ANLEITUNG.md`](TESTBOT_ANLEITUNG.md).

## Normaler Backtest

Der integrierte Backtest simuliert die aktuell geladene Strategie; es gibt keine separate zweite Backtest-Strategie.

Für lokale historische Backtests kann außerdem verwendet werden:

```bat
HISTORISCHER_BACKTEST.bat
```

## Historischer Full-System-Replay

Der Replay ist kein Ersatz für den klassischen Backtest. Er spielt historische Daten chronologisch ab und führt zustandsabhängige Portfolio-/Risk-/Orderpfade mit.

Zuerst historische Daten laden und prüfen:

```bat
HISTORISCHE_DATEN_LADEN.bat
```

Danach:

```bat
HISTORISCHER_LIVE_REPLAY.bat
```

Der Replay nutzt ein gemeinsames 250-USDT-Wallet für BTC, ETH und SOL und erzeugt seine Ergebnisse unter:

```text
runtime\user_data\replay_results\
```

Für den aktuellen Research-Gate sollen Baseline-Kosten von 0,002 je Orderseite und zusätzlich ein Stresslauf mit 0,004 je Seite bewertet werden.

Der Replay modelliert inzwischen zusätzlich zu Gebühren, fixer Slippage, Timeouts und Risk-Zustand auch **deterministischen Spread-Stress, eine auf 1-Minuten-Granularität begrenzte Execution-Verzögerung, Partial-Fill-Slices, Cancel-Reject-Stress, Duplicate-Minute-Idempotenz sowie Checkpoint-/Replay-Reconciliation**.

**Wichtig:** Das macht ihn noch nicht zu einer historischen Tick-/Orderbuch-/Exchange-OMS-Rekonstruktion. Spread ist ein deterministischer Stress-Proxy, Partial Fills sind kein volumenbasiertes Queue-Modell, die Latenzauflösung bleibt 1 Minute und echte Exchange-Reconciliation bzw. asynchrones Fill-Reordering sind weiterhin offen. Der genaue Status steht im Gap-Audit.

## Paper-vs-Replay-Parität

Wenn ein tatsächlich überlappender Paper-Zeitraum vorhanden ist:

```bat
PAPER_REPLAY_PARITAET.bat
```

Unerklärte Signal- oder Risk-Allow/Reject-Abweichungen bei identischem kausalem Input sind ein Release-Blocker für spätere Strategie-Promotion.

## Red-Team-/Fault-Abdeckung

Deep Research verlangt mehr als einen einzelnen Stale-Data-Test. Bereits maschinell geprüft sind jetzt unter anderem Data-Unhealthy, Kill-Switch, rückwärts laufende Replay-Zeit, fehlausgerichtete Minute-Batches, Fill-Time-Risk-Recheck, Entry-Timeout, Duplicate/Conflicting-Minute-Events, Partial Fills, Cancel Reject und Checkpoint-Restore mit teilgefüllter offener Position.

Offen bzw. nur teilweise modelliert bleiben insbesondere echtes asynchrones Fill-/Order-Event-Reordering, reale Exchange-Positionen bei Boot, Risk-Service-/DB-Ausfall und feinere als 1-Minuten-Latenz. Die Fault-/Execution-Schicht bleibt deshalb als Gesamtpaket **PARTIAL**.

## Replay-/Research-Auswertung

```bat
HISTORISCHE_AUSWERTUNG.bat
```

Die Auswertung dient insbesondere dazu, die `failed_4h_breakout`-Trades, Volume-Ratio, Breakout-Distanz und kausale Regime zu untersuchen, **ohne V8 dadurch automatisch zu verändern**.

## Trial Ledger, Walk-Forward und Multiple Testing

Alle Kandidaten – auch abgelehnte – bleiben in:

```text
research\trial_ledger.csv
```

PBO/Deflated-Sharpe-Diagnostik kann über:

```bat
STATISTIK_AUDIT.bat
```

laufen, sobald vergleichbare Return-Serien für mehrere Trials vorliegen.

Ein kausaler Walk-Forward-Contract ist inzwischen in `runtime/walk_forward.py` vorhanden: half-open Train/Test-Fenster, Fensterprüfung und Fold-Summary einschließlich Kostenstress- und 1-Bar-Lag-Feldern. Noch fehlt die vollständige Strategie-Runner-/Promotion-Integration; deshalb ist Walk-Forward **PARTIAL**, nicht fertig.

Für neue Strategie-Challenger müssen Development/Validation/Holdout, Walk-Forward, Kostenstress, 1-Bar-Lag, Parameterplateau und PnL-Konzentration vollständig in den Research-Prozess aufgenommen werden. Diese Kennzahlen sind Research-Gates und keine Gewinn- oder Echtgeldfreigabe.

## Offline AI Research Plane

`research\Start-ResearchDesk.ps1` ist nur ein sicherheitsbewusster Prototyp. Autonome Ausführung bleibt absichtlich deaktiviert, bis eine echte Low-Privilege-/VM-/Container-Isolation besteht. Dieser fehlende aktive Loop ist **kein Bug, den man durch Entfernen des Guards beheben darf**.

## Was aktuell ausdrücklich nicht gemacht wird

- kein Futures/Perpetuals
- kein Margin
- kein Short
- kein Hebel
- kein Martingale/DCA
- keine automatische Kapitalerhöhung
- kein LLM mit direkter Exchange-Orderfunktion
- kein Mischen von Bollinger/Ichimoku/ORB in den eingefrorenen V8
- kein neues Volume-Tuning nach Sicht auf B1/B2
- kein Regime-Hybrid, bevor Einzelstrategien getrennt validiert wurden
- keine Aussage „Execution/Fault-Suite fertig“, solange der Gap-Audit offene Punkte zeigt

## Nächste technische Reihenfolge

1. V8 unverändert lassen.
2. Verbleibende Replay-/Execution-/Reconciliation-/Fault-Gaps schließen, ohne V8 umzuschreiben.
3. Danach echter Full-History-, Fee-Stress- und Paper-Parity-Lauf.
4. V8-Diagnostik.
5. Walk-Forward-Runner-/Meta-Research-Integration vervollständigen.
6. Erst danach ORB-Retest, Bollinger MR und Ichimoku als **getrennte** Challenger vorregistrieren.
7. Erst nach Einzelvalidierung einen Regime-Router/Hybrid testen.

## Tests

Vor relevanten Research-Änderungen:

```bat
uv sync --frozen --all-extras --python 3.12
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
```

Marktdaten, Replay-Ergebnisse, Paper-Datenbanken, Logs und Secrets bleiben lokal und dürfen nicht in Git committed werden.
