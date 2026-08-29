# V12.20 – selektives Gewinn-Pyramiding für zehn Paare

Stand: 24.08.2026

Aktive Paper-Strategie: `CompressionBreakout250`, Version `V12.20`

Experiment: `V12.20-SELECTIVE-PYRAMID-ELIGIBILITY`

Exakter SHA-256:

`8eb1ad98e3cf13ea05c9c7f6dfb7c4b50b425741d3e225116e3b29f80391a3fb`

Status: **BESSERER ZEHN-PAARE-PAPER-KANDIDAT – KEIN CHAMPION UND NICHT FÜR
ECHTGELD FREIGEGEBEN.**

## Warum V12.20 gebaut wurde

V12.19 löste das Laufzeit- und Persistenzproblem des Backtests, änderte aber
die Handelsentscheidungen von V12.18 nicht. Der anschließend vollständig
nachgeholte gemeinsame V12.19-Systemtest zeigte, dass unbeschränktes
Gewinn-Pyramiding über alle zehn Paare die knappen drei 80-USDT-Blöcke falsch
verteilte: 250 USDT wurden zwar öfter eingesetzt, schwache Zusatzblöcke
vergrößerten aber Verlust und Drawdown.

Die vollständige V12.18-Einzelmatrix zeigte positive zusätzliche
Entry-Erwartung bei BTC, ETH, LINK und TRX. Bei SOL, XRP, BNB, DOGE, LTC und BCH
waren spätere Blöcke dagegen insgesamt schädlich. Daraus wurde vor dem Test
genau eine Änderung abgeleitet:

- alle zehn Coins behalten ihre bisherigen ersten Entry-Signale;
- BTC, ETH, LINK und TRX dürfen bei einem späteren vollständigen Signal im
  Gewinn weiterhin einen zweiten oder dritten Block erhalten;
- SOL, XRP, BNB, DOGE, LTC und BCH erhalten pro offenem Trade keinen
  Zusatzblock;
- Stops, Exits, Protections, Gebühren, Entry-Schwellen, 250-USDT-Wallet,
  80-USDT-Block und 240-USDT-Gesamtgrenze bleiben unverändert.

Dies ist kein Verlust-Nachkauf. Selbst für die vier freigegebenen Paare bleibt
jeder Zusatzblock gesperrt, solange Gesamttrade oder neuer Einstieg nicht im
Gewinn liegen oder der Kurs nicht über allen früheren Fills liegt.

## Einzeltests auf denselben Drei-Jahres-Kerzen

Jeder Coin startete unabhängig mit 250 USDT. Die Tabelle dient der
Pair-Diagnose und ist keine gemeinsame 2.500-USDT-Kapitalkurve.

| Coin | V12.18 P/L | V12.20 P/L | V12.20 Trades | V12.20 PF | V12.20 DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| BTC | +166,63 | +166,63 | 14 | 9,78 | 2,70 % |
| ETH | +133,11 | +135,94 | 43 | 2,37 | 13,19 % |
| SOL | −22,04 | −2,03 | 25 | 0,97 | 15,68 % |
| XRP | +37,62 | +92,73 | 19 | 3,95 | 7,18 % |
| BNB | −36,56 | +17,82 | 18 | 1,66 | 5,87 % |
| DOGE | −1,46 | +56,67 | 25 | 1,84 | 8,09 % |
| LINK | +61,86 | +61,86 | 30 | 1,62 | 26,02 % |
| TRX | +15,23 | +15,23 | 5 | 2,53 | 3,63 % |
| LTC | −66,29 | −45,01 | 18 | 0,00 | 18,01 % |
| BCH | −59,61 | −24,25 | 18 | 0,46 | 12,52 % |
| **Summe der Diagnosen** | **+228,49** | **+475,59** | **215** | – | – |

Die Änderung verbesserte die unabhängige Diagnosesumme um 247,10 USDT. Sie
löste jedoch die schwachen ersten Entry-Routen von SOL, LTC und BCH noch nicht.

## Maßgeblicher gemeinsamer 250-USDT-Systemtest

Alle zehn Coins konkurrierten um dasselbe Wallet und höchstens drei Blöcke.
V12.19 wurde dafür nachträglich mit seinem exakten registrierten Quelltext auf
denselben Kerzen ausgeführt; damit beruht der Vergleich nicht auf addierten
Einzelergebnissen.

