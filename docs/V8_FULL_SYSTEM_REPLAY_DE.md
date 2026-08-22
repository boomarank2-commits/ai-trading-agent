# V8 Full-System-Replay und Paper-Parität

Stand: 16.08.2026

## Ziel

Der eingefrorene V8-Champion `CompressionBreakout250` bleibt in seiner Signaldatei unverändert. Der Replay-Pfad ist **keine zweite Handelsstrategie**. Er lädt die exakt gehashte V8-Quelle, ruft deren eigene Indicator-/Entry-/Exit-/`custom_exit`-Callbacks auf und setzt die Entscheidungen anschließend in einer separaten historischen State-Machine um.

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
- Cooldown, StoplossGuard und MaxDrawdown-Lock als deterministischer Portfoliozustand
- Kill-Switch und Data-Health fail-closed für neue Entries
- Teilfüllungsreste derselben ursprünglichen Entry-Order werden vor weiteren Fills erneut gegen Risk/Data-Status geprüft; das ist **kein DCA**
- `STARTBOT.bat` und Windows-Kill-on-close werden nicht verändert
- Replay-, Paper-Telemetrie- und Backtest-Artefakte bleiben getrennt

## Zeitmodell

Die Simulationsuhr ist monoton. Eine 15m-Strategieentscheidung wird erst nach Abschluss der Signal-Candle sichtbar. Ein Signal aus der 00:00-Candle ist damit frühestens um 00:15 bekannt.

1h- und 4h-Informative-Candles werden mit ihrer **Close-Zeit** as-of gemerged. Eine 4h-Candle mit Open 00:00 darf folglich erst ab 04:00 in einer abgeschlossenen 15m-Entscheidung auftauchen.

Optional kann eine deterministische `execution_delay_minutes`-Verzögerung verwendet werden. Wegen der 1m-Detaildaten ist dies eine **Minuten-Granularität**, keine Rekonstruktion einer echten Zwei-Sekunden-Exchange-Latenz.

Wenn Stop und ROI in derselben 1m-Detail-Candle berührt werden, wird konservativ zuerst der adverse Stop ausgewertet.

## Execution-/Cost-Stress

Der Replay besitzt inzwischen mehrere deterministische Stressmodelle:

- `fee_per_side` für Gebühren
- `slippage_bps` als adverse fixe Slippage-Annahme
- `spread_bps` als adverser Spread-Proxy; pro Orderseite wird die Hälfte des konfigurierten Spread-Proxys belastet
- `execution_delay_minutes` für deterministische Fill-Verzögerung
- `fill_fraction_per_touch` für deterministische Partial-Fill-Slices über mehrere berührende 1m-Bars
- `cancel_rejects_before_cancel` für reproduzierbare abgelehnte Cancel-Versuche
- Entry-/Exit-Timeouts und Exit-Retry

Wichtig: Diese Mechanismen sind **Stress-/Robustheitsannahmen**. Sie sind kein historisches Binance-Orderbuch, keine Queue-Positionssimulation und keine Tick-genaue Matching-Engine.

## Duplicate-/Event-Sicherheit

Für 1m-Market-Batches gilt:

- ein exakt identischer bereits verarbeiteter Minute-Batch wird idempotent ignoriert
- derselbe Minute-Timestamp mit abweichendem OHLCV-Inhalt schlägt fail-closed fehl
- rückwärts laufende Replay-Zeit wird abgelehnt
- fehlausgerichtete Batches oder Pair-Key-/Bar-Pair-Mismatches werden abgelehnt

Echtes asynchrones out-of-order Order-/Fill-Event-Reordering ist damit noch **nicht vollständig** modelliert.

## Checkpoint / Restart / Reconciliation

Checkpoint-Schema 2 persistiert zusätzlich zu Wallet/Positionen/Orders auch Partial-Fill- und Duplicate-Minute-State. Schema-1-Checkpoints können weiterhin gelesen werden.

Beim Restore läuft eine deterministische Replay-Reconciliation. Sie akzeptiert konsistente offene bzw. teilgefüllte Positionen, lehnt aber unter anderem fail-closed ab:

