# Verbindlicher Research-Masterplan – V8, Research Plane und Challenger

Stand: 16.08.2026

## Autorität

Diese Datei ist der **verbindliche technische und methodische Fahrplan** für die Weiterentwicklung dieses Repositories.

Sie ersetzt den früheren Auftrag `CODEX_NEXT_PHASE_LIVE_REPLAY_DE.md` als aktive Arbeitsgrundlage. Die frühere Datei war eine Vorversion und darf nicht mehr als aktueller Sollzustand verwendet werden.

Grundlage sind die beiden aktuellen Deep-Research-Berichte zu Hermes/OpenClaw und zu den vier Video-Strategien. Bei Widersprüchen zwischen älteren Notizen, alten Codex-Aufträgen und dieser Datei gilt **dieser Masterplan**. Der aktuelle technische Soll/Ist-Status wird zusätzlich in `docs/DEEP_RESEARCH_GAP_AUDIT_DE.md` geführt.

Die beiden Berichte setzen bei der Trend-Komponente unterschiedliche Schwerpunkte:

- Bericht A priorisiert als Engineering-Reihenfolge zunächst eine deterministische ORB-Retest-Baseline und anschließend Bollinger Mean Reversion.
- Bericht B empfiehlt als Zielbild insbesondere Ichimoku Trend Engine + Bollinger Mean-Reversion Engine.

Diese Abweichung wird **nicht stillschweigend aufgelöst**. ORB-Retest und Ichimoku bleiben getrennte Trend-Challenger-Familien. Erst vorregistrierte Out-of-Sample-, Kosten-, Walk-Forward- und Robustheitsevidenz darf später entscheiden, welche Trend-Komponente für ein Multi-Strategy-System geeignet ist.

## Oberste Grundregel

**V8 bleibt der eingefrorene Champion.**

Neue Ideen dürfen V8 nicht nachträglich so verändern, bis ein schöner Backtest entsteht. Neue Hypothesen werden als getrennte Challenger oder als reine Diagnose-/Telemetrie-/Infrastrukturänderungen umgesetzt. Ein negativer Versuch bleibt im Trial Ledger erhalten.

Klarstellung zum aktuellen Repository-Stand vom 24.08.2026: „Champion“ bezeichnet
hier die unveränderte Forschungsreferenz unter `research/baselines/V8/`, nicht
die gerade von `STARTBOT.bat` geladene Datei. Der aktive, separat registrierte
Paper-/Dry-run-Kandidat ist V12.31. Er behält V12.22 einschließlich des
SOL-Filters `adx_4h >= 21`, DOGEs vorregistrierten 4h-Supertrend(20, 3)
oberhalb einer steigenden EMA100 und kombiniert die unveränderte, bereits exakt
geprüfte BCH-EMA30/EMA80-Route oberhalb steigender EMA100 bei ADX 24. Sein
genauer technischer Stand, seine Vorgängerkette und die offenen Prüfungen stehen in
`research/V12_20_SELECTIVE_PYRAMID_DE.md` und
`research/V12_22_SOL_ADX21_DE.md` sowie
`research/V12_30_DOGE_SUPERTREND_DE.md` sowie
`research/V12_31_DOGE_BCH_COMBINATION_DE.md`. V12.31 ist nicht als neuer Champion
und nicht für Echtgeld promoviert.

Sicherheitsvertrag der eingefrorenen V8-Referenz:

- Strategie: `CompressionBreakout250` / V8
- Binance Spot / USDT
- long-only, 1x
- kein Futures, Margin, Short, DCA oder Martingale
- 250 virtuelle USDT
- maximal 80 USDT je Position
- maximal drei Positionen / 240 USDT Gesamtengagement
- Hard-Stop -5,5 %
- keine automatische Kapitalerhöhung
- **keine automatische Echtgeldfreigabe**
- Research-/LLM-Code erhält keine freie Exchange-Orderfunktion

Bindender LF-normalisierter V8-SHA256:

`9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280`

Status: **READY FOR EXTENDED PAPER TEST – NOT READY FOR REAL MONEY.**

## Zielarchitektur aus Deep Research

Das langfristige Ziel ist **keine einzelne ständig handelnde Super-Strategie**, sondern eine deterministische Multi-Strategy Execution Engine mit separater AI Research Plane.

Der spätere Strategie-Zustandsraum muss mindestens diese Zustände unterstützen:

