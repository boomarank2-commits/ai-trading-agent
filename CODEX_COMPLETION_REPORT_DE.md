# CODEX Completion Report – V8 Replay/Research-Umbau

Stand: 16.08.2026

## Auftrag

Umsetzung der priorisierten Punkte aus dem V8-Deep-Research-Fahrplan, ohne den eingefrorenen V8-Signalcode durch nachträgliches Tuning zu verändern.

## Umgesetzt

- separater Entwicklungszweig `feature/replay-v8-parity-20260816`
- Frozen-V8-Hash-Contract in CI
- historische monotone Simulationsuhr
- 15m-Signale erst nach Candle-Close; 1m Detail-Execution
- punkt-in-zeit korrektes 1h-/4h-Informative-Merging
- exakte, gehashte V8-Quelle als Signalautorität; keine zweite Entry-/Exit-Strategieformel
- gemeinsames 250-USDT-Wallet für BTC/ETH/SOL
- 80-USDT-Positionscap, 240-USDT-Exposure, max. drei Positionen
- Daily-Closed-Loss-Guard, Cooldown, StoplossGuard, MaxDrawdown-Lock
- Kill-Switch und Data-Health fail-closed
- Hard-Stop, effektives +50-%-ROI und V8-`custom_exit`
- deterministische Entry-/Exit-Limitorders mit Timeouts
- konservative Same-1m-Bar-Reihenfolge Stop vor ROI
- Checkpoint/Restart mit State-Hash
- Datenmanifest mit SHA-256, UTC, Gap-/Duplikatprüfung
- maschinenlesbare Run-Telemetrie und getrennte Run-Verzeichnisse
- behavior-preserving Paper-Signal-/Entry-Confirmation-Telemetrie außerhalb der Strategy-Datei
- Paper-vs-Replay-Paritätschecker
- Analyse nach Pair/Jahr/Monat/Exit und PnL-Konzentration
- read-only Failed-Breakout-/Volume-/Breakout-Distanz-/Regime-Diagnostik mit Entry-Order-Verknüpfung
- Trial Ledger inkl. negativer/pausierter Volume-Experimente
- statistischer Audit für CSCV/PBO und Deflated-Sharpe-Diagnostik
- Golden-Replay-, Restart-, Fail-closed-, Kill-Switch-, Exposure- und Same-Bar-Tests
- Windows-Helferskripte für Daten, Replay, Auswertung und Paritätscheck
- Replay-/Paper-Artefakte in `.gitignore`

## Bewusst nicht verändert

- `runtime/user_data/strategies/CompressionBreakout250.py`
- `STARTBOT.bat` Lebenszyklus und Kill-on-close-Vertrag
- Binance Spot / long-only / kein Hebel
- V8 Entry-/Exit-Parameter
- bestehende Paper-Datenbank
- keine Futures, Shorts, Margin oder automatische Kapitalerhöhung

## Empirische Gates nach Download

Die Software kann in CI ohne die mehrjährigen lokalen Binance-Feather-Dateien nur mit Golden-/Contract-Fixtures geprüft werden. Nach Download sind deshalb zwei lokale Research-Gates vorgesehen:

1. Full-History-Replay mit den lokalen BTC/ETH/SOL-Daten und Baseline-Fee 0,002 sowie Fee-Stress 0,004.
2. Paper-/Replay-Parität auf einem tatsächlich überlappenden Paper-Zeitraum. Ein Mismatch bleibt Release-Blocker für jede spätere Strategie-Promotion.

Diese Gates verändern V8 nicht; sie erhöhen lediglich die Evidenz.

## Status

**Replay-/Research-Infrastruktur implementiert. V8 bleibt READY FOR EXTENDED PAPER TEST – NOT READY FOR REAL MONEY.**
