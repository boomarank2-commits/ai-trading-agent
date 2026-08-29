# V12.25 – BCH-Donchian durch eine geprüfte EMA-Trendroute ersetzen

Stand: 24.08.2026

Experiment: `V12.25-BCH-EMA30-80-MACRO100`

Elternstand: `V12.22-SOL-ADX21`

Strategie: `CompressionBreakout250`, Version `V12.25`

Vor dem ersten Finanzlauf registrierter SHA-256:

`5b4ac18b86d38a86114a67955bd5b452c52526211513a880f8de2f86bce92c5d`

Status: **TECHNISCH ABGEBROCHEN – KEIN FINANZERGEBNIS.**

Der erste exakte Aufruf stoppte vor der Simulation mit `KeyError:
bch_ema_fast`: Die drei BCH-EMA-Basisspalten waren versehentlich im
1h-Decorator angelegt, während Cross und Entry sie im 4h-Decorator benötigen.
Es wurden keine Trades und keine Ergebniskennzahlen erzeugt. Die registrierte
V12.25 wird nicht editiert; die reine Verdrahtungskorrektur erhält als V12.26
einen neuen Hash und eine eigene Ledger-Zeile.

## Diagnose und kausaler Screen

BCH verlor im unabhängigen V12.22-Dreijahreslauf 24,25 USDT bei 18 Trades,
Profit-Faktor 0,46 und 12,52 Prozent Drawdown. Im gemeinsamen V12.22-Wallet
betrug sein Beitrag −4,305 USDT.

Der feste 4h-Screen prüfte dieselben 186 transparenten Varianten wie zuvor für
LTC. Jahr 1 und 2 waren Auswahlfenster; Jahr 3 und 0,3 Prozent Gebühr je Seite
waren getrennte Prüfungen. Genau eine Route bestand alle Hürden:

- EMA30 kreuzt auf 4h über EMA80;
- Schlusskurs über EMA100;
- EMA100 höher als vor zwölf 4h-Kerzen;
- ADX mindestens 24;
- Exit bei EMA30 unter EMA80 oder Schlusskurs unter EMA80.

Die drei Jahresscheiben ergaben im vereinfachten Screen +0,750, +21,001 und
+2,271 USDT. Der Kostenstress ergab +17,343 USDT, 20 Trades und PF 1,349.
Diese Zahlen sind nur die Auswahlbegründung und kein Ersatz für Freqtrade.

## Eine Änderung und vorab festgelegte Hürden

Nur BCH ersetzt Entry und Exit. Der 5,5-Prozent-Hard-Stop bleibt bestehen, BCH
erhält weiterhin keine Zusatzblöcke. Alle neun anderen Pair-Routen, 250 USDT,
80 USDT je Block, maximal drei Positionen, Spot, Long-only, 1x, Protections,
Gebühren und Dry-run bleiben unverändert.

V12.25 wird nur fortgesetzt, wenn:

1. BCH über drei Jahre mindestens 15 Trades, positives Ergebnis, PF über 1,0,
   weniger als 12,52 Prozent Drawdown und mindestens 35 USDT Verbesserung
   gegenüber V12.22 erreicht;
2. das letzte Jahr bei mindestens drei Trades positiv bleibt;
3. BCH bei 0,3 Prozent Gebühr je Seite über drei Jahre positiv bleibt;
4. das gemeinsame Wallet V12.22 mit +280,7752 USDT und PF 2,0230 übertrifft,
   ohne 16,07 Prozent Drawdown zu überschreiten;
5. kein zuvor positives Paar negativ wird und alle Sicherheitsverträge grün
   bleiben.

Scheitert eine Hürde, wird V12.25 dokumentiert verworfen und die aktive
Strategie exakt auf V12.22 zurückgesetzt. Innerhalb dieser registrierten
Version werden nach dem ersten Ergebnis keine Parameter geändert.
