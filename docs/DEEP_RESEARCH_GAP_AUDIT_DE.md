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
| Hot Path: Daten → Features → Gate → Regime → Strategie → Risk → Execution → Reconciliation | **PARTIAL** | V8/Replay besitzt Strategie, Risk, Execution und Replay-Reconciliation. Ein produktiver generischer Regime-/Multi-Strategy-Hot-Path ist absichtlich noch nicht aktiv. |
| Cold Path: Logs → AI Research → Hypothese → Tests → Registry → Shadow/Forward | **PARTIAL/BLOCKED** | Registry, Prompts, Ledger und Research-Desk-Prototyp existieren. Autonome Research-Ausführung bleibt bis zu echter OS-/VM-/Container-Isolation deaktiviert. |
| `TREND/BREAKOUT` / `RANGE/MEAN_REVERSION` / `NO_TRADE` | **DONE als Contract / PLANNED produktiv** | `runtime/research_strategy_contract.py` erzwingt die drei Zustände für spätere Challenger; er ist bewusst nicht in V8 verdrahtet. |
| `NO_TRADE` als Default bei Unsicherheit | **DONE als Research-Contract / PARTIAL produktiv** | Unhealthy Data, Risk-Reject, unklarer Regime-State oder Family-Mismatch fallen im Research-Router auf `NO_TRADE`; V8 bleibt unverändert. |
| Position Reconciliation | **PARTIAL** | Checkpoint-/Replay-Restore validiert offene Positionen, Exposure und orphan Orders fail-closed. Reale Exchange-/Boot-Reconciliation bleibt offen. |

## Replay, Daten und Parität

| Anforderung | Status | Befund |
|---|---|---|
| monotone Simulationsuhr | **DONE** | Replay erzwingt monotone Zeit. |
| nur geschlossene Candles / kausale Informative-Daten | **DONE/PARTIAL** | Replay-/V8-Adapter ist auf geschlossene historische Daten ausgelegt; reale Full-History-Abnahme steht noch aus. |
| gemeinsames 250-USDT-Wallet BTC/ETH/SOL | **DONE** | Full-System-Replay-Grundgerüst vorhanden. |
| V8-Hashbindung | **DONE** | LF-normalisierter V8-SHA ist Governance-Vertrag. |
| Checkpoint/Restart-Determinismus | **DONE** | Schema 2 persistiert zusätzlich Partial-Fill-/Duplicate-State; Golden-/Restart-Tests sind grün. |
| Datenmanifest, UTC, Gaps, Duplikate | **DONE** | Replay-Datenpfad besitzt Manifest-/Integritätsprüfungen. |
| Golden Replay | **DONE** | Fixture/Test vorhanden; Handelsresultat blieb trotz Schema-2-Erweiterung unverändert. |
| Paper-vs-Replay-Parität | **EMPIRICAL-GATE** | Checker vorhanden; echte überlappende Paper-Periode noch nicht lokal abgenommen. |
| mehrjähriger Full-History-Replay | **EMPIRICAL-GATE** | Code vorhanden; aktueller neuer Gesamtlauf noch nicht ausgeführt. |
| Fee-Stress 0,004 je Seite | **EMPIRICAL-GATE** | vorgesehen; aktueller neuer Replay-Lauf noch nicht ausgeführt. |

## Execution-/Cost-Simulator

| Anforderung | Status | Befund / Lücke |
|---|---|---|
| Gebühren | **DONE** | `fee_per_side` wird berücksichtigt. |
| fixe Slippage-Stressannahme | **DONE** | `slippage_bps` vorhanden. |
| Entry-/Exit-Timeouts | **DONE** | Pending Orders und Retry/Cancel vorhanden. |
| konservative Same-Bar-Reihenfolge | **DONE** | Stop vor ROI, danach Custom Exit. |
| Spread-Stress | **DONE als deterministischer Proxy** | `spread_bps` belastet Buy/Sell advers. Das ist kein historischer Bid/Ask-Orderbuch-Replay. |
| deterministische Latenz | **PARTIAL/DONE auf 1m-Granularität** | `execution_delay_minutes` verschiebt Fill-Berechtigung deterministisch. Sekunden-Latenzen bzw. echte Exchange-Timestamps werden damit nicht rekonstruiert. |
| Partial Fills | **DONE als deterministischer Stressmodus** | Entry- und Limit-Exit-Orders können in festen Slices über mehrere Touch-Bars gefüllt werden; kein volumenbasiertes Queue-Modell. |
| Cancel Reject | **DONE als deterministischer Stressmodus** | konfigurierbare Zahl abgelehnter Cancel-Versuche vor finalem Cancel/Retry. |
| duplicate Events | **DONE für 1m-Market-Batches** | identischer Batch wird idempotent ignoriert; gleicher Timestamp mit anderem Inhalt schlägt fail-closed fehl. |
| out-of-order Fill/Event | **PARTIAL** | monotone Bar-Zeit und conflicting-duplicate-Guard schützen den Hauptpfad; echtes asynchrones Fill-/Order-Event-Reordering ist noch nicht separat modelliert. |
| Position bei Boot / Exchange-Abgleich | **PARTIAL** | Checkpoint-Restore mit offener/teilgefüllter Position wird reconciled; echte Exchange-Positionen bei Prozessstart sind noch kein Live-Abgleich. |

