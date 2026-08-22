# Start hier: V12.15-Testbot, V8-Baseline und Deep-Research-System

## Aktueller Stand

Der eingefrorene Research-Champion bleibt `CompressionBreakout250` / V8. Die
aktuell vom Dry-run-Testbot geladene Kandidatendatei ist jedoch
`CompressionBreakout250` / **V12.15** auf `agent/v12-adaptive-league`.

V12.15 läuft ausschließlich im simulierten Paper-/Dry-run-Betrieb mit:

- Binance Spot / USDT
- BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, BNB/USDT, DOGE/USDT
- long-only, 1x
- 250 virtuelle USDT
- maximal 80 USDT je Position
- maximal drei Positionen / 240 USDT Gesamtengagement

V8 bleibt unter `research/baselines/V8/` unverändert für Replay, Reproduktion
und Research-Governance erhalten. V12.15 verändert diese Baseline nicht.

Status: **V12.15 BESTANDENER PAPER-/DRY-RUN-KANDIDAT – NOT READY FOR REAL MONEY.**

V12.15 verwendet wieder die vollständige V12.12-Signallogik und deren
pair-lokale Pause nach zwei Verlusten. Die einzige Strategieänderung ist ein
später Gewinn-Ratchet nur für Champion-Donchian-Trades: erst ab +30 % laufendem
Gewinn wird ein +5-%-Boden gesetzt. Sechs Pairs, alle normalen Exits und die
250/80/3-Kapitalgrenzen bleiben unverändert.

Der einzige V12.12-Drei-Jahres-Lauf lieferte eine starke diagnostische
Verbesserung, scheiterte aber formal am ersten nativen Candle-Dateiaudit. Der
Fehler lag in der Audit-Instrumentierung, nicht in der Simulation; der Lauf wird
trotzdem nicht als vollständig bestanden ausgegeben und sein identischer
Fingerabdruck darf nicht erneut getestet werden. Details und alle Kennzahlen:
[`research/V12_12_LIQUID_UNIVERSE_DE.md`](research/V12_12_LIQUID_UNIVERSE_DE.md).

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

Der spätere Research-Router ist bereits als fail-closed Contract in
`runtime/research_strategy_contract.py` formalisiert. Er ist **nicht** in die
aktive V12.15-Kandidatenstrategie verdrahtet und verändert deshalb keine aktuelle
Paper-Handelsentscheidung.

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

Der integrierte Backtest simuliert die aktuell geladene V12.15-Strategie; es gibt
keine separate zweite Backtest-Strategie.

In der Oberfläche ist **Gesamtportfolio** die maßgebliche 250-USDT-Prüfung.
Alle sechs Pairs laufen dabei gemeinsam auf einem Konto. „Alle 14 Backtests“
ergänzt diese echte Portfolio-Sicht um zwölf Einzelpaar-Zellen zur Attribution
und zeigt, wie viel Kapitalzeit tatsächlich genutzt wurde. Der gesperrte Runner
prüft dabei die wirklich verwendeten Strategy-, Config- und Candle-Dateien.

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
