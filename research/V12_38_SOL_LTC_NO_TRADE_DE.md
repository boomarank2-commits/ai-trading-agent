# V12.38 – SOL und LTC ohne unbewiesenen Entry

Stand: 25.08.2026

Experiment: `V12.38-SOL-LTC-NO-TRADE-COUNTERFACTUAL`

Elternstand: `V12.33-LTC-NO-TRADE-COUNTERFACTUAL`

Strategie: `CompressionBreakout250`, Version `V12.38`

Vor dem ersten V12.38-Finanzlauf registrierter SHA-256:

`df57d11fb3c5cc4d993d59f15859fae36efaa14a7184377b05c70ef833289d02`

Status: **VERWORFEN – ERHALTUNGSHÜRDE FÜR ETH VERFEHLT.**

## Genau eine neue Entscheidung gegenüber V12.33

SOL eröffnet keinen Trade (`enter_long = 0`). LTC bleibt entsprechend der
bestandenen V12.33-Entscheidung ebenfalls ohne Einstieg. Die zehn Coins
bleiben in Whitelist, Datenpflege, UI und Einzeltest-Auswahl sichtbar; nur die
beiden bisher nicht systemisch validierten Routen belegen keinen Kapitalplatz.

Der Grund ist paarlokal und kausal: Der aktive SOL-Pfad trug im V12.31-/
V12.33-System −39,910 USDT bei. Die neue Rangefamilie verlor isoliert, die
Supertrend-Reserve war positiv, verfehlte jedoch ihre vorab festgelegte
Mindeststichprobe. Dieser Versuch behauptet nicht, SOL sei dauerhaft
unhandelbar; er prüft nur, ob kein SOL-Entry unter der heutigen Evidenz mehr
Shared-Wert besitzt.

Die acht übrigen Routen bleiben V12.33. Unverändert: gemeinsames Wallet 250
USDT, höchstens drei offene 80-USDT-Blöcke, 240 USDT Exposition, Plätze bis
zum vollständigen Trade-Exit belegt, Spot long-only 1x, −5,5 Prozent
Hard-Stop, ROI, Protections, Gebühren und Dry-run-Sicherheit.

## Vor dem ersten Ergebnis bindende Hürden

1. SOL und LTC erzeugen im Einzel- und gemeinsamen Lauf null Trades und null
   PnL.
2. Gemeinsam: Gewinn über +421,9152 USDT, Profit-Faktor mindestens 2,4530 und
   geschlossener Drawdown höchstens 12,1794 Prozent.
3. Alle acht unter V12.33 positiven Coins bleiben positiv.
4. Maximal drei offene Trades; ein Platz wird erst nach dem endgültigen Exit
   frei. Keine Futures-, Margin-, Short-, DCA- oder Echtgeldfunktion.
5. Datei-, Kausalitäts-, Kapital-, Dry-run- und Sicherheitstests bleiben grün.

Scheitert eine Hürde, bleibt V12.33 aktiv. Besteht sie, ist V12.38 nur ein
Paper-Kandidat; neue SOL/LTC-Familien benötigen frische, separat
vorregistrierte Evidenz. Keine Echtgeldfreigabe oder Gewinngarantie.

## Ergebnis

Der gemeinsame Lauf verbesserte die Gesamtkennzahlen, verfehlte aber die
bindende Paar-Erhaltung:

| Kennzahl | V12.33 | V12.38 | Änderung |
| --- | ---: | ---: | ---: |
| Gewinn | +421,915 USDT | **+453,234 USDT** | +31,319 USDT |
| Endkapital | 671,915 USDT | **703,234 USDT** | +31,319 USDT |
| Trades | 154 | **144** | −10 |
| Profit-Faktor | 2,4530 | **2,7500** | besser |
| geschlossener Drawdown | 12,1794 % | **11,61 %** | besser |
| SOL/LTC | −39,910 / 0 USDT | **0 / 0 USDT** | besser |
| ETH | +9,186 USDT | **−1,662 USDT** | Hürde verletzt |

Die geänderte Slot- und Protection-Chronologie ließ fünf zusätzliche
ETH-Trades zu und machte ETH negativ. Deshalb kann die höhere Gesamtrendite
die vorregistrierte Erhaltungshürde nicht nachträglich überschreiben.
Entscheidung: `REJECT_DO_NOT_PROMOTE`; aktive Quelle zurück auf den exakten
V12.33-Hash.
