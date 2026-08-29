# Kausaler Screen V2 – SOL und LTC ohne Bot-Patch verworfen

Stand: 24.08.2026

Diese zwei Diagnosen wurden nach der V2-Korrektur der Segmentgrenzen mit
`research/causal_pair_route_screen.py` ausgeführt. Sie sind keine eigene
Strategieversion und änderten den Bot nicht. Offene Positionen wurden jeweils
am letzten zulässigen Schlusskurs des Jahressegments bewertet. Verwendet wurden
die lokal auditierten Binance-15m-Dateien vom 24.08.2026, 250 USDT Startwert,
ein 80-USDT-Block, 0,2 Prozent Gebühr je Seite und 0,3 Prozent Kostenstress.

## SOL

Von 186 festen Routen bestand genau eine die einfachen Positivitätsgates:

- RSI14 war zuvor unter 30 und kreuzte anschließend über 50,
- Kurs über EMA200 und EMA200 höher als zwölf Kerzen zuvor,
- Exit bei RSI über 70 oder Kurs unter EMA200.

Jahresergebnisse: +5,9615 / +3,7256 / +2,9984 USDT bei 13 / 20 / 18 Trades.
Kostenstress: +4,5082 USDT, PF 1,1132. Der gesamte modellierte Gewinn von rund
12,69 USDT liegt unter der vorab verwendeten wirtschaftlichen
Mindestverbesserung von 25 USDT. Deshalb wurde kein exakter Freqtrade-Kandidat
angelegt und keine SOL-Regel verändert.

## LTC

Auch hier bestand nur eine Route:

- RSI14 war zuvor unter 30 und kreuzte anschließend über 50,
- Kurs über EMA100 und EMA100 höher als zwölf Kerzen zuvor,
- Exit bei RSI über 70 oder Kurs unter EMA100.

Jahresergebnisse: +0,3444 / +5,3386 / +1,9782 USDT bei 8 / 7 / 3 Trades.
Kostenstress: +4,7687 USDT, PF 1,4115. Der gesamte modellierte Gewinn von rund
7,66 USDT ist wirtschaftlich zu klein und im ersten Jahr praktisch null.
Deshalb wurde kein exakter Freqtrade-Kandidat angelegt und keine LTC-Regel
verändert.

## Verbindliche Folgerung

Diese beiden RSI-Kombinationen dürfen auf demselben Drei-Jahres-Fenster nicht
erneut als neue Idee vorgeschlagen oder durch benachbarte RSI-/EMA-Schwellen
nachoptimiert werden. SOL und LTC bleiben in V12.31 ungelöst. Der nächste
zulässige Versuch benötigt entweder frische Forward-Daten oder eine sachlich
andere, vorab registrierte Routenfamilie mit eigenem Kausalitäts- und
Kostenstress.
