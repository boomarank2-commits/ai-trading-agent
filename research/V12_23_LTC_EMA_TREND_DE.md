# V12.23 – LTC-Donchian durch chronologisch geprüfte EMA-Trendroute ersetzen

Stand: 24.08.2026

Experiment: `V12.23-LTC-EMA30-80-MACRO200`

Elternstand: `V12.22-SOL-ADX21`

Strategie: `CompressionBreakout250`, Version `V12.23`

Vor dem ersten V12.23-Finanzlauf registrierter SHA-256:

`248fdac232c65d3c13b9946059a3932f5ed568d5656cbed0fed729f0d6ec10a0`

Status: **VERWORFEN – NICHT IN DEN PAPERBOT ÜBERNEHMEN.**

## Diagnose

V12.20 und V12.22 erzeugten für LTC im exakten Dreijahres-Einzeltest dieselben
18 Trades. Alle 18 endeten im Minus: −45,01 USDT, Profit-Faktor 0,00 und
18,01 Prozent geschlossener Drawdown. Trotzdem erreichten 13 Trades
zwischenzeitlich mindestens +2 Prozent, fünf mindestens +5 Prozent und drei
mehr als +10 Prozent. Ein kleiner weiterer Filter der vorhandenen Entries kann
das Grundproblem nicht lösen, weil jede Teilmenge dieser 18 abgeschlossenen
Trades ohne neue Exit-Logik weiterhin nur Verlierer enthält.

Ein enger LTC-Gewinnratchet wird bewusst nicht zusammen mit einer neuen Route
getestet. Entry und Exit gleichzeitig anhand desselben Ergebnisses nachzustimmen
würde die Ursache unklar machen und das Überanpassungsrisiko erhöhen.

## Vorgeschalteter kausaler Screen

`research/causal_pair_route_screen.py` prüfte 186 feste 4h-Varianten aus fünf
transparenten Familien:

- EMA-Trendwechsel;
- Supertrend;
- Macro-Donchian;
- RSI-Pullback im Aufwärtstrend;
- MACD-Trendwechsel.

Signale werden ausschließlich aus abgeschlossenen Kerzen gebildet und erst am
nächsten 4h-Open ausgeführt. Jahr 1 und 2 dienen zur Auswahl. Jahr 3 bleibt bis
zur Auswahl unangetastet. Jeder Screen verwendet einen 5,5-Prozent-Hard-Stop,
80 USDT Einsatz sowie 0,2 Prozent Gebühr je Orderseite; anschließend folgt
0,3-Prozent-Kostenstress.

Nur zwei von 186 Varianten bestanden alle Screen-Hürden. Beide waren
EMA30/EMA80-Crosses oberhalb eines steigenden EMA200. Vor dem exakten Lauf wird
die ADX-12-Variante festgelegt, weil sie in den beiden Auswahljahren mit
+7,27 und +19,68 USDT gleichmäßiger war als die ADX-18-Variante. Das dritte
Jahr war bei der Festlegung kein Auswahlkriterium und endete im Screen mit
+4,81 USDT.

## Eine falsifizierbare Änderung

Nur für `LTC/USDT` wird der bisherige Broad-Core-Donchian-Einstieg ersetzt:

1. EMA30 kreuzt auf 4h von unten über EMA80.
2. Der 4h-Schluss liegt über EMA200.
3. EMA200 liegt über seinem Stand vor zwölf 4h-Kerzen.
4. 4h-ADX ist mindestens 12.
5. Der Entry erfolgt erst nach der abgeschlossenen Signalkerze.
6. Exit, wenn EMA30 unter EMA80 liegt oder der 4h-Schluss EMA80 unterschreitet.

Der vorhandene 5,5-Prozent-Hard-Stop bleibt erhalten. LTC erhält weiterhin
keine Zusatzblöcke. V12.22-SOL, alle anderen acht Pair-Routen, sämtliche
Kapitalgrenzen, Protections, Gebührenannahmen und Dry-run-Regeln bleiben
unverändert.

