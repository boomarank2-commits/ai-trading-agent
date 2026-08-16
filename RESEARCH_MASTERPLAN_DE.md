# Verbindlicher Research-Masterplan – V8 und Challenger

Stand: 16.08.2026

## Autorität

Diese Datei ist ab jetzt der **verbindliche technische und methodische Fahrplan** für die Weiterentwicklung dieses Repositories.

Sie ersetzt den früheren Auftrag `CODEX_NEXT_PHASE_LIVE_REPLAY_DE.md` als aktive Arbeitsgrundlage. Die frühere Datei war eine Vorversion und darf nicht mehr als aktueller Sollzustand verwendet werden.

Der Masterplan basiert auf der zuletzt konsolidierten Deep-Research-Auswertung. Bei Widersprüchen zwischen älteren Notizen, alten Codex-Aufträgen und dieser Datei gilt **diese Datei**.

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

## Verbindliche Forschungsreihenfolge

### Phase 0 – Baseline einfrieren

1. V8-SHA unverändert lassen.
2. 250-USDT-Paper-Forward weiterführen.
3. Alle Research-Versuche inklusive Fehlschläge im Trial Ledger führen.
4. Keine nachträgliche Holdout-Optimierung.

### Phase 1 – Full-System-Replay und Paper-Parität

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
- Golden Replay und Fault-Injection
- maschinenlesbare Telemetrie
- Paper-vs-Replay-Paritätsprüfung

**Release-Blocker:** Bei identischem kausalem Input dürfen Signal- oder Risk-Allow/Reject-Entscheidungen nicht unerklärt zwischen Paper und Replay abweichen.

Lokale empirische Gates nach Download:

1. Full-History-Replay BTC/ETH/SOL gemeinsam, Baseline-Fee 0,002 je Seite.
2. Fee-Stress 0,004 je Seite.
3. Paper-vs-Replay-Parität auf einem tatsächlich überlappenden Paper-Zeitraum.

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

Regime werden zunächst **nur gelabelt**. Ein `NO_TRADE`-Gate darf erst nach wiederholbar schwacher Attribution in mehreren Zeitslices und mindestens zwei Coins als eigener vorregistrierter Challenger entstehen.

### Phase 3 – Vorregistrierte V8-Challenger

Für die globale Volume-Hypothese sind ausschließlich diese Varianten vorgesehen:

- B0 = unverändertes V8
- B1 = V8 + `volume_ratio >= 1.00`
- B2 = V8 + `volume_ratio >= 1.25`

Nach Einsicht in B1/B2 wird **keine neue Schwelle spontan erfunden**.

B1 wurde als globaler Filter verworfen. B2 ist pausiert, bis Replay-/Diagnose-Gates belastbar sind.

Zusätzlich darf später maximal **ein** einfaches Regime-Gate vorregistriert werden, wenn die vorherige Attribution es rechtfertigt.

Kein Challenger ersetzt V8 allein aufgrund eines Gesamt-Backtests.

### Phase 4 – Separater Bollinger-Mean-Reversion-Challenger

Erst nach den vorherigen Gates darf eine Mean-Reversion-Strategie untersucht werden.

Sie bleibt eine **eigene Strategy-ID** und wird nicht in `CompressionBreakout250.py` gemischt.

Sicherheitsrahmen:

- Spot
- long-only
- kein Hebel
- kein Short
- kein Futures
- keine Positionsaufstockung
- bestehender Portfolio-Exposure-Cap bleibt erhalten

Research-Baseline:

- 15m
- Bollinger 20 / 2,0
- Long nach Berührung/Unterschreitung des unteren Bands und Close zurück hinein
- nur in kausal definiertem Range-Regime
- Exit zunächst am Mittelband

Vergleich:

- A = V8 allein
- B = MR allein
- C = virtuelles V8+MR-Portfolio unter demselben Gesamt-Exposure-Cap

