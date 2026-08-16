# Deep-Research-Soll/Ist-Audit

Stand: 16.08.2026

Dieses Dokument verhindert, dass ein vorhandenes Grundgerüst versehentlich als vollständige Umsetzung der aktuellen Deep-Research-Zielarchitektur bezeichnet wird.

Statuswerte:

- **DONE**: im Repository technisch vorhanden und automatisiert geprüft
- **PARTIAL**: wesentliche Grundlage vorhanden, aber Deep-Research-Anforderung noch nicht vollständig umgesetzt/getestet
- **PLANNED**: Ziel vertraglich festgelegt, noch nicht implementiert
- **BLOCKED**: absichtlich gesperrt, bis eine Sicherheits-/Evidenzbedingung erfüllt ist
- **EMPIRICAL-GATE**: Code vorhanden, aber der reale lokale Datentest wurde noch nicht durchgeführt

## Architektur

| Deep-Research-Anforderung | Status | Repository-Befund / nächster Schritt |
|---|---|---|
| V8 als eingefrorener Champion | **DONE** | LF-SHA wird durch Research-Governance gebunden; Strategie bleibt unverändert. |
| LLM aus synchronem Orderpfad heraushalten | **DONE** | Agenten-/Registry-Grenzen verbieten freie Exchange-Orders; Paper-/Replay-Handel ist deterministisch. |
| Hot Path: Daten → Features → Gate → Regime → Strategie → Risk → Execution → Reconciliation | **PARTIAL** | V8/Replay besitzt Strategie, Risk und Execution-Grundpfad. Ein generischer Data-Normalizer/Regime-Router/OMS/Reconciliation-Layer für das spätere Multi-Strategy-System ist noch nicht vollständig als eigenständige Schicht umgesetzt. |
| Cold Path: Logs → AI Research → Hypothese → Tests → Registry → Shadow/Forward | **PARTIAL/BLOCKED** | Registry, Prompts, Ledger und Research-Desk-Prototyp existieren. Autonome Research-Ausführung ist aus Sicherheitsgründen hart deaktiviert, bis echte OS-/VM-/Container-Isolation besteht. |
| `TREND/BREAKOUT` / `RANGE/MEAN_REVERSION` / `NO_TRADE` | **PLANNED** | Jetzt verbindlich im Masterplan. Kein produktiver Multi-Strategy-Router aktiv. |
| `NO_TRADE` als Default bei Unsicherheit | **PARTIAL** | V8 handelt nur bei Signal/Risk-Allow; Data-Unhealthy blockiert im Replay. Ein expliziter generischer Multi-Strategy-NO_TRADE-State ist noch nicht implementiert. |
| Position Reconciliation | **PARTIAL** | Replay besitzt deterministischen internen Positionszustand; vollständige Exchange-/Restart-Reconciliation ist noch kein abgenommener eigener Layer. |

## Replay, Daten und Parität

| Anforderung | Status | Befund |
|---|---|---|
| monotone Simulationsuhr | **DONE** | Replay erzwingt monotone Zeit. |
| nur geschlossene Candles / kausale Informative-Daten | **DONE/PARTIAL** | Replay-/V8-Adapter ist auf geschlossene historische Daten ausgelegt; reale Full-History-Abnahme steht noch aus. |
| gemeinsames 250-USDT-Wallet BTC/ETH/SOL | **DONE** | Full-System-Replay-Grundgerüst vorhanden. |
| V8-Hashbindung | **DONE** | LF-normalisierter V8-SHA ist Governance-Vertrag. |
| Checkpoint/Restart-Determinismus | **DONE** | Mechanik und Tests vorhanden. |
| Datenmanifest, UTC, Gaps, Duplikate | **DONE** | Replay-Datenpfad besitzt Manifest-/Integritätsprüfungen. |
| Golden Replay | **DONE** | Fixture/Test vorhanden. |
| Paper-vs-Replay-Parität | **EMPIRICAL-GATE** | Checker vorhanden; echte überlappende Paper-Periode noch nicht lokal abgenommen. |
| mehrjähriger Full-History-Replay | **EMPIRICAL-GATE** | Code vorhanden; aktueller neuer Gesamtlauf noch nicht ausgeführt. |
| Fee-Stress 0,004 je Seite | **EMPIRICAL-GATE** | vorgesehen; aktueller neuer Replay-Lauf noch nicht ausgeführt. |

