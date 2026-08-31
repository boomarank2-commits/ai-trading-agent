# Hixton V6 – Sequenzanalyse nach erstem Holdout

Status: **EXPLORATIVE FORSCHUNG – NOCH KEIN V6-TRADINGCODE**

Der erste Safety-V2/V3-Dead-Trend-Screen hat drei Einzelfeature-Kandidaten aus Discovery+Validation geliefert. Keiner dieser drei Kandidaten hat den vorher festgelegten Holdout-Vertrag vollständig bestanden. Der ursprüngliche 60/20/20-Holdout gilt damit als **verbraucht** und darf nicht erneut als unberührter Beweis für eine neue Regel bezeichnet werden.

## Ziel

Statt einzelne Schwellen nachträglich zu lockern, wird jetzt eine kleine, vorab festgelegte Familie kausaler **Sequenz-Zustände** untersucht. Die Idee lautet:

1. der Trade hat Fee-Break-even bereits durch einen abgeschlossenen 1m-Close bestätigt,
2. danach muss ein klarer Giveback/Strukturverlust eintreten,
3. zusätzlich muss Momentum bzw. der abgeschlossene 1h-Zustand Schwäche bestätigen,
4. der Exit wird weiterhin erst am ersten 1m-Open nach dem abgeschlossenen 15m-Signal modelliert.

Es werden **keine** neuen q-Schwellen gesucht. Verwendet werden ausschließlich q20/q80 aus zeitlich vorherliegenden Daten.

## Feste Walk-Forward-Fenster

Die vorhandenen drei Jahre werden nur noch als explorative Entwicklungsdaten benutzt.

Basistraining: alles vor `2024-09-01T00:00:00Z`.

Danach vier feste Vorwärtsfenster:

1. `2024-09-01` bis exklusiv `2025-03-01`
2. `2025-03-01` bis exklusiv `2025-09-01`
3. `2025-09-01` bis exklusiv `2026-03-01`
4. `2026-03-01` bis exklusiv `2026-09-01`

Für jedes Fenster werden Quantile nur aus vollständig abgeschlossenen Checkpoints **vor Beginn dieses Fensters** berechnet. Das Training wächst anschließend expandierend an.

## Drei festgelegte Routen

### ROUTE_A_60_GIVEBACK_MACD_1H

Nur am 60-Minuten-Checkpoint:

- `giveback_fraction >= q80`
- `macd_hist_atr <= q20`
- `trend_up_1h == 0`

### ROUTE_B_120_STRUCTURE_MACD_1H

Nur am 120-Minuten-Checkpoint:

- `macd_hist_atr <= q20`
- `price_minus_vidya_atr <= q20`
- `trend_up_1h == 0`

### ROUTE_C_TWO_STAGE

Zweistufige Zustandsmaschine:

1. bei 60 Minuten zuerst `ROUTE_A_60_GIVEBACK_MACD_1H`,
2. falls dort kein Exit ausgelöst wurde, bei 120 Minuten `ROUTE_B_120_STRUCTURE_MACD_1H`.

Ein Trade kann höchstens einmal ausgelöst werden; 60 Minuten hat Vorrang vor 120 Minuten.

## Exploratives Gate für eine spätere frische OOS-Prüfung

Dieses Gate kann **keine V6 freigeben**. Es entscheidet nur, ob eine Route stark genug ist, um unverändert für einen späteren wirklich neuen OOS-Test eingefroren zu werden.

Eine Route wird als `candidate_for_fresh_oos = 1` markiert, wenn alle Bedingungen erfüllt sind:

- aggregiertes Delta-P/L über die vier Vorwärtsfenster > 0,
- mindestens 3 von 4 Vorwärtsfenstern mit positivem Delta-P/L,
- in jedem Vorwärtsfenster mindestens 15 ausgelöste Trades,
- maximale Trigger-Quote je Fenster <= 20 %, 
- Dead-Trend-Enrichment in jedem Fenster >= 1,05x,
- Gewinner-Gewinnmassenschaden je Fenster <= 10 %,
- Fat-Tail-Gewinnmassenschaden je Fenster <= 10 %,
- Fat-Tail-Triggerquote je Fenster <= 20 %,
- aggregiertes Delta-P/L positiv bei mindestens 6 der 10 Coins.

Diese Grenzen werden mit diesem Dokument vor dem neuen lokalen Lauf festgeschrieben und nicht nach dessen Ergebnis gelockert.

## Was danach noch fehlt

Selbst wenn eine Route dieses explorative Gate besteht, ist sie **noch keine profitable V6**. Danach muss die gewählte Route unverändert auf Daten geprüft werden, die für diese Hypothese bislang nicht benutzt wurden. Erst danach darf ein echter Strategiecode gebaut und anschließend die chronologische 250-USDT-Shared-Portfolio-Simulation mit maximal 3 x 80 USDT durchgeführt werden.

Die vorhandenen drei Jahre dürfen für die neue Route nicht nochmals als finaler Holdout verkauft werden.