- `TREND/BREAKOUT`
- `RANGE/MEAN_REVERSION`
- `NO_TRADE`

**`NO_TRADE` ist die Default-Aktion**, wenn Datenqualität, Regime, Signalqualität oder Risk Policy keine belastbare Freigabe liefern.

```text
Exchange WebSocket / REST
        ↓
Market Data Normalizer
        ↓
Feature Engine
        ↓
Data Quality Gate ───────────────→ NO_TRADE
        ↓
Regime Detector
        ├─ TREND/BREAKOUT ───────→ Trend-Engine
        │                         ├─ ORB-Retest-Challenger
        │                         └─ Ichimoku-Challenger
        ├─ RANGE/MEAN_REVERSION ─→ Bollinger-MR-Challenger
        └─ unklar ───────────────→ NO_TRADE
                                  ↓
                         Signal Validator
                                  ↓
                       Portfolio & Risk Engine
                          ├─ reject → NO_TRADE
                          └─ allow
                                  ↓
                         Execution / OMS
                                  ↓
                              Exchange
                                  ↓
                     Position Reconciliation
                                  ↓
                      Journal / Telemetrie
                                  ↓
                        Offline AI Research
                                  ↓
                      Hypothesis Generator
                                  ↓
                  Backtest + Walk-Forward
                                  ↓
                  PBO / DSR / Stress Tests
                                  ↓
                    Strategy Registry
                                  ↓
                  manuelle/Policy-Freigabe
```

### Hot Path

Der zeitkritische Trading-Pfad bleibt deterministisch:

```text
Market event
→ normalisierte Daten
→ Features
→ Datenqualitäts-Gate
→ Regime
→ deterministische Strategie
→ deterministisches Portfolio/Risk
→ deterministische Order/OMS
→ Reconciliation
```

Kein LLM, Hermes-, OpenClaw-, Codex- oder anderer Agent darf im Hot Path frei über Orders, Hebel, Stopps, Positionsgröße oder Live-Parameter entscheiden.

### Cold Path / Research Plane

```text
Trades + Logs + Regime + Execution-Daten
→ Offline AI Research Agent
→ Analyse
→ falsifizierbare Hypothese
→ separater Strategy-Fork
→ Backtest
→ Walk-Forward
→ Robustheits-/Kosten-/Lag-Tests
→ PBO / Deflated Sharpe
→ Versionierung / Registry
→ Shadow / Forward
→ manuelle Promotion
```

`Self Improvement` bedeutet hier **Self Hypothesis Generation + Automated Testing**, nicht ungeprüfte Selbstmodifikation des Live-Tradings.

## Verbindliche Forschungsreihenfolge

### Phase 0 – Baseline einfrieren

1. V8-SHA unverändert lassen.
2. 250-USDT-Paper-Forward weiterführen.
3. Alle Research-Versuche inklusive Fehlschläge im Trial Ledger führen.
4. Keine nachträgliche Holdout-Optimierung.
5. Keine neue Strategieidee darf die laufende V8-Paperstrategie implizit verändern.

### Phase 1 – Full-System-Replay, Parität und Execution-/Cost-Stress

Vor Strategie-Tuning müssen belastbar sein:

- monotone historische Simulationsuhr
- nur vollständig abgeschlossene Candles sichtbar
- 15m-Signale, 1m Execution-Detail, 1h/4h Informative
- punkt-in-zeit korrektes Informative-Merging
- exakt gehashte V8-Quelle als Signalautorität
- gemeinsames 250-USDT-Wallet für BTC/ETH/SOL
- dieselben Exposure-, Daily-Loss-, Cooldown- und Protection-Regeln
- deterministische Order-/Fill-Simulation
- konservative Same-Bar-Reihenfolge
- Checkpoint/Restart mit identischem Endzustand
- Datenmanifest mit SHA-256, UTC, Gap-/Duplikatprüfung
- Golden Replay
- Paper-vs-Replay-Paritätsprüfung
- maschinenlesbare Telemetrie

Der Replay modelliert inzwischen zusätzlich zu Gebühren, fixer Slippage und Timeouts auch:

- deterministischen Spread-Stress als **Proxy**, nicht als historisches Orderbuch
- deterministische Execution-Verzögerung auf 1m-Granularität
- **Partial Fills** als deterministische Fill-Slices für Entry- und Limit-Exit-Orders
- deterministische Cancel-Reject-Szenarien (`cancel rejected`)
- idempotente Duplicate-Minute-Batches und fail-closed widersprüchliche Duplikate
- Checkpoint-/Replay-Reconciliation für valide offene bzw. teilgefüllte Positionen

Diese Erweiterungen machen den Replay robuster, aber **nicht** zu einer historischen Tick-/Orderbuch-/Exchange-OMS-Rekonstruktion. Noch offen oder nur teilweise sind insbesondere:

- echte sub-minute/Exchange-Latenz
- volumen-/queue-basierte Fill-Wahrscheinlichkeit
- echtes asynchrones out-of-order Order-/Fill-Reordering
- reale Exchange-Reconciliation bei Prozessstart
- vollständiger Risk-Service-/DB-Fault-Pfad

**Release-Blocker:** Bei identischem kausalem Input dürfen Signal- oder Risk-Allow/Reject-Entscheidungen nicht unerklärt zwischen Paper und Replay abweichen.

Lokale empirische Gates:

1. Full-History-Replay BTC/ETH/SOL gemeinsam, Baseline-Fee 0,002 je Seite.
2. Fee-Stress 0,004 je Seite.
3. Paper-vs-Replay-Parität auf einem tatsächlich überlappenden Paper-Zeitraum.
4. Execution-Stress mit dokumentierten Annahmen; keine Behauptung historischer Orderbuchgenauigkeit.

### Phase 1b – Red-Team-/Fault-Injection-Matrix

Die Deep-Research-Matrix bleibt verbindliches Coverage-Ziel:

- WebSocket reconnect / Datenfeed-Ausfall
- Exchange-Antwort verspätet
- duplicate event
- out-of-order event/fill
- partial fill
- cancel rejected
- stale candle
- clock offset / nicht-monotone Zeit
- strategy process restart
- risk service restart
- position exists at boot
- LLM/Research-Service unavailable
- database temporarily unavailable

Bereits automatisiert geprüft sind unter anderem Data-Unhealthy, Kill-Switch, rückwärts laufende Replay-Zeit, fehlausgerichtete Minute-Batches, Pair-Mismatch, Fill-Time-Risk-Recheck, Entry-Timeout, Duplicate/Conflicting-Minute-Events, Partial Fills, Cancel Reject und Checkpoint-Restore mit teilgefüllter Position.

Noch nicht vollständig abgedeckt sind insbesondere asynchrones Fill-Reordering, echte Exchange-Positionen bei Boot, Risk-Service-/DB-Ausfall und sub-minute Latenz. Bei ungeklärter sicherheitsrelevanter Unsicherheit gilt fail closed / `NO_TRADE`.

### Phase 2 – V8-Diagnostik, noch ohne Entry-Änderung

Zuerst beobachten und erklären, nicht filtern. Für Entry-Kandidaten sollen soweit technisch verfügbar protokolliert werden:

- `volume_ratio_15m`
- `atr_pct_15m`
- `adx_4h`
- `rsi_4h`
- `momentum_30d_4h`
- 4h-EMA-Steigung
- Breakout-Distanz in ATR
- Donchian-Level
- BTC-Regime
- Pair
- späterer Exit-Grund
- MFE / MAE
- Netto-PnL

Ziel ist insbesondere die Ursachenanalyse der `failed_4h_breakout`-Trades. Regime werden zuerst gelabelt. Ein aktives neues Gate für V8 entsteht nur als eigener vorregistrierter Challenger.

### Phase 3 – Vorregistrierte V8-Challenger

Für die globale Volume-Hypothese sind ausschließlich diese Varianten vorgesehen:

- B0 = unverändertes V8
- B1 = V8 + `volume_ratio >= 1.00`
- B2 = V8 + `volume_ratio >= 1.25`

B1 wurde als globaler Filter verworfen. B2 ist pausiert, bis Replay-/Diagnose-Gates belastbar sind. Nach Einsicht in B1/B2 wird **keine neue Schwelle spontan erfunden**.

Zusätzlich darf später maximal ein einfaches Regime-Gate vorregistriert werden, wenn die Attribution es rechtfertigt. Kein Challenger ersetzt V8 allein aufgrund eines Gesamt-Backtests.

### Phase 4 – Eigenständige Strategie-Challenger