## Execution-/Cost-Simulator

| Anforderung | Status | Befund / Lücke |
|---|---|---|
| Gebühren | **DONE** | `fee_per_side` wird im Replay berücksichtigt. |
| fixe Slippage-Stressannahme | **DONE** | `slippage_bps` vorhanden. |
| Entry-/Exit-Timeouts | **DONE** | Pending Orders und Retry/Cancel vorhanden. |
| konservative Same-Bar-Reihenfolge | **DONE** | Positionspfad prüft Stop vor ROI und anschließend Custom Exit. |
| Spread-Modell | **PLANNED** | noch kein explizites Bid/Ask-/Spread-Modell. |
| deterministische Latenz | **PLANNED** | noch kein konfigurierbarer Latenzpfad. |
| Partial Fills | **PLANNED** | aktuelle Orders werden vollständig gefüllt, sobald der Limitpreis durch die 1m-Bar berührt wird. |
| Cancel Reject | **PLANNED** | Timeout/Cancel existiert, aber kein Cancel-Reject-Szenario. |
| duplicate Events | **PLANNED** | keine vollständige Idempotenz-/Duplicate-Event-Fault-Suite. |
| out-of-order Fill/Event | **PARTIAL** | monotone Bar-Zeit schützt den Hauptpfad; echte out-of-order Order-/Fill-Ereignisse sind nicht separat modelliert. |
| Position bei Boot / Exchange-Abgleich | **PLANNED** | noch keine vollständige Boot-Reconciliation im historischen Simulator. |

**Folgerung:** Der Replay darf aktuell als deterministischer Full-System-Replay bezeichnet werden, aber noch **nicht** als vollständig realistischer Exchange-/OMS-Simulator.

## Red-Team-/Fault-Injection

| Szenario aus Deep Research | Status |
|---|---|
| WebSocket/Data-feed-Ausfall | **PARTIAL** – Data-Unhealthy-Blocktest vorhanden |
| Exchange 2 s zu spät / Latenz | **PLANNED** |
| duplicate event | **PLANNED** |
| out-of-order fill | **PLANNED** |
| partial fill | **PLANNED** |
| cancel rejected | **PLANNED** |
| stale candle | **PARTIAL/DONE** – Datenintegritäts-/Health-Gates vorhanden |
| clock offset / nicht-monotone Zeit | **PARTIAL** – monotone Replay-Uhr vorhanden; expliziter Offset-Test ergänzen |
| strategy process restart | **PARTIAL** – Checkpoint vorhanden; Fault-Szenario mit offenen Orders/Positionen erweitern |
| risk service restart | **PLANNED** |
| position exists at boot | **PLANNED** |
| LLM service unavailable | **DONE als Sicherheitsarchitektur** – Trading-Hot-Path hängt nicht vom LLM ab |
| database temporarily unavailable | **PLANNED/PARTIAL** – Runtime-Grenzen existieren, gezielte Fault-Suite fehlt |

Die bisherige Datei `tests/replay/test_replay_fault_injection.py` deckt nicht die ganze Matrix ab. Ein einzelner Data-Health-Test darf deshalb nicht als vollständiges Red Team bezeichnet werden.

## Strategien und Regime

