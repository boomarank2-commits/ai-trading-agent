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
- Holdout darf keine Kandidatenauswahl beeinflussen,
- Fat-Tail-Schutz wird segmentlokal berechnet; eine globale 3-Jahres-q95 darf Discovery/Validation nicht mit Holdout-Information beeinflussen,
- zusätzlich zur Anzahl geschützter Fat-Tails wird die tatsächlich entfernte Fat-Tail-Gewinnmasse begrenzt.

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

### Safety-V2-Regeln vor dem ersten Candle-Pfad-Lauf

Die Dead-Trend-Analyse wird vor Sichtung der Ergebnisse zusätzlich wie folgt gehärtet:

1. **Aktivierung erst nach bestätigtem 1m-Schluss über Fee-Break-even.** Ein einzelner Intraminute-Wick reicht nicht mehr, um den Dead-Trend-Timer zu starten.
2. **Signal und Ausführung werden getrennt.** Die Zustandsentscheidung darf nur auf einer vollständig geschlossenen 15m-Kerze beruhen. Der hypothetische Exitpreis ist der erste 1m-Open danach und nicht der bereits bekannte Schlusskurs der Signalkerze. Das entspricht der Next-Candle-Open-Semantik eines Freqtrade-Exit-Signals deutlich besser.
3. **Maximal 35 % der zum Checkpoint noch offenen, aktivierten Trades dürfen von einem Kandidaten ausgelöst werden.** Der Exit soll eine gezielte Fehlerklasse treffen und nicht zu einem versteckten pauschalen Früh-Exit werden.
4. **Dead-Trend-Enrichment ist zwingend.** In Discovery muss die ausgelöste Gruppe mindestens 1,20× so stark mit `PROFITABLE_THEN_LOST` angereichert sein wie die Basispopulation; in Validation mindestens 1,05×.
5. **Gewinner-Gewinnmasse wird geschützt.** Ein Kandidat darf in Discovery höchstens 5 % und in Validation/Holdout höchstens 10 % der Gewinnmasse der betroffenen Gewinner durch den früheren Exit zerstören.
6. **Fat-Tail-Gewinnmasse wird separat geschützt.** Discovery maximal 5 %, Validation/Holdout maximal 10 % negativer Delta-Schaden relativ zur segmentlokalen Top-5%-Gewinnmasse.
7. **Fat-Tail-Anzahl bleibt zusätzliche Guardrail.** Discovery höchstens 10 %, Validation/Holdout höchstens 20 % der segmentlokalen Fat-Tails dürfen ausgelöst werden.
8. **Holdout bleibt report-only.** Keine Schwelle, kein Feature und kein Checkpoint darf anhand des Holdouts verändert werden.

Diese Grenzen werden vor dem ersten lokalen Candle-Pfad-Lauf festgeschrieben und dürfen anschließend nicht nach Ergebnislage gelockert werden.

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

Der nächste Schwerpunkt ist die kausale Candle-Pfad-Analyse der `PROFITABLE_THEN_LOST`-Trades mit den oben festgeschriebenen Safety-V2-Regeln.
