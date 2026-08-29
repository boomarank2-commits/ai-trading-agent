# V12.41 – BNB-Exit-Isolation (verworfen)

## Anlass und unveränderte Sicherheitsgrenzen

Die V12.31-Paaranalyse zeigte, dass BNB unter V12.33 in drei Jahren
+17,821 USDT erzielte. Elf frühe `failed_breakout`-Exits kosteten zusammen
−17,605 USDT, während vier langsame Trend-Exits +40,817 USDT beitrugen.
Ein vor dem exakten Ergebnis festgelegter älterer 15m-Screen deutete deshalb
darauf hin, dass nur BNB von einem Verzicht auf den generischen frühen Exit
profitieren könnte.

V12.41 änderte genau diese eine Entscheidung. Unverändert blieben Spot
long-only 1x, Dry-run, 250 USDT Testwallet, ein 80-USDT-Block für BNB,
höchstens drei Blöcke im gemeinsamen Bot, kein Verlustnachkauf, −5,5 Prozent
Hard-Stop, 50-Prozent-ROI, Profit-Floor, Signal-Exits und Protections.

## Vorregistrierte Hürden

Der erste exakte BNB-Lauf musste alle folgenden Hürden erfüllen:

- mehr als +25 USDT Nettogewinn;
- mindestens 15 Trades;
- Profit-Faktor mindestens 1,60;
- geschlossener Drawdown höchstens 8 Prozent.

Nur danach wären jüngstes Jahr, 0,3-Prozent-Gebührenstress und gemeinsames
Zehn-Paare-Wallet geöffnet worden.

## Exaktes Ergebnis

Der unveränderte Kandidat mit SHA-256
`4eb220a4b99a185250acefe4a9546c2c0e5424a6f1291e4a908f7f0065776535`
wurde am 28.08.2026 mit Freqtrade 2026.7, `--timeframe-detail 1m`, aktivierten
Protections und 0,2 Prozent Gebühr je Seite geprüft. Tatsächlicher Zeitraum:
29.08.2023 bis 28.08.2026.

- Start 250,000 USDT, Ende 273,248 USDT;
- **+23,248 USDT** beziehungsweise +9,30 Prozent;
- 12 Trades, sechs Gewinner und sechs Verlierer;
- Profit-Faktor 1,90;
- geschlossener Maximal-Drawdown 4,94 Prozent;
- sieben langsame Trend-Exits: +38,030 USDT;
- vier Stop-Loss-Exits: −18,752 USDT;
- ein Profit-Floor/Trailing-Exit: +3,971 USDT.

Damit bestanden Profit-Faktor und Drawdown, aber Gewinn und Tradezahl
scheiterten an den bindenden Hürden. Der jüngste Jahreslauf, Gebührenstress
und gemeinsame Portfoliolauf wurden nicht ausgeführt. Die aktive Strategie
wurde byte-identisch auf V12.33 zurückgestellt.

## Nicht erneut testen

Der betrachtete Kandidat „BNB-Donchian ohne generischen frühen
Failed-Breakout-Exit“ ist abgeschlossen und darf nicht durch nachträgliches
Verschieben der angesehenen Grenzen wiederholt werden. Ein neuer BNB-Versuch
braucht eine materiell andere, vorher registrierte Entry-/Exit-Familie oder
neue Forward-Evidenz.
