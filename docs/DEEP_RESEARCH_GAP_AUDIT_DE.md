# Deep-Research-Soll/Ist-Audit

Stand: 18.08.2026

Dieses Dokument ist der aktuelle technische Soll/Ist-Status zum V12-Research-Zweig. Historische V8-Audits bleiben über Git-Historie und `research/` nachvollziehbar, sind aber nicht mehr der aktuelle Betriebszustand.

Statuswerte:

- **DONE** – technisch vorhanden und geprüft
- **PARTIAL** – Grundlage vorhanden, aber noch nicht vollständig
- **RESEARCH** – bewusst nur Research-/Candidate-Pfad
- **EMPIRICAL-GATE** – Code vorhanden, reale Datenprüfung noch erforderlich
- **REJECTED** – getesteter Weg verworfen

## Aktueller Runtime-Zustand

| Bereich | Status | Aktueller Befund |
|---|---|---|
| Aktive Strategy-Datei | **DONE** | `CompressionBreakout250.py`, `STRATEGY_VERSION = "V11"` |
| V12 | **RESEARCH** | Optimizer/Family-League; verändert den aktiven Hotpath nicht automatisch |
| Pair-Unabhängigkeit | **DONE** | BTC/ETH/SOL nutzen nur eigene 15m/1h/4h-Regime-/Signaldaten |
| Regime | **DONE in V11** | `TREND/BREAKOUT`, `RANGE/MEAN_REVERSION`, `NO_TRADE` |
| Strategy-Familien | **DONE in V11 / RESEARCH für Promotion** | ORB, Ichimoku, Bollinger werden geroutet; Robustheit noch nicht bewiesen |
| V8 Baseline | **DONE historisch** | eingefroren unter `research/baselines/V8/`; Vergleichsbasis, nicht aktive Strategy |

## Wichtigste offene Inkonsistenz

`runtime/user_data/config.json` und Teile des Start-/Datenbank-Lifecycles tragen noch historische V8-Bezeichnungen (`slow-donchian-v8-250-dryrun`, `tradesv8.dryrun.sqlite`).

Das ist **kein reiner Text-Cleanup**, weil ein DB-Pfadwechsel Paper-Historie, Reporter und Tests beeinflussen kann. Diese Migration muss separat und kontrolliert erfolgen.

## V12 Research

| Anforderung | Status | Befund |
|---|---|---|
| Pair-spezifische Kandidatensuche | **DONE** | BTC/ETH/SOL werden separat optimiert |
| Development/Validation/Blind | **DONE im Family-League-Research** | Candidate wird vor Blindtest eingefroren |
| Rolling Walk-Forward | **DONE/PARTIAL** | mehrere Folds vorhanden; Promotion noch nicht automatisiert |
| Kostenstress | **DONE im Research** | Baseline + zusätzlicher Stress werden ausgewertet |
| Familien-Attribution | **DONE** | PnL kann je Family ausgewertet werden |
| Automatische Live-Promotion | **BLOCKED by design** | keine Selbstumschreibung des aktiven Bots |
| Finaler lokaler Freqtrade-Beweis | **EMPIRICAL-GATE** | Gewinner muss mit exakter Strategy und 1m Detail lokal gegengeprüft werden |

## Bisherige V12-Erkenntnisse

Frühe V12-Varianten mit zu vielen kleinen Spezialisten waren OOS/Blind nicht robust und wurden verworfen. Der Research-Fokus liegt deshalb auf stabileren Family-League-/Walk-Forward-Auswertungen statt auf maximalem Trainingsgewinn.

Negative Varianten bleiben im Trial Ledger erhalten.

## Replay / Execution / Parität

| Anforderung | Status | Befund |
|---|---|---|
| monotone Simulationszeit | **DONE** | Replay-Infrastruktur vorhanden |
| geschlossene Candles / kausale Inputs | **DONE/PARTIAL** | Contract/Tests vorhanden; empirische Vollabnahme bleibt relevant |
| 1m Detail | **DONE** | für Backtest/Replay vorgesehen |
| Checkpoint/Restart | **DONE** | deterministische Tests vorhanden |
| Datenmanifest / Gaps / Duplikate | **DONE** | fail-closed Datenprüfung vorhanden |
| Spread/Delay/Partial Fill/Cancel Stress | **DONE als deterministische Stressmodelle** | keine historische Tick-/Orderbuch-Rekonstruktion |
| Paper-vs-Replay-Parität | **EMPIRICAL-GATE** | echte überlappende Paper-Stichprobe weiterhin nötig |
| reale Exchange-/Boot-Reconciliation | **PARTIAL** | kein vollständiger echter Exchange-Zustandsabgleich |
| asynchrones Fill/Event-Reordering | **PARTIAL** | noch keine vollständige realistische Modellierung |

## Research-Statistik

| Anforderung | Status |
|---|---|
| Trial Ledger inkl. Fehlschläge | **DONE** |
| PBO/DSR-Infrastruktur | **DONE als Tool / EMPIRICAL-GATE als Aussage** |
| Parameter-Plateau | **PARTIAL** |
| 1-Bar-Lag/Execution-Delay | **PARTIAL/DONE je Runner** |
| PnL-Konzentration | **PARTIAL/DONE je Report** |
| Monte-Carlo/Block-Bootstrap | **PLANNED** |

## Was nicht mehr als aktueller Plan gilt

- V8 als aktive Strategy oder aktueller Champion im Runtime-Sinn
- BTC-Regime als Steuerung für ETH/SOL
- ORB als automatisch bevorzugte Kernstrategie
- alte offene V9/V10/V11-Draft-PRs
- alte Root-Statusberichte wie `CODEX_COMPLETION_REPORT_DE.md`

## Aktuelle Reihenfolge

1. V12-Family-League-Ergebnisse vollständig auswerten.
2. Nur Familien/Varianten weiterführen, die Development, Validation, Blind und Walk-Forward tragen.
3. Verlierer dokumentieren und nicht wieder als aktiven Weg behandeln.
4. Kandidaten gegen Kosten, Lag, Drawdown und Parameter-Nachbarschaften prüfen.
5. Gewinner als neue Strategy-Version/Hash festschreiben.
6. Exakten Gewinner lokal mit Freqtrade und 1m-Detaildaten testen.
7. Erst danach aktive Runtime/DB-Migration bewusst planen.

Status: **RESEARCH ACTIVE – NOT READY FOR REAL MONEY.**
