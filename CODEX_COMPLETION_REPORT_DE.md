# Completion Report – V8 Replay-/Research-Infrastruktur

Stand: 16.08.2026

## Aktive Arbeitsgrundlage

Die verbindliche aktuelle Weiterentwicklungsgrundlage ist `RESEARCH_MASTERPLAN_DE.md`.

Der frühere Root-Auftrag `CODEX_NEXT_PHASE_LIVE_REPLAY_DE.md` war eine Vorversion und wird nicht mehr als aktiver Sollzustand verwendet.

## Was bereits implementiert ist

- Frozen-V8-Hash-Contract
- historische monotone Simulationsuhr
- 15m-Signale erst nach Candle-Close
- 1m Detail-Execution
- punkt-in-zeit korrektes 1h-/4h-Informative-Merging
- exakte, gehashte V8-Quelle als Signalautorität
- gemeinsames 250-USDT-Wallet für BTC/ETH/SOL
- 80-USDT-Positionscap, 240-USDT-Exposure, max. drei Positionen
- Daily-Closed-Loss-Guard, Cooldown, StoplossGuard, MaxDrawdown-Lock
- Kill-Switch und Data-Health fail-closed
- Hard-Stop, effektives +50-%-ROI und V8-`custom_exit`
- deterministische Entry-/Exit-Limitorders mit Timeouts
- konservative Same-1m-Bar-Reihenfolge Stop vor ROI
- Checkpoint/Restart mit State-Hash
- Datenmanifest mit SHA-256, UTC, Gap-/Duplikatprüfung
- maschinenlesbare Run-Telemetrie
- behavior-preserving Paper-Signal-/Entry-Confirmation-Telemetrie außerhalb der Strategy-Datei
- Paper-vs-Replay-Paritätschecker
- Analyse nach Pair/Jahr/Monat/Exit und PnL-Konzentration
- read-only Failed-Breakout-/Volume-/Breakout-Distanz-/Regime-Diagnostik
- Trial Ledger inklusive negativer/pausierter Volume-Experimente
- CSCV/PBO- und Deflated-Sharpe-Diagnostik
- Golden-Replay-, Restart-, Fail-closed-, Kill-Switch-, Exposure- und Same-Bar-Tests
- Windows-Helferskripte für Daten, Replay, Auswertung und Parität

## Was bewusst nicht verändert wurde

- `runtime/user_data/strategies/CompressionBreakout250.py`
- `STARTBOT.bat` Lebenszyklus und Kill-on-close-Vertrag
- Binance Spot / long-only / kein Hebel
- V8 Entry-/Exit-Parameter
- bestehende Paper-Datenbank
- keine Futures, Shorts, Margin oder automatische Kapitalerhöhung

## Noch offene empirische Gates

Die Software kann in CI ohne die mehrjährigen lokalen Binance-Dateien nur mit Golden-/Contract-Fixtures geprüft werden. Vor weiteren Strategy-Challengern müssen lokal noch durchgeführt werden:

1. Full-History-Replay BTC/ETH/SOL gemeinsam mit Baseline-Fee 0,002 je Seite.
2. Fee-Stress-Replay mit 0,004 je Seite.
3. Paper-/Replay-Parität auf einem tatsächlich überlappenden Paper-Zeitraum.
4. Auswertung der `failed_4h_breakout`-, Volume- und Regime-Telemetrie, bevor neue Filter aktiviert werden.

Ein unerklärter Paper-/Replay-Mismatch bleibt Release-Blocker für spätere Strategie-Promotion.

## Research-Reihenfolge nach diesen Gates

- zunächst V8-Diagnostik ohne Entry-Änderung
- B2 bleibt pausiert; keine zusätzliche Volume-Schwelle erfinden
- höchstens ein vorregistriertes Regime-/`NO_TRADE`-Gate nach belastbarer Attribution
- Bollinger Mean Reversion später als **separater** Challenger
- PBO/DSR/Trial-Ledger/Parameter-Plateau in jeder Promotion berücksichtigen
- robuste Challenger zunächst Shadow, danach frische Forward-Evidenz

## Status

**Infrastruktur an den aktuellen Deep-Research-Masterplan angepasst. V8 bleibt READY FOR EXTENDED PAPER TEST – NOT READY FOR REAL MONEY.**
