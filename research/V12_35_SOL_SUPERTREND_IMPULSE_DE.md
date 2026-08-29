# V12.35 – SOL ATR-Supertrend-Impulse

Stand: 24.08.2026

Experiment: `V12.35-SOL-ATR-SUPERTREND-IMPULSE`

Elternstand: `V12.33-LTC-NO-TRADE-COUNTERFACTUAL`

Strategie: `CompressionBreakout250`, Version `V12.35`

Vor dem ersten V12.35-Finanzlauf registrierter SHA-256:

`a1d032d293ea6a94886c58ac39ac0fef9ec8b547f947f095b3f2c07ab2753f79`

Status: **TECHNISCH ABGEBROCHEN – KEIN FINANZERGEBNIS.**

## Hypothese und genau eine Änderung

Nachdem die vollständig vorregistrierte V12.34-Rangefamilie ihre erste
Einzelhürde verfehlte, testet V12.35 ausschließlich die im Deep-Research-
Bericht festgelegte SOL-Reservefamilie. Elternstand ist die bestandene V12.33;
die verworfene V12.34-Logik ist nicht enthalten.

1. Der 4h-Supertrend(14, 3,5) wechselt auf long.
2. 4h-Schluss liegt über EMA200; EMA200 liegt über ihrem Stand vor sechs
   abgeschlossenen 4h-Kerzen; ADX14 ist mindestens 20 und 30-Tage-Momentum
   mindestens 5 Prozent.
3. Innerhalb der ersten vier geschlossenen 15m-Kerzen nach dem Flip wird nur
   das erste Signal mit Schluss über EMA20 und RSI14 zwischen 50 und 72
   gekauft.
4. SOL erhält genau einen 80-USDT-Block und kein Pyramiding.
5. Exit ausschließlich beim 4h-Supertrend-Shortflip beziehungsweise durch
   unveränderten Hard-Stop, ROI oder Protections.

LTC bleibt ohne Entry. Die übrigen acht Routen, 250-USDT-Wallet, drei Plätze,
80 USDT je Platz, Spot long-only 1x und alle Sicherheitsregeln bleiben
V12.33. Jeder Platz ist vom Fill bis zum endgültigen Exit belegt.

## Vor dem ersten Ergebnis bindende Hürden

1. SOL allein über drei Jahre: mindestens +20 USDT, mindestens zwölf Trades,
   Profit-Faktor über 1,30 und Drawdown höchstens 12 Prozent.
2. SOL im jüngsten Jahr: mindestens drei Trades und positiv.
3. SOL bei 0,3 Prozent Gebühr je Seite: mindestens +10 USDT und
   Profit-Faktor über 1,20.
4. Im gemeinsamen Lauf muss SOL positiv sein; Gesamtgewinn über
   +421,9152 USDT, Profit-Faktor mindestens 2,4530 und geschlossener Drawdown
   höchstens 12,1794 Prozent. Alle anderen positiven Paare bleiben positiv.
5. Datei-, Kausalitäts-, Kapital-, Dry-run- und Sicherheitstests bleiben grün.

Scheitert die erste Hürde, enden die Finanzläufe für diese Familie. Es gibt
keine nachträgliche Schwellenänderung. V12.33 bleibt dann der Kandidat und SOL
benötigt neue, noch unbetrachtete Evidenz. Keine Echtgeldfreigabe oder
Gewinngarantie.

## Ergebnis

Der exakte Runner stoppte während `populate_entry_trend()` vor Beginn der
Simulation. Die rollierende Vier-Kerzen-Markierung wurde von Pandas als
Float-Serie geliefert und konnte deshalb nicht mit den booleschen State- und
Execution-Serien verknüpft werden. Es wurden keine Trades, kein PnL und keine
finanziellen Kennzahlen erzeugt. Der registrierte V12.35-Hash bleibt
unverändert. Die reine Datentypkorrektur benötigt gemäß Immutabilitätsvertrag
eine neue Version und einen neuen Hash: V12.36.
