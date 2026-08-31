# Hixton V6 – Präregistrierung vor Strategiecode

Status: **ANALYSEPHASE – NOCH KEIN V6-TRADINGCODE**

Basisexperiment: `HIXTON-V1-TRADE-DIAGNOSTICS`  
Strategie: `HIXTON-V1-DIAG`  
SHA256: `d43da032ad8aac714da60027702f84b584fc9cbc7e84038ca06847b5c2342290`

## Forschungsziel

V1 soll nicht durch pauschale Regimefilter auf einen kleinen Restbestand an Trades reduziert werden. Gesucht werden die kleinsten kausalen Änderungen, die überproportionalen Verlustschaden vermeiden und die großen Trendgewinner weitgehend erhalten.

Die Analyse trennt zwei Problemklassen:

1. **FAILED_START** – Verlusttrade erreicht nach Entry nicht einmal die exakte Fee-Break-even-MFE-Schwelle.
2. **PROFITABLE_THEN_LOST** – Verlusttrade erreicht die Fee-Break-even-MFE-Schwelle, endet aber später netto negativ.

MFE/MAE sind Outcome-Informationen. Sie dürfen nicht rückwirkend als Entry-Feature verwendet werden.

## Entry-Forschung

Zulässige Entry-Features müssen zum Signalzeitpunkt bekannt sein. Dazu gehören insbesondere Hixton-/VIDYA-/ATR-Struktur, Vorwelle/Chop, Breakout-Stärke, Candle-Range/Body, Volumen, RSI/ADX/MACD sowie bereits abgeschlossene 1h-/4h-Zustände.

Erster systematischer Screen:

- pro Coin chronologisch 60 % Discovery / 20 % Validation / 20 % Holdout,
- kontinuierliche Features nur als vorab definierte Discovery-Tails (q20 / q80),
- boolesche 1h-/4h-Zustände separat,
- keine Schwellen-Mikrooptimierung,
- Holdout darf keine Kandidatenauswahl beeinflussen.

Ein Entry-Kandidat darf nur weiterverfolgt werden, wenn die entfernte Gruppe sowohl in Discovery als auch Validation netto negativ ist, überproportionalen Verlustschaden trägt und die Fat-Tail-Gewinner nicht überproportional trifft.

Trade-Retention ist nur Guardrail, keine Zielmetrik.

## Exit-Forschung

Kein fixer Take Profit wird als V6-Grundlösung präregistriert.

`PROFITABLE_THEN_LOST` muss mit dem tatsächlichen zeitlichen Candle-Pfad untersucht werden. Ein Dead-Trend-Kandidat darf nur kausal verfügbare Informationen verwenden, beispielsweise:

- Zeit seit letztem laufenden Hoch,
- Drawdown vom laufenden Hoch,
- Verlust von VIDYA-/ATR-Struktur,
- bestätigter VIDYA-Slope-Knick,
- Momentum-/Volumenverlust,
- bereits abgeschlossene 1h-/4h-Zustandsänderung.

`max_rate` oder spätere MFE-Werte dürfen nicht benutzt werden, um einen rückblickend perfekten Exit zu konstruieren.

Same-Candle-High/Low-Reihenfolgen dürfen nicht erfunden werden. Exit-Kandidaten sind mit 1m-Pfaddaten bzw. konservativer Reihenfolge zu simulieren.

## Akzeptanz vor echter V6

Vor dem ersten V6-Tradingcode müssen vorliegen:

1. reproduzierbarer V1-Causal-Report,
2. mindestens ein Entry-Kandidat mit Discovery+Validation-Evidenz **oder** dokumentiertes Ergebnis, dass kein robuster Entry-Filter gefunden wurde,
3. Candle-Pfad-Analyse für `PROFITABLE_THEN_LOST` gegen Fat-Tail-Gewinner,
4. ein vor Holdout eingefrorener Dead-Trend-Kandidat,
5. einmalige Holdout-Auswertung,
6. anschließende echte chronologische Shared-Portfolio-Simulation mit 250 USDT und maximal 3 × 80 USDT.

Ein Ergebnis wird nicht akzeptiert, nur weil die Tradezahl niedriger ist.

## Aktueller Befund des ersten Screens

Der erste konservative Einzelfeature-Screen auf dem vollständigen V1-Diagnosebatch findet **keinen** Entry-Filter, der die festgelegten Discovery+Validation-Kriterien erfüllt.

Das ist ein wichtiger negativer Befund: V6 darf deshalb aktuell **keine** einfachen Regeln wie `ADX > X`, `RSI > X`, `4h grün` oder `Candle > X ATR` allein aufgrund der Gesamtdaten hartcodieren.

Der nächste Schwerpunkt ist die kausale Candle-Pfad-Analyse der `PROFITABLE_THEN_LOST`-Trades.