| Kennzahl | V12.19 | V12.20 | Änderung |
| --- | ---: | ---: | ---: |
| Endkapital | 355,93 USDT | 529,59 USDT | +173,66 USDT |
| Nettogewinn | +105,93 USDT | +279,59 USDT | +173,66 USDT |
| Rendite | +42,37 % | +111,84 % | +69,46 Punkte |
| Trades | 133 | 135 | +2 |
| Profit Factor | 1,3069 | 2,0114 | +0,7045 |
| geschlossener Max-Drawdown | 32,78 % | 16,07 % | −16,71 Punkte |
| Entry-Blöcke | 172 | 159 | −13 |
| Zusatzblöcke | 39 | 24 | −15 |

V12.20 bestand damit die vorregistrierte relative V12.19-Systemhürde. Es blieb
aber unter der akzeptierten V12.15-Sechs-Paare-Referenz von +295,41 USDT,
Profit Factor 2,5554 und 8,19 % Drawdown. Deshalb folgt keine Champion- oder
Echtgeld-Promotion.

Pair-Beiträge im V12.20-Systemtest:

- BTC +96,97 USDT
- LINK +85,65 USDT
- XRP +70,52 USDT
- BNB +36,02 USDT
- ETH +31,14 USDT
- TRX +12,35 USDT
- DOGE +0,18 USDT
- BCH −4,31 USDT
- LTC −17,44 USDT
- SOL −31,49 USDT

## Nicht erneut ausführen: V12.21

V12.21 testete als einzige weitere Änderung `volume_ratio >= 1.00` nur für LTC
und BCH. Beide isolierten Ergebnisse verbesserten sich zusammen um 21,44 USDT,
im gemeinsamen Wallet sank der Gewinn aber auf +275,84 USDT und der Profit
Factor auf 1,9862; außerdem wurde DOGE negativ. Das Experiment ist als
`REJECT_BACKTEST_SYSTEM_GATE` im Trial Ledger erhalten. Dieser identische
LTC-/BCH-Volumenversuch darf nicht wiederholt oder nachträglich umetikettiert
werden.

## Laufzeit und alter Netzwerkfehler

Die V12.19-Laufzeitreparatur bleibt in V12.20 erhalten: Zusatz-Entry-Prüfungen
werden im historischen 1m-Detailtest nur an neuen 15m-Signalcandles ausgeführt,
ohne Stop- oder Exit-Auflösung zu reduzieren. Zehner-Einzelbatches werden nach
jedem Coin serverseitig gespeichert und können fortgesetzt werden.

Der vom Nutzer erhaltene alte Log mit `_async_get_candle_history`, veralteten
Kerzen und einem fehlgeschlagenen BTC-Orderbook-Aufruf war dagegen ein
Binance-/Netzwerkfehler des laufenden Paperbots. Er beweist weder einen
festgefahrenen historischen Backtest noch einen Strategiefehler. Bei veralteten
Marktdaten bleibt der Bot fail-closed und darf keine neuen Entscheidungen auf
alten Kerzen treffen.

## Verbindlicher nächster Zyklus

1. Den exakten V12.20-Commit pullen und den Paperbot neu starten.
2. Offizielle V12.20-Einzelhistorien für die noch nicht identisch ausgeführten
   1-, 2- und 3-Jahres-Fingerprints erzeugen. Fertige identische Zellen werden
   aus der Historie geladen, nicht erneut gerechnet.
3. Ergebnisse pro Coin in `_PAIR_HISTORIEN` und im Fingerprint-Ledger behalten.
4. SOL, LTC und BCH jeweils getrennt diagnostizieren. Pro neuer Version genau
   eine vorher begründete Hypothese testen; keine Schwellen nach demselben
   Fenster schönsuchen.
5. Jede isolierte Verbesserung anschließend im gemeinsamen Zehn-Paare-Wallet
   prüfen, weil Slot-Chronologie Einzelerfolge umkehren kann.
6. Erst nach kürzeren Zeitfenstern, Walk-Forward/Kostenstress und frischem
   Paper-Forwardlauf über eine spätere Promotion entscheiden.

Der Backtest misst immer den unveränderten aktuellen Bot. Er optimiert keine
Parameter selbst und darf niemals durch eine separate versteckte Strategie
ein besseres Ergebnis vortäuschen.