## Vor dem Test festgelegte Entscheidungshürden

V12.23 darf nur als aktiver Paper-Challenger fortgesetzt werden, wenn alle
folgenden Bedingungen erfüllt sind:

1. Der exakte LTC-Dreijahreslauf handelt mindestens zwölfmal, wird positiv,
   erreicht Profit-Faktor über 1,0 und verbessert V12.22 um mindestens
   40 USDT.
2. Der geschlossene LTC-Drawdown bleibt unter 18,01 Prozent.
3. Der exakte letzte Einjahreslauf bleibt bei mindestens drei Trades positiv.
4. LTC bleibt bei 0,3 Prozent Gebühr je Orderseite im Dreijahreslauf positiv.
5. Der gemeinsame Zehn-Paare-Lauf übertrifft V12.22 mit +280,7752 USDT und
   Profit-Faktor 2,0230, ohne dessen 16,07 Prozent Drawdown zu überschreiten.
6. Kein zuvor positiver gemeinsamer Pair-Beitrag wird negativ.
7. Strategie-, Kausalitäts-, Kapital-, Dry-run- und Sicherheitsverträge bleiben
   grün.

Scheitert eine dieser Hürden, wird die Route im Trial Ledger verworfen und der
exakte V12.22-Stand wiederhergestellt. Parameter, Exit und Gewinnratchet werden
innerhalb von V12.23 nach dem ersten exakten Ergebnis nicht verändert.

## Exakte Ergebnisse nach der Vorregistrierung

Die LTC-Route bestand alle isolierten Hürden:

| LTC-Einzeltest | Ergebnis |
| --- | ---: |
| 3 Jahre, Gebühr 0,2 % je Seite | +29,245 USDT; 21 Trades; PF 1,62; DD 9,91 % |
| letztes Jahr, Gebühr 0,2 % je Seite | +8,250 USDT; 3 Trades; PF 3,51; DD 1,32 % |
| 3 Jahre, Kostenstress 0,3 % je Seite | +26,098 USDT; 21 Trades; PF 1,53; DD 10,32 % |

Gegenüber dem unabhängigen V12.22-LTC-Ergebnis von −45,01 USDT war das eine
Verbesserung um 74,255 USDT. Die maßgebliche gemeinsame Hürde scheiterte jedoch
klar:

| Gemeinsames 250-USDT-Wallet | V12.22 | V12.23 | Änderung |
| --- | ---: | ---: | ---: |
| Gewinn | +280,775 USDT | +232,037 USDT | −48,738 USDT |
| Trades | 136 | 154 | +18 |
| Profit-Faktor | 2,023 | 1,76 | −0,263 |
| geschlossener Drawdown | 16,07 % | 18,86 % | +2,79 Punkte |

Im gemeinsamen Lauf wurde LTC mit +23,309 USDT positiv. Seine längeren Trades
belegten aber knappe Slots und verdrängten bessere Signale. Besonders BTC fiel
von +96,295 auf +58,838 USDT, XRP von +70,517 auf +26,841 USDT und ETH von
+29,310 auf +12,230 USDT. SOL verschlechterte sich ebenfalls von −26,783 auf
−32,773 USDT. Der isolierte Erfolg war deshalb kein Portfoliofortschritt.

Entscheidung: `REJECT_DO_NOT_PROMOTE`. Die Schwellen und Exits dieser
registrierten Version werden nicht nachträglich geändert. Ein eventueller
Slot-Reservetest ist ein neues Experiment mit eigener Version und eigenem Hash.

## Langfristiges Ziel und Grenze

Das Nutzerziel bleibt 250 → mindestens 500 USDT je Coin über drei Jahre. Der
Screen prognostiziert für diese LTC-Route nur einen kleinen positiven Schritt,
nicht +250 USDT. Die Version wird trotzdem an den vorab festgelegten relativen
Gates gemessen: Ein ehrlicher kleiner Fortschritt ist verwertbar; ein auf genau
500 USDT hingetunter Rückblick wäre keine belastbare Paperbot-Regel.
