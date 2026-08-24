# V12.33 – LTC ohne Einstieg im V12.31-Portfolio

Stand: 24.08.2026

Experiment: `V12.33-LTC-NO-TRADE-COUNTERFACTUAL`

Elternstand: `V12.31-DOGE-BCH-FIXED-ROUTE-COMBINATION`

Strategie: `CompressionBreakout250`, Version `V12.33`

Vor dem ersten V12.33-Finanzlauf registrierter SHA-256:

`58d59413ef41b798c75c41bab0f98e377316ad3b289b6ba874876e841cdfb263`

Status: **BESTANDEN – NEUER PAPER-KANDIDAT, KEINE ECHTGELDFREIGABE.**

## Warum dieser Versuch neu und zulässig ist

Im exakten gemeinsamen V12.31-Dreijahreslauf verlor LTC 18,831 USDT bei
sieben Trades und einem Profit-Faktor von null. Die separat profitable
V12.23-LTC-EMA-Route wurde als V12.32 erneut unverändert kombiniert, blieb im
gemeinsamen Portfolio aber negativ und verdrängte stärkere DOGE- und
BCH-Chronologie. Sie wurde deshalb verbindlich verworfen.

Noch nicht simuliert wurde der kausale Gegenversuch, LTC vollständig aus der
Slotvergabe zu nehmen. Dieser Test stimmt keine betrachtete Schwelle nach.

## Genau eine Änderung

`LTC/USDT` setzt auf jeder geschlossenen 15-Minuten-Kerze `enter_long = 0`.
LTC eröffnet damit keinen Block und belegt keinen der drei globalen Plätze.
Alle anderen neun Routen und sämtliche Exits bleiben byteinhaltlich in ihren
Entscheidungen V12.31. Unverändert bleiben außerdem:

- ein gemeinsames Wallet mit 250 USDT,
- höchstens drei gleichzeitig offene Positionen,
- 80 USDT pro Block und höchstens 240 USDT Exposition,
- ein Platz wird erst nach vollständig geschlossenem Trade wieder frei,
- Spot, long-only, 1x, 5,5 Prozent Hard-Stop, Gebühren und Protections,
- Dry-run sowie alle Sicherheits- und Paritätsverträge.

## Vor dem ersten Ergebnis bindende Hürden

1. Der LTC-Einzeltest erzeugt über drei Jahre exakt null Trades und null
   Gewinn oder Verlust.
2. Das gemeinsame 250-USDT-Wallet übertrifft V12.31 beim Gewinn
   (+419,8571 USDT) und verschlechtert weder Profit-Faktor (mindestens 2,4358)
   noch geschlossenen Drawdown (höchstens 12,5447 Prozent).
3. Jedes unter V12.31 positive Paar bleibt im gemeinsamen Lauf positiv.
4. Es gibt höchstens drei gleichzeitig belegte 80-USDT-Plätze; jeder bleibt
   vom Einstieg bis zum endgültigen Exit belegt. Kein Verlustnachkauf,
   Futures-, Margin-, Short- oder Echtgeldpfad wird hinzugefügt.
5. Strategie-, Datei-, Kausalitäts-, Kapital-, Dry-run- und Sicherheitstests
   bleiben grün.

Scheitert eine Hürde, wird V12.33 verworfen und die aktive V12.31-Quelle
bytegenau beibehalten. Besteht der Versuch, ist V12.33 nur der neue
Paper-Kandidat; er ist keine Echtgeldfreigabe oder Gewinngarantie.

## Ergebnis

Der exakte gemeinsame Dreijahreslauf bestand alle vorregistrierten Hürden:

| Kennzahl | V12.31 | V12.33 | Änderung |
| --- | ---: | ---: | ---: |
| Gewinn | +419,8571 USDT | **+421,9152 USDT** | +2,0581 USDT |
| Endkapital | 669,8571 USDT | **671,9152 USDT** | +2,0581 USDT |
| Trades | 155 | **154** | −1 |
| Profit-Faktor | 2,4358 | **2,4530** | +0,0172 |
| geschlossener Drawdown | 12,5447 % | **12,1794 %** | −0,3653 Punkte |
| LTC-Beitrag | −18,8310 USDT | **0,0000 USDT** | +18,8310 USDT |

Alle zuvor positiven Coins blieben positiv. Die Verbesserung ist klein, weil
die freigewordene Slotchronologie andere Paarbeiträge verändert; deshalb wird
nicht einfach der frühere LTC-Verlust zum Gesamtgewinn addiert. Der Dateiaudit
verwendete den registrierten Strategiehash und die lokalen Kerzen für alle
zehn Paare. Entscheidung: `KEEP_AS_PAPER_CANDIDATE_NOT_REAL_MONEY`.