| Anforderung | Status | Befund |
|---|---|---|
| V8 unverändert weiter testen | **DONE** | aktiver Champion/Paper-Kandidat |
| B1 Volume >=1.00 | **REJECTED** | globaler Filter verworfen |
| B2 Volume >=1.25 | **BLOCKED** | bis Replay-/Diagnose-Gates pausiert |
| ORB-Retest als separater Challenger | **PLANNED** | Bericht A; noch nicht implementieren, bevor Infrastruktur-Gates schließen |
| Bollinger MR als separater Challenger | **PLANNED** | Range-Engine; 20/2 nur Research-Default |
| Ichimoku als separater Trend-Challenger | **PLANNED** | Bericht B; 9/26/52 als Research-Default, Golden Indicator Tests erforderlich |
| FVG/BOS | **BLOCKED/PLANNED** | erst nach einfacher ORB-Baseline |
| Regime Router | **PLANNED** | erst nach separater Validierung von Komponenten |
| Hybrid | **PLANNED** | darf Komponenten nicht vor ihrer Einzelvalidierung vermischen |

Die beiden Deep-Research-Berichte werden bewusst nicht so dargestellt, als hätten sie dieselbe Trend-Empfehlung. ORB und Ichimoku sind getrennte Trend-Hypothesen und müssen evidenzbasiert verglichen werden.

## Research-Statistik

| Anforderung | Status | Befund |
|---|---|---|
| Trial Ledger inkl. Fehlschläge | **DONE** | Schema/Governance vorhanden |
| Development/Validation/Holdout | **DONE/PARTIAL** | Registry/Ledger unterstützen die Trennung; echte neue Challenger fehlen noch |
| PBO/CSCV | **DONE als Tool**, **EMPIRICAL-GATE** als echte Auswertung | Implementierung/Test vorhanden; echte Trial-Universe-Auswertung steht aus |
| Deflated Sharpe | **DONE als Tool**, **EMPIRICAL-GATE** als echte Auswertung | dito |
| Walk-Forward | **PLANNED** | muss vor neuer Challenger-Promotion als eigener Workflow/Report vorhanden sein |
| Parameter-Plateau | **PLANNED/PARTIAL** | als Research-Gate dokumentiert; standardisierte Auswertung fehlt |
| 1.5x Kostenstress | **PLANNED** | neue Challenger müssen es vorregistriert messen |
| 1-Bar-Lag-Stress | **PLANNED** | noch kein standardisierter Runner |
| PnL-Konzentration | **PARTIAL** | Kennzahlen können aus Trades abgeleitet werden; verbindlicher Promotion-Report fehlt |
| Monte-Carlo/Block-Bootstrap-DD | **PLANNED** | erst bei geeigneten Return-Serien |

Die im Deep Research genannten Beispielschwellen (OOS Sharpe >0,8; DSR >95 %; PBO <20 %; PF >1,2; MaxDD <10 % usw.) sind **Engineering-Startgates und keine universellen Naturgesetze**. Für neue Challenger werden sie vor dem Holdout vorregistriert oder vorab begründet ersetzt; sie dienen nicht dazu, den eingefrorenen V8 rückwirkend schönzutunen.

## Monitoring/Dashboard

Noch nicht vollständig als standardisierter Release-Report umgesetzt sind:

- Equity netto nach Kosten
- Underwater/Drawdown Plot
- Rolling Sharpe 90/180 Tage
- Monats-/Zeitslice-Heatmap
- PnL nach Regime und Asset
- MAE/MFE Scatter
- Parameter-Heatmap/Plateau
- Kosten vs. Brutto-PnL
- Monte-Carlo/Block-Bootstrap-DD

Vor echten Daten dürfen keine Resultate oder Charts erfunden werden.

## Unmittelbare Reihenfolge ab jetzt

1. Keine V8-Strategieänderung.
2. Replay-/Execution-/Fault-Abdeckung vervollständigen, ohne Handelslogik zu ändern.
3. Danach echten Full-History-/Fee-Stress-/Parity-Lauf durchführen.
4. V8-Diagnostik einschließlich `failed_4h_breakout` auswerten.
5. Walk-Forward-/Promotion-Research-Harness vervollständigen.
6. Erst danach neue ORB-, Bollinger- und Ichimoku-Challenger getrennt vorregistrieren.
7. Regime-Router/Hybrid erst nach belastbarer Einzelkomponenten-Evidenz.

Status bleibt: **READY FOR EXTENDED PAPER TEST – NOT READY FOR REAL MONEY.**
