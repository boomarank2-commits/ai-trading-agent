# V8-B1: Volume-Ratio-1.00-Challenger

Stand: 16.08.2026

## Zweck

Dieser Research-Branch setzt den ersten klar vorregistrierten V8-Challenger aus `deep-research-report(1).md` um. Der produktive/eingefrorene V8-Champion auf `main` bleibt unverändert.

Hypothese: Ein Teil der vielen `failed_4h_breakout`-Verluste entsteht bei Breakouts ohne wenigstens durchschnittliches 15m-Volumen. V8 berechnet `volume_ratio` bereits, nutzte es bisher aber nicht als Entry-Filter.

## Exakte Änderung

Baseline B0:

- unverändertes V8 auf `main`
- Entry verlangt nur `volume > 0`

Challenger B1 auf diesem Branch:

- sämtliche bisherigen V8-Regeln bleiben erhalten
- zusätzlich muss beim Entry `volume_ratio_15m >= 1.00` gelten
- `volume_ratio = aktuelles 15m-Volumen / Durchschnitt der 20 vorherigen abgeschlossenen 15m-Kerzen`
- keine weitere Entry-, Exit-, Stop-, ROI-, Stake- oder Protection-Regel wird verändert

Der Threshold `1.00` ist vor dem Backtest festgelegt. Er darf nach Sichtung der Ergebnisse nicht nachträglich so verschoben werden, dass der Backtest besser aussieht. Ein möglicher B2-Test mit `1.25` muss als eigener Branch/Experiment-ID erfolgen.

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

Dieser Branch ist ausschließlich für Research/Backtest vorgesehen. Dry-run-Entries werden in der Strategy bewusst blockiert, damit die bestehende V8-Paper-Datenbank nicht durch einen ungeprüften Challenger vermischt wird. Der klassische Backtest bleibt davon unberührt.

## Abnahmematrix für den 3-Jahres-Test

Jeweils separat über die normale Backtest-Oberfläche:

1. BTC/USDT – 3 Jahre
2. ETH/USDT – 3 Jahre
3. SOL/USDT – 3 Jahre

Zu vergleichen mit B0:

| Pair | B0 Trades | B0 Rendite | B0 PF | B0 MaxDD |
|---|---:|---:|---:|---:|
| BTC/USDT | 20 | +20,995 % | 3,386 | 3,07 % |
| ETH/USDT | 20 | +22,194 % | 2,827 | 7,58 % |
| SOL/USDT | 21 | +17,650 % | 1,875 | 10,91 % |

## Entscheidungsregel

B1 wird nicht allein deshalb akzeptiert, weil die Endrendite höher ist. Besonders geprüft werden:

- wie viele `failed_4h_breakout` tatsächlich entfernt werden
- ob große historische Trend-/ROI-Gewinner verloren gehen
- Profit Factor
- Max Drawdown
- Tradezahl
- längste Verlustserie
- Stabilität je Pair
- spätere Jahresslices und Kostenstress, falls B1 den 3-Jahres-Screen übersteht

Status vor Backtest: **RESEARCH / NOT A PAPER CANDIDATE / NOT REAL MONEY**.
