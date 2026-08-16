# Verbindlicher Research-Masterplan – V8, Research Plane und Challenger

Stand: 16.08.2026

## Autorität

Diese Datei ist der **verbindliche technische und methodische Fahrplan** für die Weiterentwicklung dieses Repositories.

Sie ersetzt den früheren Auftrag `CODEX_NEXT_PHASE_LIVE_REPLAY_DE.md` als aktive Arbeitsgrundlage. Die frühere Datei war eine Vorversion und darf nicht mehr als aktueller Sollzustand verwendet werden.

Die Grundlage sind die beiden aktuellen Deep-Research-Berichte zu Hermes/OpenClaw sowie zu den vier Video-Strategien. Bei Widersprüchen zwischen älteren Notizen, alten Codex-Aufträgen und diesem Masterplan gilt **dieser Masterplan**.

Die beiden Berichte setzen bei der Trend-Komponente unterschiedliche Schwerpunkte:

- Bericht A priorisiert als Engineering-Reihenfolge zunächst eine deterministische ORB-Retest-Baseline und anschließend Bollinger Mean Reversion.
- Bericht B empfiehlt als Zielbild insbesondere Ichimoku Trend Engine + Bollinger Mean-Reversion Engine.

Diese Abweichung wird **nicht stillschweigend aufgelöst**. ORB-Retest und Ichimoku werden als getrennte Trend-Challenger-Familien behandelt. Keiner wird allein aufgrund der Reihenfolge seiner Implementierung zum Sieger erklärt. Erst vorregistrierte Out-of-Sample-, Kosten-, Walk-Forward- und Robustheitsevidenz darf entscheiden, welche Trend-Komponente später in ein Multi-Strategy-System eingeht.

## Oberste Grundregel

**V8 bleibt der eingefrorene Champion.**

Neue Ideen dürfen V8 nicht nachträglich so verändern, bis ein schöner Backtest entsteht. Neue Hypothesen werden als getrennte Challenger oder als reine Diagnose-/Telemetrieänderungen umgesetzt. Ein negativer Versuch bleibt im Trial Ledger erhalten.

Aktueller Sicherheitsvertrag:

- Strategie: `CompressionBreakout250` / V8
- Binance Spot / USDT
- long-only, 1x
- kein Futures, Margin, Short, DCA oder Martingale
- 250 virtuelle USDT
- maximal 80 USDT je Position
- maximal drei Positionen / 240 USDT Gesamtengagement
- Hard-Stop -5,5 %
- keine automatische Kapitalerhöhung
- keine automatische Echtgeldfreigabe
- Research-/LLM-Code erhält keine freie Exchange-Orderfunktion

Bindender LF-normalisierter V8-SHA256:

`9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280`

Status: **READY FOR EXTENDED PAPER TEST – NOT READY FOR REAL MONEY.**

## Zielarchitektur aus Deep Research

Das langfristige Ziel ist **keine einzelne ständig handelnde Super-Strategie**, sondern eine deterministische Multi-Strategy Execution Engine mit separater AI Research Plane.

Der spätere Strategie-Zustandsraum muss mindestens diese drei Zustände unterstützen:

- `TREND/BREAKOUT`
- `RANGE/MEAN_REVERSION`
- `NO_TRADE`

**`NO_TRADE` ist die Default-Aktion**, wenn Datenqualität, Regime, Signalqualität oder Risk Policy keine belastbare Freigabe liefern.

Das Zielbild ist:

