# V12.34 – SOL Range-Overreaction-Reversion

Stand: 24.08.2026

Experiment: `V12.34-SOL-RANGE-OVERREACTION-REVERSION`

Elternstand: `V12.33-LTC-NO-TRADE-COUNTERFACTUAL`

Strategie: `CompressionBreakout250`, Version `V12.34`

Vor dem ersten V12.34-Finanzlauf registrierter SHA-256:

`a640fec71c2a7a44f9993d848ce74fac8ae6762eebea2fe42cc01bc33ed898a6`

Status: **VERWORFEN – NICHT IN DEN PAPERBOT ÜBERNEHMEN.**

## Hypothese und genau eine Änderung

Der unveränderte SOL-Donchian-Pfad verlor im exakten gemeinsamen V12.33-Lauf
39,910 USDT. V12.34 ersetzt nur diese SOL-Entry-/Exit-Familie durch die im
Deep-Research-Bericht vorab definierte Range-Reversion. LTC bleibt gemäß der
bestandenen V12.33-Entscheidung ohne Einstieg; die übrigen acht Coin-Routen
bleiben unverändert.

Nur vollständig geschlossene Kerzen entscheiden:

1. Range-Zustand auf 4h: ADX14 höchstens 18, Abstand EMA50 zu EMA200 relativ
   zum Schluss höchstens 3 Prozent und 30-Tage-Rendite zwischen −20 und
   +20 Prozent.
2. Schock auf 15m: Schluss mindestens 2,50 ATR14 unter EMA96. Die Schockkerze
   selbst darf nicht gekauft werden.
3. Einstieg innerhalb der nächsten acht geschlossenen 15m-Kerzen nur beim
   Kreuzen zurück über `EMA96 − 1,50 × ATR14` und bei positivem Volumen.
4. SOL erhält genau einen 80-USDT-Block und kein Pyramiding.
5. Exit beim Schluss an/über EMA96, nach spätestens zwölf Stunden oder wenn
   4h-ADX mindestens 24 erreicht, während SOL weiter unter EMA96 liegt.
6. Der globale Hard-Stop von −5,5 Prozent, ROI, Gebühren und Protections
   bleiben unverändert.

## Vor dem ersten Ergebnis bindende Hürden

1. SOL allein über drei Jahre: mindestens +15 USDT, mindestens zwölf Trades,
   Profit-Faktor über 1,20 und geschlossener Drawdown höchstens 12,20 Prozent.
2. SOL im jüngsten Jahr: mindestens drei Trades und nicht negativ.
3. SOL bei 0,3 Prozent Gebühr je Seite: positiv und Profit-Faktor über 1,10.
4. Im gemeinsamen Dreijahreslauf muss SOL positiv beitragen. Das gemeinsame
   Wallet muss V12.33 beim Gewinn (+421,9152 USDT) übertreffen, einen
   Profit-Faktor von mindestens 2,4530 und einen geschlossenen Drawdown von
   höchstens 12,1794 Prozent halten.
5. Jedes unter V12.33 positive Paar bleibt positiv. Es bleiben höchstens drei
   80-USDT-Plätze belegt, und jeder Platz wird erst nach dem endgültigen Exit
   des Trades frei.
6. Datei-, Kausalitäts-, Kapital-, Dry-run- und Sicherheitstests bleiben grün.

Scheitert eine Hürde, wird V12.34 verworfen und V12.33 bleibt der Kandidat.
Schwellen werden nach dem ersten Ergebnis nicht verändert. Historische
Resultate sind keine Echtgeldfreigabe oder Gewinngarantie.

## Ergebnis

Die primäre Einzelhürde scheiterte bereits im exakten Dreijahreslauf:

- **−4,055 USDT** statt mindestens +15 USDT,
- 25 Trades,
- Profit-Faktor **0,44** statt über 1,20,
- Trefferquote 44 Prozent,
- geschlossener Drawdown 2,07 Prozent,
- 79,944 USDT durchschnittlicher Einsatz und kein Zusatzblock.

20 EMA96-Exits erzielten zusammen nur +1,958 USDT; fünf Zwölf-Stunden-Exits
verloren zusammen −6,013 USDT. Kosten- und Shared-Gates wurden nach dem
vorregistrierten Ablauf nicht mehr ausgeführt. Die Schwellen bleiben
unverändert dokumentiert und werden auf diesem Fenster nicht nachgestimmt.
Entscheidung: `REJECT_DO_NOT_PROMOTE`. V12.33 bleibt der Elternkandidat für
eine separat registrierte SOL-Reservefamilie.
