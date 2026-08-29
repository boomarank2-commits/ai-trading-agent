# V12.33 Kapital- und Zeiteffizienz – frischer Zehnerlauf 2026-08-29

## Zweck

Diese Akte wertet den vollständig abgeschlossenen serverseitigen Zehnerlauf
`20260829T063826Z-635287bc` aus. Jeder Coin wurde getrennt über 1095 Tage mit
eigenen 250 USDT getestet. Das ist **nicht** der gemeinsame Drei-Slot-Lauf.

Die aktive Strategy blieb bytegenau V12.33 mit SHA-256
`58d59413ef41b798c75c41bab0f98e377316ad3b289b6ba874876e841cdfb263`.
Es wurde kein Entry, Exit, Stop oder Pair-Parameter nach dem Ergebnis geändert.

## Ergebnis und neue Effizienzdiagnose

| Pair | P/L USDT | Trades | USDT/Trade | USDT/100 Entry | USDT/100 Kapitaltag | Kapitalzeit | Ohne Position |
|---|---:|---:|---:|---:|---:|---:|---:|
| BTC/USDT | +163,27 | 15 | 10,89 | 7,88 | 0,375 | 15,92 % | 80,13 % |
| ETH/USDT | +134,02 | 44 | 3,05 | 2,21 | 0,361 | 13,56 % | 84,36 % |
| SOL/USDT | +7,32 | 24 | 0,30 | 0,38 | 0,048 | 5,58 % | 82,55 % |
| XRP/USDT | +92,73 | 19 | 4,88 | 6,10 | 2,187 | 1,55 % | 95,16 % |
| BNB/USDT | +17,82 | 18 | 0,99 | 1,24 | 0,137 | 4,75 % | 85,12 % |
| DOGE/USDT | +106,48 | 25 | 4,26 | 5,33 | 1,219 | 3,19 % | 90,02 % |
| LINK/USDT | +56,59 | 30 | 1,89 | 1,73 | 0,329 | 6,28 % | 91,69 % |
| TRX/USDT | +15,23 | 5 | 3,05 | 3,17 | 0,186 | 3,00 % | 93,19 % |
| LTC/USDT | 0,00 | 0 | 0,00 | 0,00 | 0,000 | 0,00 % | 100,00 % |
| BCH/USDT | +17,72 | 20 | 0,89 | 1,11 | 0,169 | 3,83 % | 87,98 % |

Die zehn getrennten Wallets erzielten zusammen rechnerisch +611,18 USDT. Diese
Summe darf nicht als Ergebnis eines 250-USDT-Wallets ausgegeben werden.

## Diagnose

- SOL verfehlt das Ziel von 1 USDT je 100 USDT Entry-Kapital deutlich. Seine
  aktive Route ist zwar knapp positiv, bindet Kapital aber wirtschaftlich
  unproduktiv.
- BNB und BCH liegen nur knapp über 1 USDT je 100 USDT Entry-Kapital. Kleine
  Ausführungsabweichungen oder höhere Kosten können diesen Vorsprung aufzehren.
- BTC, ETH, XRP und DOGE haben klar positive Einsatz-Effizienz. LINK und TRX
  sind positiv, TRX ist mit nur fünf Trades jedoch sehr dünn belegt.
- LTC ist keine verlorene oder defekte Backtest-Route. V12.33 schaltet LTC nach
  negativer Shared-Wallet-Evidenz bewusst pair-lokal auf NO_TRADE.
- Viel Leerlauf in einem Einzeltest ist nicht automatisch falsch: Im Paperbot
  sollen zehn unabhängige Signalquellen denselben Leerlauf gemeinsam füllen.
  Ob das gelingt, beweist nur der chronologische gemeinsame Drei-Slot-Test.

## Gemeinsame Systemreferenz

Der letzte unveränderte exakte V12.33-PORTFOLIO-Lauf bleibt die gültige
Systemreferenz: 250,00 → 671,92 USDT, also +421,92 USDT, 154 abgeschlossene
Trades, Profit Factor 2,453 und 12,18 % maximaler geschlossener Drawdown. Die
mittlere historische Leistung beträgt damit rund 0,385 USDT je Kalendertag und
2,74 USDT je abgeschlossenem Trade. Jeder offene Trade belegt seinen 80-USDT-
Slot bis zum tatsächlichen Exit; es gibt keine vorzeitige rechnerische
Freigabe.

## Entscheidung und nächster zulässiger Schritt

V12.33 bleibt unverändert der aktive Paper-/Dry-Run-Kandidat, nicht Echtgeld.
Die bereits angesehenen Schwellen und Familien werden nicht nachträglich auf
demselben Dreijahresfenster nachgestimmt. Für SOL, BNB, BCH oder LTC ist nur
eine materiell neue, vorher registrierte Pair-Hypothese oder neue
Paper-Forward-Evidenz zulässig. Ein Kandidat muss anschließend Einzeltest,
aktuelles/recentes Fenster, Kostenstress und den gemeinsamen Drei-Slot-Test
bestehen. Mehr Trades allein sind kein Akzeptanzgrund.
