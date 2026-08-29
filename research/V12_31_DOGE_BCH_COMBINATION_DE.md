# V12.31 – feste DOGE-/BCH-Routen einmalig kombinieren

Stand: 24.08.2026

Experiment: `V12.31-DOGE-BCH-FIXED-ROUTE-COMBINATION`

Elternstand: `V12.30-DOGE-SUPERTREND20X3-MACRO100`

Strategie: `CompressionBreakout250`, Version `V12.31`

Vor dem ersten Finanzlauf registrierter SHA-256:

`e13a324560a4941350edd30b53e69ed6286eeb77f2b31673a859c3144e8965d5`

Status: **ÜBERNOMMEN ALS AKTIVER PAPER-/DRY-RUN-KANDIDAT.**

## Warum dieser Versuch nicht bloßes Nachoptimieren ist

V12.26 und V12.30 wurden bereits getrennt, mit unveränderlichen Quellen und
vorab festgelegten Hürden exakt getestet. V12.26 machte BCH im Einzeltest
profitabel und erhöhte den damaligen gemeinsamen Gewinn, scheiterte aber um
0,4017 Drawdown-Prozentpunkte. V12.30 änderte ausschließlich DOGE und senkte
den gemeinsamen Drawdown von 16,07 auf 13,3897 Prozent.

V12.31 verändert keine nach Ansicht dieser Ergebnisse ausgewählte Schwelle.
Es kombiniert einmalig:

- die unveränderte V12.30-DOGE-Route Supertrend(20, 3) über steigender EMA100,
- die unveränderte V12.26-BCH-Route EMA30-Kreuz über EMA80, Kurs über
  steigender EMA100 und ADX mindestens 24,
- alle übrigen V12.30-Regeln einschließlich SOL-ADX21,
- genau ein 80-USDT-Block für DOGE und BCH,
- gemeinsames 250-USDT-Wallet, höchstens drei Blöcke und 240 USDT Exposition,
- Spot long-only, 1x, Dry-run und dieselben Schutzregeln.

Die BCH-EMA-Route verwendet ihren eigenen EMA80-Exit und wird deshalb nicht
durch den Donchian-spezifischen Failed-Breakout-Exit verändert. Das entspricht
der zuvor exakt geprüften Routenfamilie.

## Vor dem Lauf bindende Hürden

1. BCH drei Jahre: mindestens +25 USDT, 20 Trades, PF mindestens 1,45,
   geschlossener Drawdown höchstens 12 Prozent und kein Zusatzblock.
2. BCH jüngstes Jahr: positiv mit mindestens drei Trades.
3. BCH bei 0,3 Prozent Gebühr je Seite: weiterhin positiv.
4. DOGE muss V12.30 innerhalb 0,01 USDT und mit unveränderter Tradezahl
   reproduzieren.
5. Gemeinsames Wallet: Gewinn über +373,6057 USDT, PF mindestens 2,3576,
   geschlossener Drawdown höchstens 13,3897 Prozent und positiver BCH-Beitrag.
6. Jedes in V12.30 positive gemeinsame Paar bleibt positiv; alle Kapital-,
   Dry-run-, Kausalitäts- und Sicherheitsverträge bleiben grün.

Nach dem ersten Finanzlauf bleiben Quellhash und Hürden unverändert. Scheitert
eine Hürde, wird V12.31 verworfen und die bytegenaue aktive V12.30-Quelle
wiederhergestellt. Das Ziel 250 auf 500 USDT ist eine Forschungsrichtung und
keine Hürde, die durch nachträgliches Kurvenanpassen erzwungen werden darf.

## Ergebnis

Alle vorregistrierten Hürden wurden ohne Änderung an Quelle oder Schwellen
bestanden:

- BCH drei Jahre: **+25,398 USDT**, 20 Trades, PF 1,54, geschlossener
  Drawdown 11,21 Prozent, durchschnittlicher Einsatz 79,788 USDT und kein
  Zusatzblock.
- BCH jüngstes Jahr: **+3,012 USDT**, 8 Trades und PF 1,16.
- BCH bei 0,3 Prozent Gebühr je Seite: **+22,426 USDT**, 20 Trades, PF 1,45
  und geschlossener Drawdown 11,75 Prozent.
- DOGE-Parität: **+112,552 USDT**, 25 Trades, PF 2,9046 und geschlossener
  Drawdown 6,4536 Prozent; damit innerhalb 0,001 USDT zur V12.30-Referenz.
- Gemeinsames Zehn-Coin-Wallet: Start 250, Ende **669,857 USDT**, Gewinn
  **+419,8571 USDT**, 155 Trades, PF **2,4358** und geschlossener Drawdown
  **12,5447 Prozent**.

Gemeinsame Paarbeiträge: DOGE +120,687; XRP +108,388; LINK +90,264; BTC
+80,811; BNB +34,756; BCH +22,154; TRX +12,352; ETH +9,186; LTC −18,831;
SOL −39,910 USDT. Alle in V12.30 positiven Paare blieben positiv.

Gegenüber V12.30 steigt der gemeinsame Gewinn um **+46,2513 USDT**, die
Tradezahl von 145 auf 155 und der Profit-Faktor von 2,3576 auf 2,4358. Der
geschlossene Drawdown sinkt von 13,3897 auf 12,5447 Prozent. Der Dateiaudit
bestätigte die registrierte Strategiequelle und die vorgesehenen lokalen
1m-/15m-/1h-/4h-Binance-Dateien.

Entscheidung: `KEEP_AS_ACTIVE_PAPER_CHALLENGER_NOT_REAL_MONEY`. V12.31 ist
damit die gemeinsame Quelle für Paperbot und künftige Backtests. SOL und LTC
bleiben ungelöst. Weder der historische Gewinn noch das Ziel 250 auf 500 USDT
ist eine Garantie für zukünftige Ergebnisse oder eine Echtgeldfreigabe.