Neue Strategie-Familien werden erst nach Replay-, Paritäts-, Execution-, Fault- und Diagnose-Gates aktiviert.

#### ORB-Retest-Challenger

- Opening Range deterministisch definieren
- bestätigter Ausbruch
- zunächst nur Retest-Setup
- FVG und BOS/Reversal noch nicht gleichzeitig ergänzen
- eigene Strategy-ID
- keine Änderung an V8

#### Bollinger-Mean-Reversion-Challenger

- eigene Strategy-ID
- 15m
- Research-Default Bollinger 20/2,0; kein behauptetes Video-Optimum
- Long nach Berührung/Unterschreitung des unteren Bands und bestätigtem Close zurück hinein
- nur in kausal definiertem Range-Regime
- Exit zunächst am Mittelband
- Spot, long-only, kein Hebel, kein Short, keine Positionsaufstockung

#### Ichimoku-Trend-Challenger

- eigene Strategy-ID
- Tenkan/Kijun 9/26
- Span-B 52 / Displacement 26 als Research-Default
- Preis/Cloud, Tenkan/Kijun, Chikou und Future-Cloud kausal und eindeutig implementieren
- Golden Tests für die Indikatorberechnung
- kein ungeprüftes Übernehmen ambiger Sekundärtranskripte
- keine Änderung an V8

Die Implementierungsreihenfolge ist **keine Ergebnisrangliste**. ORB und Ichimoku bleiben getrennte Trend-Hypothesen.

#### Späterer Multi-Strategy-/Regime-Router

`runtime/research_strategy_contract.py` formalisiert bereits fail-closed die drei Zustände und hält ORB, Ichimoku und Bollinger als getrennte Familien. Dieser Contract ist bewusst noch **nicht** in V8 oder einen produktiven Hybrid verdrahtet.

Ein Hybrid darf erst entstehen, wenn mindestens eine Trend-Familie und die Mean-Reversion-Familie getrennt belastbare Evidenz besitzen. Bei unklarem Regime gilt `NO_TRADE`.

### Phase 5 – Walk-Forward und Meta-Research

Vor jeder späteren Challenger-Promotion müssen sichtbar sein:

- vollständiges Trial Ledger
- Development / Validation / echter Holdout getrennt
- Walk-Forward über mehrere Zeitfenster
- CSCV/PBO
- Deflated Sharpe Ratio
- Parameter-Plateau statt isoliertem Optimum
- Pair- und Jahresslices
- Kostenstress
- 1-Bar-Lag-Stress
- PnL-Konzentration nach Instrument
- MAE/MFE
- Time-under-Water
- Monte-Carlo/Block-Bootstrap-DD, sobald belastbare Return-Serien vorliegen

`runtime/walk_forward.py` enthält inzwischen einen kausalen half-open Fenster-Contract, Fensterprüfung und Fold-Summary einschließlich Feldern für Kostenstress und 1-Bar-Lag. Die vollständige Strategie-Runner-/Promotion-Integration fehlt noch; Walk-Forward bleibt daher **PARTIAL**.

Die in Deep Research genannten Zahlen sind **Projekt-Engineering-Startgates, keine universellen wissenschaftlichen Wahrheiten**. Für neue Challenger sollen sie vor Sicht auf den Holdout vorregistriert oder begründet ersetzt werden:

```text
OOS Sharpe                   > 0.8
Deflated-Sharpe confidence   > 95 %
PBO                           < 20 %
Profit Factor                > 1.20
Expectancy                   > 0
Profitability at 1.5x costs  > 0
Profitability with 1-bar lag > 0
Max DD at target risk        < 10 %
No instrument                > 30 % total PnL
Parameter plateau            vorhanden
```

Diese Schwellen werden nicht rückwirkend benutzt, um V8 umzuschreiben oder zu demoten. PBO/DSR sind Research-Gates, keine Echtgeldfreigabe.

### Phase 6 – Shadow / Forward / manuelle Promotion

Robuste Challenger gehen zuerst in Shadow bzw. einen äquivalenten nicht-kapitalwirksamen Forward-Modus. Danach:

1. frische Forward-Daten sammeln
2. bei Schwäche zurück auf REJECT/RESEARCH
3. bei robuster Evidenz PAPER-CANDIDATE-REVIEW
4. weitere Lifecycle-Schritte nur mit expliziter manueller Freigabe

