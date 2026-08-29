# V12.29 – kausal ausgewählte BNB-Donchian80-Route

Stand: 24.08.2026

Experiment: `V12.29-BNB-DONCHIAN80-MACRO200`

Elternstand: `V12.22-SOL-ADX21` (aktive Vergleichsbasis)

Strategie: `CompressionBreakout250`, Version `V12.29`

Vor dem ersten Finanzlauf registrierter SHA-256:

`c02334560907c7cc61b3265daf345c13e8eb5da78a5101684ec8f3e97d1fb8cf`

Status: **VERWORFEN – EINZEL-GEWINNGATE NICHT BESTANDEN.**

## Warum BNB jetzt untersucht wird

BNB erzielte unter V12.20/V12.22 im exakten Einzeltest nur +17,82 USDT bei
18 Trades. LTC, BCH und TRX wurden inzwischen mit eigenen, dokumentierten
Hypothesen untersucht und nicht übernommen. BNB hatte dagegen noch keinen
pair-lokalen Routenversuch.

Der feste Screen verglich 186 einfache long-only Routen. Die ersten zwei
chronologischen Jahre dienten der Auswahl; das dritte Jahr blieb Validierung.
Zusätzlich wurde jede Route mit 0,3 Prozent Gebühr je Order geprüft. 19 Routen
bestanden alle Screen-Gates. Die vorab programmierte Rangfolge nach dem
schwächsten Jahresgewinn wählte:

- 4h-Schluss kreuzt über das vorherige 80-Kerzen-Hoch,
- Kurs über steigender EMA200; EMA200 heute über EMA200 vor zwölf 4h-Kerzen,
- 30-Tage-Momentum positiv,
- Exit unter dem vorherigen 20-Kerzen-Tief,
- harter Stop weiterhin -5,5 Prozent,
- ein 80-USDT-Block; BNB erhält kein Pyramiding.

Screen-Ergebnis je Jahr: +16,2479 / +8,6634 / +6,0756 USDT bei 11 / 8 / 10
Trades. Der 0,3-Prozent-Kostenstress blieb mit +16,9538 USDT und PF 1,2702
positiv. Der Screen ist nur Hypothesenwahl, keine Freqtrade-Bestätigung.

## Genau eine Änderung

Nur BNB ersetzt die V12.22-Route. Die anderen neun Paare, SOL-ADX21,
250-USDT-Wallet, maximal drei 80-USDT-Plätze, Spot long-only, 1x,
Stop-/Schutzregeln und Dry-run-Verträge bleiben unverändert.

## Vorab bindende Hürden

1. BNB drei Jahre: mindestens 24 Trades, mindestens +25 USDT, PF über 1,2,
   geschlossener Drawdown höchstens 12,5 Prozent, durchschnittlicher Einsatz
   höchstens 80,01 USDT und keine Zusatzblöcke.
2. Jüngstes Jahr: mindestens fünf Trades und mindestens +5 USDT.
3. 0,3-Prozent-Kostenstress: positiv und PF über 1,15.
4. Gemeinsames Wallet: Gewinn über +280,7752 USDT, PF mindestens 2,0230,
   Drawdown höchstens 16,07 Prozent und kein positives V12.22-Paar wird
   negativ.
5. Alle Strategie-, Kausalitäts-, Kapital-, Dry-run- und Sicherheitstests grün.

Die Schwellen und Gates werden nach Beginn des ersten exakten Laufs nicht
verändert. Scheitert ein Gate, wird V12.29 dokumentiert verworfen und die
aktive Strategie exakt auf V12.22 zurückgestellt.

## Exaktes Ergebnis und Entscheidung

Der verriegelte Freqtrade-Lauf mit 1m-Intracandle-Ausführung ergab für BNB über
drei Jahre:

- **+22,530 USDT** aus 31 Trades,
- PF 1,38,
- geschlossener Drawdown 10,18 Prozent,
- durchschnittlicher Einsatz 79,671 USDT,
- keine Zusatzblöcke.

Tradezahl, PF, Drawdown und Kapitalregel bestanden. Der Gewinn verfehlte aber
die vorab festgelegten +25 USDT um 2,470 USDT. Deshalb wurden jüngstes Jahr,
Gebührenstress und gemeinsames Wallet nicht mehr gestartet.

Entscheidung: `REJECT_DO_NOT_PROMOTE`. V12.22 wird bytegenau wiederhergestellt.
Die BNB80-Schwellen werden auf diesem eingesehenen Zeitraum nicht angepasst.

Nach dem Lauf wurde im reinen Hypothesen-Screen zusätzlich entdeckt, dass eine
am Segmentende noch offene Diagnoseposition nicht zum letzten Segmentkurs
geschlossen wurde. Dieser Screen-Fehler betrifft nicht den exakten Freqtrade-
Lauf und hat keine Strategie freigegeben. Der Screen muss vor jeder weiteren
Hypothesenauswahl versioniert repariert und erneut ausgeführt werden.