**Folgerung:** Der Replay ist deutlich näher an einem Execution-Stress-Simulator, bleibt aber **kein historischer Tick-/Orderbuch-/Exchange-OMS-Rekonstruktor**. Spread, Latenz und Partial Fills sind konservative deterministische Stressannahmen.

## Red-Team-/Fault-Injection

| Szenario aus Deep Research | Status |
|---|---|
| WebSocket/Data-feed-Ausfall | **PARTIAL** – Data-Unhealthy blockiert neue Entries und Fill-Remainder |
| Exchange 2 s zu spät / Latenz | **PARTIAL** – deterministische Verzögerung vorhanden, jedoch nur 1m-Granularität |
| duplicate event | **DONE für 1m-Market-Batches** |
| out-of-order fill | **PLANNED/PARTIAL** – monotone Zeit schützt Bars, asynchrones Fill-Reordering fehlt |
| partial fill | **DONE als deterministischer Stressmodus** |
| cancel rejected | **DONE als deterministischer Stressmodus** |
| stale candle | **PARTIAL/DONE** – Datenintegritäts-/Health-Gates vorhanden |
| clock offset / nicht-monotone Zeit | **DONE für rückwärts laufende Replay-Zeit** – echter Clock-Drift/Offset bleibt außerhalb des historischen 1m-Modells |
| strategy process restart | **PARTIAL/DONE im Replay** – Checkpoint-Restore mit offener Teilposition getestet; OS-Prozessfehler selbst wird nicht simuliert |
| risk service restart | **PLANNED** |
| position exists at boot | **PARTIAL** – Replay-/Checkpoint-Reconciliation vorhanden, reale Exchange-Reconciliation fehlt |
| LLM service unavailable | **DONE als Sicherheitsarchitektur** – Hot Path hängt nicht vom LLM ab |
| database temporarily unavailable | **PLANNED/PARTIAL** – gezielte Fault-Suite fehlt |

Die Matrix ist damit wesentlich weiter, aber weiterhin **nicht vollständig**. Offene Punkte dürfen nicht als erledigt bezeichnet werden.

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
| Regime Router | **DONE als fail-closed Contract / PLANNED produktiv** | Research-Contract trennt ORB/Ichimoku/Bollinger und fällt bei Mismatch auf NO_TRADE; noch nicht mit produktiven Strategien verdrahtet. |
| Hybrid | **PLANNED** | darf Komponenten nicht vor ihrer Einzelvalidierung vermischen |

Die beiden Deep-Research-Berichte werden bewusst nicht so dargestellt, als hätten sie dieselbe Trend-Empfehlung. ORB und Ichimoku bleiben getrennte Trend-Hypothesen und müssen evidenzbasiert verglichen werden.

## Research-Statistik

| Anforderung | Status | Befund |
|---|---|---|
| Trial Ledger inkl. Fehlschläge | **DONE** | Schema/Governance vorhanden |
| Development/Validation/Holdout | **DONE/PARTIAL** | Registry/Ledger unterstützen die Trennung; echte neue Challenger fehlen noch |
| PBO/CSCV | **DONE als Tool**, **EMPIRICAL-GATE** als echte Auswertung | Implementierung/Test vorhanden; echte Trial-Universe-Auswertung steht aus |
| Deflated Sharpe | **DONE als Tool**, **EMPIRICAL-GATE** als echte Auswertung | dito |
| Walk-Forward | **PARTIAL** | kausale half-open Train/Test-Fenster, Validierung und Fold-Summary vorhanden; Strategie-Runner/Promotion-Integration fehlt noch. |
| Parameter-Plateau | **PLANNED/PARTIAL** | als Research-Gate dokumentiert; standardisierte Heatmap/Plateau-Auswertung fehlt |
| 1.5x Kostenstress | **PARTIAL** | Fold-Contract kann Cost-Stress-Resultate erzwingen/sichtbar machen; automatischer Challenger-Runner fehlt. |
| 1-Bar-Lag-Stress | **PARTIAL** | Fold-Contract führt die Prüfung explizit; standardisierter Signal-Delay-Runner fehlt. |
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
2. Verbleibende Replay-/Execution-/Fault-Lücken schließen, insbesondere asynchrone Event-Reihenfolge, reale Boot-/Exchange-Reconciliation, Risk-Service-/DB-Faults und präzisere Latenz-/Liquidity-Annahmen nur soweit methodisch sinnvoll.
3. Danach echten Full-History-/Fee-Stress-/Parity-Lauf durchführen.
4. V8-Diagnostik einschließlich `failed_4h_breakout` auswerten.
5. Walk-Forward-Runner/Promotion-Integration sowie Plateau-/Lag-/Konzentrationsreports vervollständigen.
6. Erst danach neue ORB-, Bollinger- und Ichimoku-Challenger getrennt vorregistrieren.
7. Regime-Router/Hybrid erst nach belastbarer Einzelkomponenten-Evidenz.

Status bleibt: **READY FOR EXTENDED PAPER TEST – NOT READY FOR REAL MONEY.**