Keine automatische Echtgeldfreigabe und keine automatische Kapitalerhöhung.

### Phase 7 – Offline AI Research Agent

Der autonome Research-Scheduler bleibt **fail-closed deaktiviert**, solange er nicht in einer ausreichend isolierten Umgebung läuft.

Vor Aktivierung erforderlich:

- separater Low-Privilege-Account, VM oder Container
- kein Leserecht auf Exchange-Secrets oder quarantinierten Holdout
- nur explizit gestagte Inputs
- host-kontrollierter Output-Kanal
- harter Prozessbaum-/cgroup-Lifetime-Guard
- keine Exchange-Ordertools
- keine automatische Registry-Promotion

Der Agent liefert Hypothesen und Research-Artefakte, keine Live-Orders.

## Research-Entscheidungslogik

Jede neue Idee folgt diesem Ablauf:

1. Diagnose/Telemetrie, wenn V8 nicht verändert wird.
2. Separate Challenger-Branch, wenn Trading-Logik verändert wird.
3. Hypothese vorregistrieren.
4. Experiment-ID sowie Strategy-/Config-Hash speichern.
5. Kausalitäts- und Datenintegritätschecks.
6. Baseline gegen Challenger.
7. Pair- und Jahresslices.
8. Kostenstress + 1m Detail.
9. Walk-Forward.
10. Parameterplateau / DSR / PBO.
11. Lag-/Konzentrations-/Drawdown-Stress.
12. Replay-/Determinismusprüfung.
13. Erst dann Shadow.
14. Frische Forward-Evidenz.
15. Manuelle Review vor jeder Promotion.
16. Negative Ergebnisse dokumentieren, nicht löschen.

## Branch-Konvention

Keine Strategie-Forschungsänderung direkt auf `main`.

- `feature/replay-<thema>-YYYYMMDD`
- `feature/execution-<thema>-YYYYMMDD`
- `research/v8-<experiment>-YYYYMMDD`
- `research/challenger-orb-<experiment>-YYYYMMDD`
- `research/challenger-bollinger-<experiment>-YYYYMMDD`
- `research/challenger-ichimoku-<experiment>-YYYYMMDD`

## Pflicht-Telemetrie

Soweit im jeweiligen Pfad verfügbar:

- `experiment_id`, `run_id`, `git_sha`
- `strategy_name`, Strategy-/Runtime-Hash
- `config_hash`, `risk_policy_hash`, Replay-`data_manifest_hash`
- Modus, Pair, Candle-Close UTC
- Datenqualitätsstatus und Regime-Label
- Breakout-/Trend-/Volume-/ATR-/RSI-/Momentum-Features
- BTC-Regime
- Entry-Kandidat, Allow/Reject und Grund
- offene Positionen, Exposure, Daily PnL, Risk-Lock
- Orderstatus, Requested Price, Fill/Partial Fill, Slippage, Fee, Spread, Latenz
- Reconciliation-Status
- Exit-Grund, PnL, MAE/MFE
- Checkpoint-/Restart-Information

Observability darf das Trading-Verhalten nicht verändern.

## Ergebnis-Dashboard für neue Releases

Sobald echte Daten vorliegen, soll die Research-Auswertung mindestens erzeugen oder aus Rohdaten ableiten können:

- Equity netto nach Kosten
- Underwater-/Drawdown-Verlauf
- Rolling Sharpe 90/180 Tage, soweit Stichprobe sinnvoll
- Monats-/Zeitslice-Auswertung
- PnL nach Regime und Asset
- MAE/MFE
- Parameter-Heatmap/Plateau
- Kosten vs. Brutto-PnL
- PnL-Konzentration
- Monte-Carlo/Block-Bootstrap-DD, sobald methodisch belastbar

Keine erfundenen Charts oder Kennzahlen, wenn der empirische Lauf noch nicht stattgefunden hat.

## Trial-Ledger-Mindestfelder

- `experiment_id`
- `parent_experiment_id`
- `strategy_version`
- `strategy_hash`
- `parameter_hash`
- `hypothesis`
- `date_decided`
- `development_window`
- `validation_window`
- `holdout_window`
- `pairs`
- `fees`
- `trade_count`
- `net_return`
- `profit_factor`
- `sharpe`
- `max_drawdown`
- `reason_accepted_or_rejected`

## CI-/Testvertrag

Vor einem Research-PR mindestens:

