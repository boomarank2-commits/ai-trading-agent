# V12.27 – breitere TRX-Donchian-Route aus einem stabilen Plateau

Stand: 24.08.2026

Experiment: `V12.27-TRX-DONCHIAN40-MACRO200`

Elternstand: `V12.22-SOL-ADX21`

Strategie: `CompressionBreakout250`, Version `V12.27`

Vor dem ersten Finanzlauf registrierter SHA-256:

`a47396306f6b15c1cbc4f6e1c7339d8e494092e101fb858f2258c7c67bbd5544`

Status: **VERWORFEN – ISOLIERTE RISIKOHÜRDE VERFEHLT.**

## Diagnose und Auswahl

TRX war unter V12.22 zwar positiv, handelte in drei Jahren aber nur fünfmal
und erzielte unabhängig +15,23 USDT; im gemeinsamen Wallet waren es drei Trades
und +12,35 USDT. Das Kapital wurde damit kaum genutzt.

Im festen kausalen Screen bestanden 81 von 186 Varianten beide Auswahljahre,
das getrennte dritte Jahr und höhere Gebühren. Das spricht für ein
Familienplateau statt eines einzelnen Parameterspitzenwerts. Vor dem exakten
Lauf wurde der konservative 40/40-Punkt festgelegt:

- 4h-Schluss kreuzt über das vorherige 40-Kerzen-Hoch;
- Kurs über steigendem EMA200;
- 30-Tage-Momentum positiv;
- Exit unter dem vorherigen 40-Kerzen-Tief;
- unveränderter 5,5-Prozent-Hard-Stop.

Die Jahresscheiben ergaben +22,013, +12,497 und +15,037 USDT bei zusammen 28
Trades. Der 0,3-Prozent-Kostenstress über den Gesamtzeitraum ergab +75,240 USDT,
30 Trades, PF 2,69 und 8,07 Prozent Drawdown. Der aktivere 20/20-Punkt wurde
nicht gewählt, weil sein Screen-Drawdown mit 14,01 Prozent deutlich höher war.

## Vorab festgelegte Hürden

1. TRX 3y: mindestens 20 Trades, mindestens +40 USDT, PF über 1,3 und höchstens
   10 Prozent Drawdown.
2. Letztes Jahr: positiv und mindestens fünf Trades.
3. Kostenstress 0,3 Prozent je Seite: positiv und PF über 1,3.
4. Gemeinsames Wallet: mehr als V12.22 +280,7752 USDT, PF mindestens 2,0230,
   Drawdown höchstens 16,07 Prozent und kein bisher positives Paar wird negativ.
5. Alle Kapital-, Kausalitäts-, Dry-run-, Strategie- und Sicherheitstests grün.

Nur TRX-Entry und -Exit ändern sich. TRX behält die vorhandene Erlaubnis für
spätere neue Gewinnsignale; Verlust-Nachkäufe bleiben gesperrt. Alle anderen
Pair-Routen, 250 USDT, 80 USDT je Block, höchstens drei Positionen, Spot,
Long-only, 1x, Gebühren, Stops und Protections bleiben unverändert.

## Exaktes Ergebnis und Entscheidung

Der Dreijahreslauf erzielte +165,512 USDT, 32 Trades und Profit-Faktor 2,52.
Damit wurden Aktivitäts- und Gewinnziel deutlich bestanden. Der geschlossene
Drawdown betrug jedoch 15,79 Prozent statt der vorab erlaubten höchstens zehn
Prozent. Der Lauf stoppte deshalb vor Einjahres-, Kosten- und gemeinsamem Test.

Der durchschnittliche Einsatz lag bei 187,477 USDT. Die unverändert aus V12.20
übernommene TRX-Pyramiding-Freigabe machte aus der im Screen geprüften
Ein-Block-Route häufig zwei oder drei Blöcke. Vier `trailing_stop_loss`-Exits
verloren zusammen 47,038 USDT. Die Entry-/Exit-Route wird innerhalb V12.27 nicht
verändert. Entscheidung: `REJECT_DO_NOT_PROMOTE`.

Als getrennte V12.28 darf genau eine neue Allokationshypothese geprüft werden:
dieselbe Route ohne TRX-Zusatzblöcke. Die drei globalen 80-USDT-Slots für
unterschiedliche Paare bleiben dabei unverändert.
