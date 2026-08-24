# V12.37 – SOL-Supertrend vom alten Donchian-Exit isolieren

Stand: 25.08.2026

Experiment: `V12.37-SOL-SUPERTREND-EXIT-ISOLATION`

Elternstand: `V12.36-SOL-ATR-SUPERTREND-IMPULSE-BOOL-FIX`

Finanzieller Elternstand: `V12.33-LTC-NO-TRADE-COUNTERFACTUAL`

Strategie: `CompressionBreakout250`, Version `V12.37`

Vor dem ersten V12.37-Finanzlauf registrierter SHA-256:

`56ad3d2263795828ad3280b1937e1e794aeea8b1caa5849bb114b2752abcbcf2`

Status: **VERWORFEN – AKTIVITÄTSHÜRDE NICHT BESTANDEN.**

## Ausschließlich regelkonforme Exit-Isolation

V12.36 legte offen, dass der geerbte Donchian-Custom-Exit alle neuen
SOL-Supertrend-Trades sofort beendete. Das widersprach der bereits vor dem
Lauf festgelegten Regel „Exit nur Supertrend-Shortflip beziehungsweise
Hard-Stop/ROI/Protections“. V12.37 ändert daher ausschließlich Folgendes:

- Der Tag wird auf V12.37 aktualisiert.
- Trades mit diesem Tag überspringen den alten Donchian-Failed-Breakout-
  Callback, genau wie bereits die separaten DOGE- und BCH-Familien.

Alle Entry-Regeln, der Shortflip-Exit, Supertrend(14, 3,5), EMA200, ADX20,
Momentum 5 Prozent, RSI 50–72, Ein-Stunden-Fenster, ein 80-USDT-Block,
LTC-NO-TRADE und die übrigen acht V12.33-Routen bleiben unverändert.

## Unveränderte bindende Hürden

1. SOL drei Jahre: mindestens +20 USDT, zwölf Trades, PF über 1,30 und
   Drawdown höchstens 12 Prozent.
2. SOL jüngstes Jahr: mindestens drei Trades und positiv.
3. SOL bei 0,3 Prozent Gebühr je Seite: mindestens +10 USDT und PF über 1,20.
4. Gemeinsam: Gewinn über +421,9152 USDT, PF mindestens 2,4530, Drawdown
   höchstens 12,1794 Prozent, SOL positiv und alle anderen positiven Paare
   weiter positiv.
5. Maximal drei belegte 80-USDT-Plätze; Freigabe erst nach dem endgültigen
   Trade-Exit; alle Datei-, Kapital-, Dry-run- und Sicherheitstests grün.

Keine Schwellenänderung nach Ergebnisansicht. Keine Echtgeldfreigabe oder
Gewinngarantie.

## Ergebnis

Der exakte SOL-Dreijahreslauf war finanziell positiv, verfehlte aber die vor
Ergebnisansicht festgelegte Mindeststichprobe:

- **+31,960 USDT**, Endkapital 281,960 USDT,
- 10 Trades statt mindestens 12,
- Profit-Faktor 2,36,
- 50 Prozent Trefferquote,
- geschlossener Drawdown 4,87 Prozent,
- ein 80-USDT-Block, kein Pyramiding.

Ein +49,99-Prozent-ROI-Gewinner lieferte +40,069 USDT; fünf Stop-Loss-Trades
verloren −23,522 USDT. Wegen der kleinen und stark konzentrierten Stichprobe
wurde die erste Hürde nicht vollständig bestanden. Jüngstes Jahr, Kosten- und
Shared-Gate werden nicht nachgeschoben. Entscheidung: `REJECT_DO_NOT_PROMOTE`.
Die positiven Regeln bleiben für frische Forward-Evidenz dokumentiert, werden
auf diesem Fenster aber nicht nachgestimmt.