```bat
uv sync --frozen --all-extras --python 3.12
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
```

Replay-/Research-CI muss zusätzlich abdecken:

- Clock-Causality / keine Future-Candle
- Checkpoint-Restart-Determinismus
- Paper-Replay-Parität
- Golden Replay
- Trial-Ledger-Schema
- Metrics-Reproduzierbarkeit
- PBO-/DSR-Inputvalidierung
- Research-Router/NO_TRADE-Contract
- Walk-Forward-Fenster-Contract
- Execution-Stress-Tests
- vollständige Red-Team-Matrix als Coverage-Ziel; offene Szenarien bleiben im Gap-Audit sichtbar

## Verbotene Abkürzungen

Ausdrücklich nicht erlaubt:

- V8 mit Bollinger + Ichimoku + ORB/FVG/BOS vermischen
- Futures/Perpetuals, Shorts oder Hebel aktivieren
- Stoploss/Protections abschwächen, um Backtests zu verschönern
- LLM ändert Live-Parameter nach Verlusten
- LLM erhält direkten Exchange-Key oder freie Orderfunktion
- automatisches Hochskalieren 250 → 500 → 750 → 1000 USDT
- Holdout nach Einsicht nachoptimieren
- deterministische Stress-Proxys als historische Orderbuchgenauigkeit ausgeben
- fehlende Execution-/Fault-Tests als „fertig“ deklarieren
- ORB oder Ichimoku allein wegen eines schönen Gesamt-Backtests auswählen

## Aktueller Implementierungsstand

**Vorhanden und automatisiert geprüft:**

- Full-System-Replay-Grundgerüst und gemeinsame Wallet-/Risk-Simulation
- exakte V8-Hashbindung
- Datenmanifest/Integritätsprüfung
- Golden Replay
- Checkpoint-Schema 2 mit Restore-/Reconciliation-Prüfung
- Gebühren, fixe Slippage, Timeouts
- deterministischer Spread-Stress-Proxy
- deterministische 1m-Execution-Verzögerung
- Partial-Fill-Stress für Entry und Limit-Exit
- Cancel-Reject-Stress
- Duplicate-Minute-Idempotenz und conflicting-duplicate fail closed
- Paper-Decision-Telemetrie und Paper-vs-Replay-Paritätschecker
- Failed-Breakout-/Volume-/Regime-Diagnostik
- Trial Ledger
- PBO-/DSR-Diagnostik
- Strategy Registry und manuelle Promotion-Grenzen
- fail-closed Research-Strategy-Routing-Contract mit ORB/Ichimoku/Bollinger/NO_TRADE
- kausaler Walk-Forward-Fenster-/Fold-Contract

**Weiterhin teilweise oder offen:**

- echte Exchange-/Boot-Reconciliation
- sub-minute Latenz und historisches Orderbuch/Queue-Modell
- asynchrones out-of-order Fill-/Order-Event-Reordering
- Risk-Service-/DB-Fault-Szenarien
- vollständige Red-Team-Matrix
- vollständige Walk-Forward-Strategie-Runner-/Promotion-Integration
- Parameter-Plateau-/Lag-/Konzentrations-Release-Reports
- Offline AI Research Plane: Design vorhanden, autonome Ausführung aus Sicherheitsgründen deaktiviert
- produktive ORB-/Ichimoku-/Bollinger-Strategien und finaler Regime-Hybrid

**Noch nicht empirisch abgenommen:**

- mehrjähriger lokaler Full-History-Replay auf den echten Binance-Dateien
- Fee-Stress-Replay
- echte Paper-vs-Replay-Parität auf einem überlappenden Paper-Zeitraum
- Walk-Forward einer echten neuen Challenger-Familie
- vollständige PBO/DSR/Plateau-Auswertung einer echten Challenger-Familie

**Noch nicht als produktive Strategieänderung umzusetzen:**

- B2 Volume-Challenger
- aktives neues Regime-Gate für V8
- ORB/FVG/BOS-Challenger
- Bollinger-MR-Challenger
- Ichimoku-Challenger
- finaler Multi-Strategy-Regime-Router

Der detaillierte Soll/Ist-Abgleich steht in `docs/DEEP_RESEARCH_GAP_AUDIT_DE.md`. Ein fehlender Punkt dort darf nicht durch Dokumentationssprache als bereits implementiert ausgegeben werden.