Wichtigstes Ziel ist Diversifikation bzw. geringerer Drawdown/Time-under-Water, nicht nur eine höhere Endrendite.

### Phase 5 – Meta-Research

Vor jeder späteren Promotion müssen Multiple-Testing-Risiken sichtbar sein:

- vollständiges Trial Ledger
- CSCV/PBO
- Deflated Sharpe Ratio
- Parameter-Plateau statt isoliertem Optimum
- Pair- und Jahresslices
- Kostenstress
- PnL-Konzentration

PBO/DSR sind Research-Gates, keine Echtgeldfreigabe.

### Phase 6 – Shadow / Forward / manuelle Promotion

Robuste Challenger gehen zuerst in Shadow.

Danach:

1. frische Forward-Daten sammeln
2. bei Schwäche zurück auf REJECT/RESEARCH
3. bei robuster Evidenz PAPER-CANDIDATE-REVIEW
4. weitere Lifecycle-Schritte nur mit expliziter manueller Freigabe

Keine automatische Echtgeldfreigabe und keine automatische Kapitalerhöhung.

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
9. Parameterplateau / DSR / PBO.
10. Replay-/Determinismusprüfung.
11. Erst dann SHADOW.
12. Frische Forward-Evidenz.
13. Manuelle Review vor jeder Promotion.
14. Negative Ergebnisse dokumentieren, nicht löschen.

## Branch-Konvention

Keine Strategie-Forschungsänderung direkt auf `main`.

- `feature/replay-<thema>-YYYYMMDD`
- `research/v8-<experiment>-YYYYMMDD`
- `research/challenger-<strategie>-YYYYMMDD`

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
- Breakout-/Trend-/Volumen-/ATR-/RSI-/Momentum-Features
- BTC-Regime
- Entry-Kandidat
- Entry erlaubt/abgelehnt
- Ablehnungsgrund, soweit ohne Duplikation der Trading-Logik feststellbar
- offene Positionen / Exposure / Daily PnL / Risk-Lock, soweit verfügbar
- Orderstatus / angeforderter Preis / Fill / Slippage, soweit verfügbar
- Exit-Grund / PnL / MAE / MFE, soweit verfügbar
- Checkpoint-/Restart-Information im Replay

Observability darf das Trading-Verhalten nicht verändern. Wenn ein Grund nicht ohne Duplikation der Trading-Logik ermittelt werden kann, wird er als generischer Runtime-Reject protokolliert statt die Risk-Logik ein zweites Mal nachzubauen.

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
- Fault-Injection / fail closed
- Golden Replay
- Trial-Ledger-Schema
- Metrics-Reproduzierbarkeit
- PBO-/DSR-Inputvalidierung

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

## Aktueller Implementierungsstand

Bereits auf `main` vorhanden:

- Full-System-Replay-Grundgerüst
- gemeinsame Wallet-/Risk-Simulation
- exakte V8-Hashbindung
- Checkpoint/Restart
- Datenmanifest/Integritätsprüfung
- Golden-/Fault-/Risk-Tests
- Paper-Decision-Telemetrie
- Paper-vs-Replay-Paritätschecker
- Failed-Breakout-/Volume-/Regime-Diagnostik
- Trial Ledger
- PBO-/DSR-Diagnostik

Noch **nicht empirisch abgenommen**:

- mehrjähriger lokaler Full-History-Replay auf den echten Binance-Dateien
- Fee-Stress-Replay
- echte Paper-vs-Replay-Parität auf einem überlappenden Paper-Zeitraum

Noch **nicht als produktive Strategieänderung umzusetzen**:

- B2 Volume-Challenger
- aktives Regime-/`NO_TRADE`-Gate
- Bollinger-MR-Challenger
- Ichimoku
- ORB/FVG/BOS

Diese Punkte bleiben in der oben festgelegten Reihenfolge gesperrt, bis die jeweils vorherigen Gates ausreichend Evidenz geliefert haben.
