# V12.28 – TRX40-Route ohne pair-lokale Zusatzblöcke

Stand: 24.08.2026

Experiment: `V12.28-TRX40-SINGLE-BLOCK`

Elternstand: `V12.27-TRX-DONCHIAN40-MACRO200` (verworfen)

Strategie: `CompressionBreakout250`, Version `V12.28`

Vor dem ersten Finanzlauf registrierter SHA-256:

`50b940c5d690fd06cdb7224ec4a3cbb8d05784c8c03bd21fa434cf16130c5aea`

Status: **VERWORFEN – GEMEINSAMES WALLET-GATE NICHT BESTANDEN.**

V12.27 bewies hohe TRX-Aktivität und positiven Erwartungswert, scheiterte aber
mit 15,79 Prozent am isolierten Zehn-Prozent-Drawdown-Gate. Der durchschnittliche
Einsatz von 187,477 USDT zeigte, dass die alte, für die sparse V12.20-Route
freigegebene TRX-Pyramiding-Regel den Ein-Block-Screen nicht abbildete.

V12.28 ändert genau eine Allokationsregel: `TRX/USDT` wird aus
`PYRAMIDING_PAIRS` entfernt. Die V12.27-Entry-/Exit-Route bleibt byteinhaltlich
gleich. BTC, ETH und LINK dürfen unverändert später im Gewinn aufstocken. Das
globale Wallet behält 250 USDT, drei Slots zu je höchstens 80 USDT und 240 USDT
Gesamtexposure; verschiedene Paare können weiterhin alle drei Slots nutzen.

Vorab bindende Hürden:

1. TRX 3y: mindestens 20 Trades, mindestens +40 USDT, PF über 1,3, höchstens
   10 Prozent Drawdown, durchschnittlich höchstens 80,01 USDT Einsatz und null
   Zusatzblöcke.
2. Letztes Jahr: positiv bei mindestens fünf Trades.
3. 0,3-Prozent-Kostenstress: positiv und PF über 1,3.
4. Gemeinsames Wallet: Gewinn über +280,7752 USDT, PF mindestens 2,0230,
   Drawdown höchstens 16,07 Prozent, kein positives V12.22-Paar wird negativ.
5. Alle Strategie-, Kapital-, Kausalitäts-, Dry-run- und Sicherheitstests grün.

## Exakte Ergebnisse

- TRX, drei Jahre, 0,2 Prozent Gebühr je Order: **+98,365 USDT**, 30
  Trades, PF 3,34, geschlossener Drawdown 5,71 Prozent, durchschnittlicher
  Einsatz 79,99 USDT, keine Zusatzblöcke.
- TRX, jüngstes Jahr: **+15,231 USDT**, 7 Trades, geschlossener Drawdown
  1,37 Prozent.
- TRX, drei Jahre, 0,3 Prozent Gebühr je Order: **+93,682 USDT**, 30
  Trades, geschlossener Drawdown 6,08 Prozent.
- Gemeinsames Zehn-Coin-Wallet: **+271,929 USDT**, 151 Trades, PF 2,02,
  geschlossener Drawdown 11,95 Prozent.

Damit bestanden die isolierten TRX-, Aktivitäts-, Einsatz-, Kurzzeit- und
Kostenhürden. Das bindende gemeinsame Wallet-Gate scheiterte jedoch: Der
Gewinn lag 8,846 USDT unter V12.22 (+280,7752 USDT), und der nicht gerundete
Profit-Faktor erreichte die V12.22-Untergrenze von 2,0230 nicht. Der niedrigere
Drawdown ändert diese vorab festgelegte Entscheidung nicht.

Entscheidung: `REJECT_DO_NOT_PROMOTE`. Die aktive Strategie wird exakt auf
V12.22 mit SHA-256
`f7aac4afe8204aa7ce28a4a2bbf1d3c579ff4f084effa8bbff1c78ad8e9d2caf`
zurückgestellt. Die TRX40-Schwellen werden auf diesem eingesehenen Zeitraum
nicht nachträglich angepasst.