- negatives Cash
- Exposure oberhalb des Safety-Caps
- zu viele Positionen
- ungültige/inkonsistente Positionen
- orphan Sell-Orders
- nicht zur offenen Position gehörende Buy-Orders

Das ist **Replay-/Checkpoint-Reconciliation**, nicht gleichbedeutend mit einer echten Exchange-Abfrage bei Prozessstart. Reale Exchange-/Boot-Reconciliation bleibt ein offener Produktionsbaustein.

## Komponenten

- `runtime/replay_core.py` – öffentliche Replay-Fassade
- `runtime/replay_models.py` – Replay-Wertobjekte, Safety- und Execution-Stress-Policy
- `runtime/replay_checkpoint.py` – Checkpoint-Schema/Hash, atomisches Speichern und Restart
- `runtime/replay_risk_engine.py` – gemeinsames Wallet, Entry-Gates, Daily-Loss-/Protection-Zustand und Replay-Reconciliation
- `runtime/replay_engine.py` – 1m-Order-/Fill-/Partial-Fill-/Cancel-/Stop-/ROI-/Positions-Lifecycle
- `runtime/v8_replay_adapter.py` – lädt die exakte V8-Quelle und erzeugt Signalsnapshots ohne zweite Signalformel
- `runtime/replay_data.py` – Feather-Integrität, Gaps/Duplikate, SHA-256-Datenmanifest
- `runtime/replay_prepare_data.py` – lädt/ergänzt öffentliche Binance-Daten für BTC/ETH/SOL und 1m/15m/1h/4h
- `runtime/historical_live_replay.py` – chronologischer Full-System-Runner
- `runtime/replay_telemetry.py` – `manifest.json`, `metrics.json`, `trades.csv`, `decisions.jsonl`, `events.jsonl`, `errors.jsonl`, `equity.jsonl`
- `runtime/paper_decision_telemetry.py` – behavior-preserving Shadow-Telemetrie für den echten V8-Dry-run
- `runtime/replay_parity.py` – Paper-vs-Replay-Signal-/Risk-Comparison
- `runtime/replay_analysis.py` – Pair-/Jahr-/Monat-/Exit- und PnL-Konzentrationsanalyse
- `runtime/replay_research_analysis.py` – read-only `failed_4h_breakout`-/Volumen-/Breakout-/Regime-Attribution
- `runtime/statistical_audit.py` – CSCV/PBO- und Deflated-Sharpe-Diagnostik
- `runtime/walk_forward.py` – kausaler Walk-Forward-Fenster-/Fold-Contract; noch kein vollständiger Strategie-Runner
- `runtime/research_strategy_contract.py` – fail-closed späterer `TREND/BREAKOUT` / `RANGE/MEAN_REVERSION` / `NO_TRADE`-Routing-Contract; **nicht** in V8 verdrahtet
- `research/trial_ledger.csv` – auch negative/pausierte Experimente bleiben dokumentiert

## Windows-Nutzung

Zuerst historische Daten laden/aktualisieren:

```text
HISTORISCHE_DATEN_LADEN.bat
```

Danach den gemeinsamen BTC/ETH/SOL-Replay starten:

```text
HISTORISCHER_LIVE_REPLAY.bat
```

Der normale Research-Run kann die langfristige Historie abdecken. Explizite UTC-Zeiträume können direkt über Python angegeben werden:

```bat
.\.venv\Scripts\python.exe runtime\historical_live_replay.py --start 2020-11-15 --end 2026-08-16 --fee 0.002
```

Kostenstress:

```bat
.\.venv\Scripts\python.exe runtime\historical_live_replay.py --start 2020-11-15 --end 2026-08-16 --fee 0.004
```

Auswertung:

```text
HISTORISCHE_AUSWERTUNG.bat
```

Paper-/Replay-Parität nach einem tatsächlich überlappenden Paper-Zeitraum:

```text
PAPER_REPLAY_PARITAET.bat
```

## Paper-Telemetrie und Parität

Der gelockte `trade`-Bootstrap instrumentiert nur Dry-run-Strategieinstanzen. Der klassische gelockte Backtest aktiviert diese Paper-Telemetrie nicht. Die Wrapper rufen Originalcallbacks exakt einmal auf und geben deren Originalresultat unverändert zurück.

