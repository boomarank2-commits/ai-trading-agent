# V12.32 – feste LTC-Route im aktiven V12.31-Portfolio prüfen

Stand: 24.08.2026

Experiment: `V12.32-DOGE-BCH-LTC-FIXED-ROUTE-COMBINATION`

Elternstand: `V12.31-DOGE-BCH-FIXED-ROUTE-COMBINATION`

Strategie: `CompressionBreakout250`, Version `V12.32`

Vor dem ersten V12.32-Finanzlauf registrierter SHA-256:

`8c66a0cdca2cf240b9b554fd0c02f55ad33c6bb88549727d091cea7a1b3083e2`

Status: **VERWORFEN – NICHT IN DEN PAPERBOT ÜBERNEHMEN.**

## Warum dieser Versuch zulässig und nicht bloßes Nachoptimieren ist

V12.23 testete eine feste LTC-EMA-Route bereits exakt. Sie machte LTC allein
von −45,01 auf +29,245 USDT profitabel, bestand den Einjahres- und
Kostenstresstest, verschlechterte aber das damalige V12.22-Portfolio durch
Slotverdrängung. Deshalb wurde sie nicht übernommen und danach nicht
nachgestimmt.

V12.31 hat durch die separat geprüften DOGE- und BCH-Routen eine andere
Signalchronologie, einen höheren Gewinn und einen niedrigeren Drawdown als
V12.22. Noch nie geprüft wurde, ob die **unveränderte** V12.23-LTC-Route in
diesem neuen Portfolio einen Zusatznutzen liefert. V12.32 kombiniert daher nur
bereits feststehende Komponenten. Kein betrachteter LTC-, DOGE- oder
BCH-Schwellenwert wird verändert.

## Eine feste Änderung

V12.31 bleibt byteinhaltlich in seinen Entscheidungen erhalten. Nur für
`LTC/USDT` ersetzt die unveränderte V12.23-Route den Broad-Core-Donchian-Pfad:

1. EMA30 kreuzt auf 4h von unten über EMA80.
2. Der 4h-Schluss liegt über EMA200.
3. EMA200 liegt über seinem Stand vor zwölf 4h-Kerzen.
4. 4h-ADX ist mindestens 12.
5. Exit, sobald EMA30 unter EMA80 oder der Schluss unter EMA80 liegt.
6. LTC bleibt bei genau einem 80-USDT-Block und erhält keine Verlustnachkäufe.

Unverändert bleiben 250 USDT Gesamtwallet, höchstens drei offene Positionen,
80 USDT pro Block, maximal 240 USDT Exposition, Spot long-only, 1x, 5,5 Prozent
Hard-Stop, Protections, Gebühren, Dry-run und die übrigen neun Coin-Routen.

## Vor dem ersten Ergebnis bindende Hürden

1. LTC reproduziert V12.23 über drei Jahre innerhalb 0,01 USDT: mindestens
   +29,24 USDT, genau 21 Trades, PF mindestens 1,50, Drawdown höchstens
   10,50 Prozent, durchschnittlicher Einsatz höchstens 80,01 USDT und keine
   Zusatzblöcke.
2. LTC bleibt im jüngsten Jahr mit mindestens drei Trades und mindestens
   +8,00 USDT positiv.
3. LTC bleibt bei 0,3 Prozent Gebühr je Seite mit mindestens +25 USDT und PF
   über 1,40 positiv.
4. DOGE reproduziert V12.31 innerhalb 0,01 USDT und mit 25 Trades; BCH
   reproduziert V12.31 innerhalb 0,01 USDT und mit 20 Trades.
5. Das gemeinsame 250-USDT-Wallet muss V12.31 übertreffen: Gewinn über
   +419,8571 USDT, PF mindestens 2,4358 und geschlossener Drawdown höchstens
   12,5447 Prozent.
6. LTC trägt im gemeinsamen Lauf positiv bei und jedes unter V12.31 positive
   Paar bleibt positiv.
7. Strategie-, Datei-, Kausalitäts-, Kapital-, Dry-run- und Sicherheitstests
   bleiben grün.

Nach dem ersten Finanzlauf werden Quelle, Hash und Hürden nicht verändert.
Scheitert eine Hürde, wird V12.32 dokumentiert verworfen, die aktive
V12.31-Quelle bytegenau wiederhergestellt und der laufende Laptop-Bot nicht
angetastet. Historische Resultate sind keine Echtgeldfreigabe oder
Gewinngarantie.

## Ergebnis

Die LTC-Einzelhürden und beide Erhaltungsprüfungen bestanden exakt:

- LTC drei Jahre: **+29,245 USDT**, 21 Trades, PF 1,62, geschlossener
  Drawdown 9,91 Prozent, durchschnittlicher Einsatz 79,94 USDT und kein
  Zusatzblock.
- LTC jüngstes Jahr: **+8,250 USDT**, 3 Trades und 1,32 Prozent Drawdown.
- LTC Kostenstress mit 0,3 Prozent Gebühr je Seite: **+26,098 USDT**, 21
  Trades, PF 1,53 und 10,32 Prozent Drawdown.
- DOGE reproduzierte V12.31 exakt mit **+112,552 USDT** und 25 Trades.
- BCH reproduzierte V12.31 exakt mit **+25,398 USDT** und 20 Trades.

Der bindende gemeinsame Systemtest scheiterte jedoch deutlich:

| Gemeinsames 250-USDT-Wallet | V12.31 | V12.32 | Änderung |
| --- | ---: | ---: | ---: |
| Endkapital | 669,857 | 619,822 | −50,035 USDT |
| Gewinn | +419,857 | +369,822 | −50,035 USDT |
| Trades | 155 | 157 | +2 |
| Profit-Faktor | 2,4358 | 2,1976 | −0,2382 |
| geschlossener Drawdown | 12,5447 % | 13,2813 % | +0,7366 Punkte |
| LTC-Beitrag | −18,831 | −9,408 USDT | +9,423 USDT |

LTC selbst blieb im gemeinsamen Lauf trotz der isoliert profitablen Route
negativ. Die veränderte Slotchronologie reduzierte außerdem vor allem DOGE von
+120,687 auf +77,851 USDT und BCH von +22,154 auf +5,324 USDT. Der kleine
LTC-Fortschritt kostete dadurch insgesamt rund 50 USDT.

Der Dateiaudit bestätigte den registrierten Hash, exakt 40 Candle-Ladevorgänge
für zehn Paare und vier Zeitrahmen sowie null Kindprozesse. Die Ablehnung ist
daher finanziell und nicht technisch begründet.

Entscheidung: `REJECT_DO_NOT_PROMOTE`. Die aktive V12.31-Strategie wurde
bytegenau auf Hash
`e13a324560a4941350edd30b53e69ed6286eeb77f2b31673a859c3144e8965d5`
zurückgestellt. Die LTC-Route und benachbarte Schwellen dürfen auf diesem
Fenster nicht erneut nachoptimiert werden. Der laufende Laptop-Dry-run blieb
die ganze Zeit auf V12.31.