```text
Exchange WebSocket / REST
        ↓
Market Data Normalizer
        ↓
Feature Engine
        ↓
Data Quality Gate ───────────────→ NO_TRADE bei stale/fehlerhaften Daten
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

Im zeitkritischen Trading-Pfad gilt ausschließlich:

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

### Phase 1 – Full-System-Replay, Parität und realistischer Execution-/Cost-Simulator

Vor Strategie-Tuning müssen folgende Infrastrukturpunkte belastbar sein:

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

Der bestehende Replay ist **noch nicht automatisch ein vollständiger realistischer Execution-Simulator**. Vor einer Behauptung vollständiger Produktionsnähe müssen zusätzlich explizit modelliert und getestet werden:

- Gebühren
- Spread
- Slippage
- deterministische Latenz-/Verspätungsannahmen
- Order-Timeouts und Cancel-Zustände
- Partial Fills oder eine dokumentierte konservative Ersatzannahme
- Cancel Reject
- duplicate/out-of-order Events
- Position Reconciliation
- Position bereits beim Start vorhanden
- Restart während offener Orders/Positionen

Bis diese Punkte umgesetzt und getestet sind, ist der Execution-Teil als **PARTIAL** zu kennzeichnen.

**Release-Blocker:** Bei identischem kausalem Input dürfen Signal- oder Risk-Allow/Reject-Entscheidungen nicht unerklärt zwischen Paper und Replay abweichen.

Lokale empirische Gates nach Download:

1. Full-History-Replay BTC/ETH/SOL gemeinsam, Baseline-Fee 0,002 je Seite.
2. Fee-Stress 0,004 je Seite.
3. Paper-vs-Replay-Parität auf einem tatsächlich überlappenden Paper-Zeitraum.
4. Execution-Stress erst dann als bestanden markieren, wenn die oben genannten Order-/Reconciliation-Szenarien maschinell getestet sind.

### Phase 1b – Red-Team-/Fault-Injection-Matrix

Die Deep-Research-Red-Team-Matrix ist verbindlich als Testziel zu führen:

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

Das gewünschte Verhalten lautet grundsätzlich: **bei Unsicherheit Chancen verlieren statt unkontrolliert Kapital riskieren**. Neue Entries fallen bei ungeklärter sicherheitsrelevanter Unsicherheit auf `NO_TRADE`/fail closed zurück. Ein Test darf nur als abgedeckt gelten, wenn ein automatisierter Test oder eine klar dokumentierte deterministische Ersatzregel existiert.

### Phase 2 – V8-Diagnostik, noch ohne Entry-Änderung

Zuerst beobachten und erklären, nicht filtern.

Für jeden Entry-Kandidaten soweit technisch verfügbar protokollieren:

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

Ziel ist insbesondere die Ursachenanalyse der `failed_4h_breakout`-Trades.

Regime werden zunächst **nur gelabelt**. Ein aktives neues Regime-Gate für V8 darf erst nach wiederholbar schwacher Attribution in mehreren Zeitslices und mindestens zwei Coins als eigener vorregistrierter Challenger entstehen.

### Phase 3 – Vorregistrierte V8-Challenger

Für die globale Volume-Hypothese sind ausschließlich diese Varianten vorgesehen:

- B0 = unverändertes V8
- B1 = V8 + `volume_ratio >= 1.00`
- B2 = V8 + `volume_ratio >= 1.25`

Nach Einsicht in B1/B2 wird **keine neue Schwelle spontan erfunden**.

B1 wurde als globaler Filter verworfen. B2 ist pausiert, bis Replay-/Diagnose-Gates belastbar sind.

Zusätzlich darf später maximal **ein** einfaches Regime-Gate vorregistriert werden, wenn die vorherige Attribution es rechtfertigt.

Kein Challenger ersetzt V8 allein aufgrund eines Gesamt-Backtests.

### Phase 4 – Eigenständige Strategie-Challenger

Erst nach Replay-, Paritäts-, Execution-, Red-Team- und Diagnose-Gates werden neue Strategie-Familien aktiviert.

#### 4A – ORB-Retest-Challenger

Der erste einfache Breakout-Prototyp aus Bericht A bleibt bewusst klein:

- Opening Range deterministisch definieren
- bestätigter Ausbruch
- zunächst nur Retest-Setup
- FVG und BOS/Reversal ausdrücklich **noch nicht** gleichzeitig hinzufügen
- eigene Strategy-ID
- keine Änderung an V8

#### 4B – Bollinger-Mean-Reversion-Challenger

- eigene Strategy-ID
- 15m
- Research-Default Bollinger 20 / 2,0; kein behauptetes Video-Optimum
- Long nach Berührung/Unterschreitung des unteren Bands und bestätigtem Close zurück hinein
- nur in kausal definiertem Range-Regime
- Exit zunächst am Mittelband
- Spot, long-only, kein Hebel, kein Short, keine Positionsaufstockung

#### 4C – Ichimoku-Trend-Challenger

Der zweite Deep-Research-Bericht darf nicht verloren gehen. Als eigenständige Trend-Familie wird später geprüft:

- Tenkan/Kijun 9/26
- Span-B 52 / Displacement 26 als Research-Default
- Preis/Cloud, Tenkan/Kijun, Chikou und Future-Cloud kausal und eindeutig implementieren
- Golden Tests für die Indikatorberechnung
- kein ungeprüftes Übernehmen ambiger Sekundärtranskripte
- eigene Strategy-ID
- keine Änderung an V8

Die Reihenfolge 4A/4B/4C ist eine Implementierungsreihenfolge, **keine Ergebnisrangliste**. ORB und Ichimoku sind konkurrierende bzw. ergänzende Trend-Challenger; erst die Evidenz entscheidet.

#### 4D – Erst später Multi-Strategy/Regime-Router

Ein Hybrid darf erst entstehen, wenn mindestens eine Trend-Familie und die Mean-Reversion-Familie getrennt belastbare Evidenz besitzen.

Dann wird verglichen:

- Trend-Engine allein
- Bollinger-MR allein
- Regime-Hybrid unter demselben Gesamt-Exposure-Cap
- V8 als bestehender Champion/Benchmark
- einfacher Benchmark, soweit sinnvoll

Der Router darf niemals bei unklarem Regime erzwingen, dass eine der Strategien handelt. Unklar bedeutet `NO_TRADE`.

### Phase 5 – Walk-Forward und Meta-Research

Vor jeder späteren Challenger-Promotion müssen Multiple-Testing- und Stabilitätsrisiken sichtbar sein:

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
- Monte-Carlo/Block-Bootstrap-Drawdown, sobald dafür belastbare Return-Serien vorhanden sind

Die in Deep Research genannten Zahlen sind **Projekt-Engineering-Startgates, keine universellen wissenschaftlichen Wahrheiten**. Für neue Challenger sollen sie vor Sicht auf den Holdout als anfängliche Zielschwellen vorregistriert oder begründet ersetzt werden:

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

Diese Schwellen werden **nicht rückwirkend benutzt, um V8 umzuschreiben oder zu demoten**. Sie sind ein vorregistrierbarer Prüfrahmen für neue Challenger und können nur vor einer neuen Experimentfamilie mit dokumentierter Begründung geändert werden.

PBO/DSR sind Research-Gates, keine Echtgeldfreigabe.

### Phase 6 – Shadow / Forward / manuelle Promotion

Robuste Challenger gehen zuerst in Shadow bzw. einen äquivalenten nicht-kapitalwirksamen Forward-Modus.

Danach:

1. frische Forward-Daten sammeln
2. bei Schwäche zurück auf REJECT/RESEARCH
3. bei robuster Evidenz PAPER-CANDIDATE-REVIEW
4. weitere Lifecycle-Schritte nur mit expliziter manueller Freigabe

Keine automatische Echtgeldfreigabe und keine automatische Kapitalerhöhung.

### Phase 7 – Offline AI Research Agent

Die Deep-Research-Zielarchitektur beinhaltet einen AI Quant Researcher. Der aktuelle autonome Research-Scheduler bleibt jedoch **fail-closed deaktiviert**, solange er nicht in einer ausreichend isolierten Umgebung läuft.

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

1. Verändert sie V8 nicht? -> Diagnose/Telemetrie.
2. Verändert sie V8? -> separate Challenger-Branch.
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
13. Erst dann SHADOW.
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

Für Entry-Entscheidungen sollen – soweit im jeweiligen Pfad verfügbar – mindestens folgende Provenance-/Decision-Felder geführt werden:

- `experiment_id`
- `run_id`
- `git_sha`
- `strategy_name`
- `strategy_sha_lf` bzw. exakter Runtime-SHA
- `config_hash`
- `risk_policy_hash`
- `data_manifest_hash` im Replay
- Modus, Pair, Candle-Close UTC
- Datenqualitätsstatus
- Regime-Label
- Breakout-/Trend-/Volumen-/ATR-/RSI-/Momentum-Features
- BTC-Regime
- Entry-Kandidat
- Entry erlaubt/abgelehnt
- Ablehnungsgrund, soweit ohne Duplikation der Trading-Logik feststellbar
- offene Positionen / Exposure / Daily PnL / Risk-Lock, soweit verfügbar
- Orderstatus / angeforderter Preis / Fill / Partial Fill / Slippage / Fee / Spread / Latenz, soweit verfügbar
- Reconciliation-Status, soweit verfügbar
- Exit-Grund / PnL / MAE / MFE, soweit verfügbar
- Checkpoint-/Restart-Information im Replay

Observability darf das Trading-Verhalten nicht verändern. Wenn ein Grund nicht ohne Duplikation der Trading-Logik ermittelt werden kann, wird er als generischer Runtime-Reject protokolliert statt die Risk-Logik ein zweites Mal nachzubauen.

## Ergebnis-Dashboard für neue Releases

Sobald echte Daten vorliegen, soll die Research-Auswertung mindestens erzeugen bzw. aus Rohdaten ableiten können:

- Equity Curve netto nach Kosten
- Underwater-/Drawdown-Verlauf
- Rolling Sharpe 90/180 Tage, soweit Stichprobe sinnvoll
- Monats-/Zeitslice-Auswertung
- PnL nach Regime
- PnL nach Asset
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

Replay-/Research-CI muss zusätzlich die folgenden Eigenschaften abdecken:

- Clock-Causality / keine Future-Candle
- Checkpoint-Restart-Determinismus
- Paper-Replay-Parität
- Golden Replay
- Trial-Ledger-Schema
- Metrics-Reproduzierbarkeit
- PBO-/DSR-Inputvalidierung
- vollständige Red-Team-Matrix als Coverage-Ziel; fehlende Szenarien müssen im Gap-Audit sichtbar bleiben

## Verbotene Abkürzungen

Folgende Änderungen sind ausdrücklich **nicht** Teil des aktuellen Plans:

- V8 mit Bollinger + Ichimoku + ORB/FVG/BOS vermischen
- Futures/Perpetuals aktivieren
- Shorts aktivieren
- Hebel 5x/8x oder anderer fixer Hebel
- Stoploss/Protections abschwächen, um Backtests zu verschönern
- LLM ändert Live-Parameter nach Verlusten
- LLM erhält direkten Exchange-Key oder freie Orderfunktion
- automatisches Hochskalieren 250 -> 500 -> 750 -> 1000 USDT
- Holdout nach Einsicht nachoptimieren
- fehlende Execution-/Fault-Tests als „fertig“ deklarieren
- ORB oder Ichimoku ohne Vergleich allein wegen eines schönen Gesamt-Backtests auswählen

## Aktueller Implementierungsstand

Bereits vorhanden:

- Full-System-Replay-Grundgerüst
- gemeinsame Wallet-/Risk-Simulation
- exakte V8-Hashbindung
- Checkpoint/Restart-Grundmechanik
- Datenmanifest/Integritätsprüfung
- Golden Replay
- erste Fault-Injection für ungesunde/stale Daten
- Paper-Decision-Telemetrie
- Paper-vs-Replay-Paritätschecker
- Failed-Breakout-/Volume-/Regime-Diagnostik
- Trial Ledger
- PBO-/DSR-Diagnostik
- Strategy Registry und manuelle Promotion-Grenzen

**Nur teilweise umgesetzt:**

- realistischer Execution-/Cost-Simulator: Gebühren, fixe Slippage und Timeouts existieren; Spread, deterministische Latenz, Partial Fills, Cancel-Reject und vollständige Reconciliation-Szenarien fehlen noch bzw. sind nicht vollständig getestet
- Red-Team-Matrix: stale/data-unhealthy ist getestet; die vollständige Deep-Research-Matrix ist noch nicht abgedeckt
- Offline AI Research Plane: Design vorhanden, autonome Ausführung aus Sicherheitsgründen absichtlich deaktiviert
- Multi-Strategy-Regime-Architektur: Zielvertrag definiert, aber noch keine produktiven ORB-/Ichimoku-/Bollinger-Komponenten aktiv

Noch **nicht empirisch abgenommen**:

- mehrjähriger lokaler Full-History-Replay auf den echten Binance-Dateien
- Fee-Stress-Replay
- echte Paper-vs-Replay-Parität auf einem überlappenden Paper-Zeitraum
- Walk-Forward der neuen Challenger
- vollständige PBO/DSR/Plateau-Auswertung einer echten Challenger-Familie

Noch **nicht als produktive Strategieänderung umzusetzen**:

- B2 Volume-Challenger
- aktives neues Regime-Gate für V8
- ORB/FVG/BOS-Challenger
- Bollinger-MR-Challenger
- Ichimoku-Challenger
- finaler Multi-Strategy-Regime-Router

Der detaillierte Soll/Ist-Abgleich steht in `docs/DEEP_RESEARCH_GAP_AUDIT_DE.md`. Ein fehlender Punkt dort darf nicht durch Dokumentationssprache als bereits implementiert ausgegeben werden.