Ein grüner Unit-/Golden-Test beweist die Replay-State-Machine, nicht automatisch historische Gleichheit mit einem echten Dry-run. Empirische Paper-/Replay-Parität gilt erst als bestanden, wenn ein real überlappender Candle-Zeitraum vorliegt, Strategie-, Konfigurations- und Risk-Policy-Hashes identisch sind und Signal-/Risk-Entscheidungen erklärbar übereinstimmen. Der Vergleich schlägt bei fehlendem Abschlussmanifest, Hash-Abweichungen oder fehlender Risk-Parität geschlossen fehl. Unerklärte Abweichungen sind **Blocker** und werden nicht durch Parameteränderungen kaschiert.

## Fault-Injection / Fail Closed

Automatisiert geprüft werden inzwischen unter anderem:

- rückwärts laufende Simulationsuhr
- beschädigter Checkpoint
- Checkpoint-Restore mit offener bzw. teilgefüllter Position
- stale/fehlgeschlagene Datenquelle → keine neuen Entries
- Kill-Switch → neue Entries blockiert
- Fill-Time-Risk-Recheck bei geändertem Data-/Risk-Status
- Entry-Timeout
- fehlausgerichtete Minute-Batches
- Pair-Key-/Bar-Pair-Mismatch
- identische Duplicate-Minute-Events idempotent
- widersprüchliche gleiche Minute fail-closed
- deterministische Partial Fills
- deterministischer Cancel Reject
- Same-Bar Stop + ROI → konservativer Stop
- gemeinsames 240-USDT-Exposure statt drei unabhängigen Wallets
- unveränderter normalisierter V8-Strategy-Hash

Noch offen/teilweise sind insbesondere:

- echtes asynchrones out-of-order Fill-/Order-Event-Reordering
- reale Exchange-Positionen/Orders bei Boot
- Risk-Service-Restart
- temporärer DB-Ausfall als vollständiger Fault-Pfad
- sub-minute Latenz
- historisches Orderbuch-/Queue-Modell

Die vollständige Deep-Research-Matrix steht in `docs/DEEP_RESEARCH_GAP_AUDIT_DE.md` und darf nicht als komplett bestanden bezeichnet werden, solange dort offene Punkte stehen.

## Research-Gate

Der Replay ist **retrospektive Belastungsprüfung**, kein neues OOS-Fenster. Ein gutes Ergebnis ist kein Echtgeld-Beweis.

`runtime/replay_research_analysis.py` erzeugt deskriptive Attribution für `failed_4h_breakout`, 15m-`volume_ratio`, Breakout-Distanz in ATR, ADX, Momentum, ATR-Prozent und BTC-Regime. Daraus wird keine neue Schwelle rückwirkend ausgewählt; eine Änderung benötigt eine neue vorregistrierte Experiment-ID.

`runtime/statistical_audit.py` erwartet Return-Serien vergleichbarer Trials. PBO/DSR sind Diagnose-/Research-Gates und keine automatische Echtgeldfreigabe.

Der Walk-Forward-Contract definiert kausale Train/Test-Fenster und Fold-Summaries. Die vollständige automatische Strategie-Runner-/Promotion-Integration ist noch offen.

## Bekannte Grenzen

- 1m-OHLC kann Tick-/Orderbook-Reihenfolge nicht vollständig rekonstruieren.
- Spread ist ein deterministischer Stress-Proxy, keine historische Bid/Ask-Serie.
- Partial Fills sind deterministische Slices, kein Volumen-/Queue-Modell.
- Execution-Latenz ist aktuell nur auf 1m-Granularität modellierbar.
- asynchrone Exchange-Order-/Fill-Event-Reihenfolge ist nicht vollständig simuliert.
- echte Exchange-/Boot-Reconciliation ist nicht implementiert.
- die MaxDrawdown-Protection ist eine dokumentierte Replay-Näherung über geschlossene Trades.
- vollständige empirische Parität kann nur mit einem überlappenden echten Paper-Datenstrom bewiesen werden.

Status dieser Infrastruktur: **RESEARCH / PAPER-SAFETY INFRASTRUCTURE – NOT REAL MONEY**.
