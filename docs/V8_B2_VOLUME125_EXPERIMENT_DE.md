# V8-B2: Volume-Ratio-1.25-Challenger

Stand: 16.08.2026

## Zweck

Dieser Research-Branch setzt den zweiten und letzten vorregistrierten globalen Volume-Challenger aus `deep-research-report(1).md` um. Der produktive/eingefrorene V8-Champion auf `main` bleibt unverändert.

B1 (`volume_ratio >= 1.00`) hat im 3-Jahres-Screen BTC deutlich verbessert, ETH und SOL aber zu stark ausgedünnt bzw. verschlechtert. B2 wird trotzdem getestet, weil die Schwelle `1.25` bereits vor Einsicht in die B1-Ergebnisse als zweiter fester Challenger vorgesehen war. Es wird keine weitere globale Volume-Schwelle nachträglich hinzugefügt.

## Exakte Änderung

Baseline B0:

- unverändertes V8 auf `main`
- Entry verlangt nur `volume > 0`

Challenger B2 auf diesem Branch:

- sämtliche bisherigen V8-Regeln bleiben erhalten
- zusätzlich muss beim Entry `volume_ratio_15m >= 1.25` gelten
- `volume_ratio = aktuelles 15m-Volumen / Durchschnitt der 20 vorherigen abgeschlossenen 15m-Kerzen`
- keine weitere Entry-, Exit-, Stop-, ROI-, Stake- oder Protection-Regel wird verändert

Der Threshold `1.25` ist vor dem Backtest festgelegt. Nach Sichtung der Ergebnisse wird keine weitere globale Volume-Schwelle ergänzt. Damit ist die vorregistrierte B0/B1/B2-Volume-Serie abgeschlossen.

## B1-Ergebnis als Kontext, nicht als Optimierungsgrundlage

| Pair | B0 Rendite | B1 Rendite | B1 Trades | B1 PF | B1 MaxDD |
|---|---:|---:|---:|---:|---:|
| BTC/USDT | +20,995 % | +25,06 % | 10 | 10,26 | 1,22 % |
| ETH/USDT | +22,194 % | +13,16 % | 7 | 3,10 | 3,78 % |
| SOL/USDT | +17,650 % | +6,93 % | 15 | 1,53 | 8,45 % |

B1 wird nicht auf `main` promotet. B2 ist kein Versuch, B1 nachträglich passend zu machen, sondern die bereits vorab definierte zweite Schwelle.

## Sicherheitsvertrag

Unverändert:

- Binance Spot
- long-only
- 250 USDT Testkapital
- maximal 80 USDT je Position
- maximal 3 Positionen / 240 USDT Exposure
- Hard-Stop -5,5 %
- kein Trailing
- Limit Entry/Exit
- On-Exchange-Stop-Limit
- vorhandene Protections bleiben aktiv
- Backtest entscheidet weiter mit 15m und nutzt 1m nur für detailliertere Fill-/Stop-Simulation

Dieser Branch ist ausschließlich für Research/Backtest vorgesehen. Dry-run- und Live-Entries werden in der Strategy bewusst blockiert, damit die bestehende V8-Paper-Datenbank nicht durch einen ungeprüften Challenger vermischt wird. Der klassische Backtest bleibt davon unberührt.

## Abnahmematrix für den 3-Jahres-Test

Jeweils separat über die normale Backtest-Oberfläche:

1. BTC/USDT – 3 Jahre
2. ETH/USDT – 3 Jahre
3. SOL/USDT – 3 Jahre

Zu vergleichen mit B0 und B1. B0 bleibt der Champion.

| Pair | B0 Trades | B0 Rendite | B0 PF | B0 MaxDD |
|---|---:|---:|---:|---:|
| BTC/USDT | 20 | +20,995 % | 3,386 | 3,07 % |
| ETH/USDT | 20 | +22,194 % | 2,827 | 7,58 % |
| SOL/USDT | 21 | +17,650 % | 1,875 | 10,91 % |

## Entscheidungsregel

B2 wird nicht allein deshalb akzeptiert, weil einzelne Endrenditen höher sind. Besonders geprüft werden:

- wie viele `failed_4h_breakout` tatsächlich entfernt werden
- ob große historische Trend-/ROI-Gewinner verloren gehen
- Profit Factor
- Max Drawdown
- Tradezahl
- längste Verlustserie
- Stabilität je Pair
- ob der strengere Filter die Stichprobe in statistische Bedeutungslosigkeit drückt

Wenn B2 den globalen Ansatz nicht klar robuster macht, wird die globale Volume-Filter-Hypothese abgeschlossen und V8 B0 bleibt unverändert. Weitere Untersuchungen müssen dann als neue, ausdrücklich vorregistrierte Hypothesen erfolgen und dürfen nicht einfach weitere Schwellen aus denselben 3-Jahres-Daten durchsuchen.

Status vor Backtest: **RESEARCH / NOT A PAPER CANDIDATE / NOT REAL MONEY**.
