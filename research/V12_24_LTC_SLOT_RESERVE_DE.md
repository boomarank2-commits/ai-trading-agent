# V12.24 – LTC darf nur aus einem leeren Portfolio starten

Stand: 24.08.2026

Experiment: `V12.24-LTC-EMPTY-PORTFOLIO-ENTRY`

Elternstand: `V12.23-LTC-EMA30-80-MACRO200` (verworfen)

Strategie: `CompressionBreakout250`, Version `V12.24`

Vor dem ersten Finanzlauf registrierter SHA-256:

`b7a479b70b5dd0b82531ec5f24dcffd8493fdfbb77af1ce902e3d9a8fe08bb0d`

Status: **VERWORFEN – NICHT IN DEN PAPERBOT ÜBERNEHMEN.**

## Ursache und isolierte Hypothese

V12.23 machte LTC im Einzeltest profitabel, fiel im gemeinsamen System aber
von V12.22 +280,775 auf +232,037 USDT. LTC selbst trug dort +23,309 USDT bei;
seine langen Positionen belegten jedoch einen der nur drei 80-USDT-Slots und
verdrängten deutlich profitablere BTC-, XRP- und ETH-Signale.

V12.24 verändert weder den LTC-Entry noch dessen Exit. Es gilt genau eine neue
Portfolio-Regel:

> Ein neuer LTC-Trade erhält nur Einsatz, wenn zu diesem Zeitpunkt kein anderer
> Trade offen ist.

Nach dem LTC-Entry dürfen zwei spätere Trades anderer Paare normal hinzukommen.
Die Regel wird in `custom_stake_amount()` ausgeführt; dadurch verwenden der
historische Backtest und der Dry-run dieselbe Entscheidung. Zusatzblöcke für
LTC bleiben verboten.

Unverändert bleiben alle Indikatorparameter, Signale, Exits, Stopps,
Protections, Gebühren, zehn Paare, 250 USDT Gesamtwallet, 80 USDT je Block,
maximal drei Positionen, Spot, Long-only und 1x.

## Vor dem Test festgelegte Hürden

1. Der unabhängige LTC-Dreijahreslauf muss V12.23 bis auf 0,01 USDT
   reproduzieren, positiv bleiben und weiterhin 21 Trades enthalten.
2. Das gemeinsame Portfolio muss V12.22 mit +280,7752 USDT und Profit-Faktor
   2,0230 übertreffen.
3. Der gemeinsame geschlossene Drawdown darf 16,07 Prozent nicht überschreiten.
4. LTC muss im gemeinsamen Portfolio positiv bleiben.
5. Kein unter V12.22 positives Paar darf negativ werden.
6. Kapital-, Dry-run-, Kausalitäts-, Strategie- und Governance-Tests bleiben
   grün.

Scheitert eine Hürde, wird V12.24 verworfen und der aktive Quelltext exakt auf
V12.22 zurückgesetzt. Das Nutzerziel 250 → 500 USDT pro Einzelcoin ist keine
Erlaubnis, eine bekannte Historie nachträglich auf eine Zielzahl zu optimieren.

## Exakte Ergebnisse und Entscheidung

Der LTC-Einzeltest reproduzierte V12.23 exakt: +29,245 USDT, 21 Trades,
Profit-Faktor 1,62 und 9,91 Prozent geschlossener Drawdown. Damit war bestätigt,
dass die neue Portfolio-Regel die isolierte Route nicht heimlich verändert.

Die gemeinsame Hürde scheiterte:

| Gemeinsames 250-USDT-Wallet | V12.22 | V12.24 | Änderung |
| --- | ---: | ---: | ---: |
| Gewinn | +280,775 USDT | +223,457 USDT | −57,318 USDT |
| Trades | 136 | 150 | +14 |
| Profit-Faktor | 2,023 | 1,73 | −0,293 |
| geschlossener Drawdown | 16,07 % | 18,47 % | +2,40 Punkte |
| LTC-Beitrag | −17,441 USDT | −27,582 USDT | −10,141 USDT |

Die Regel ließ nur neun LTC-Trades in das gemeinsame Portfolio. Diese zeitlich
ausgewählte Teilmenge war schlechter als sowohl die unabhängige Route als auch
der V12.22-LTC-Beitrag. Zusätzlich blieben die bekannten Slotverschiebungen bei
anderen Paaren bestehen. Entscheidung: `REJECT_DO_NOT_PROMOTE`. Der aktive
Strategiequelltext wird auf den exakten V12.22-Hash zurückgesetzt.
