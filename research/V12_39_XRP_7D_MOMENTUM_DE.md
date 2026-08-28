# V12.39 – XRP 7-Tage-Momentum als getrennte Reservefamilie

Stand: 28.08.2026

Experiment: `V12.39-XRP-7D-TIME-SERIES-MOMENTUM`

Finanzieller Elternstand: `V12.33-LTC-NO-TRADE-COUNTERFACTUAL`

Strategie: `CompressionBreakout250V1239`, Version `V12.39`

Vor dem ersten exakten Finanzlauf registrierter Kandidaten-SHA-256:

`7d12e06a96d6286fa7730204bdcf937b8490a94e7424a5ea53b0dc8a7339e480`

Unveränderter Eltern-SHA-256:

`58d59413ef41b798c75c41bab0f98e377316ad3b289b6ba874876e841cdfb263`

Status: **ABGELEHNT – NICHT PROMOVIEREN UND NICHT IDENTISCH WIEDERHOLEN.**

## Warum dieser Versuch zulässig ist

Die Route stammt unverändert aus der pair-lokalen Deep-Research-Übergabe und
wurde nicht aus dem bekannten exakten Drei-Jahresfenster abgeleitet. Ein
kausaler Research-Screen prüfte sie anschließend auf fünf älteren
Jahresscheiben von August 2020 bis Juli 2025: vier Jahre waren positiv. Über
alle fünf Scheiben erzielte die feste Route bei 0,2 Prozent Gebühr je Seite
+156,012 USDT mit 91 Trades und PF 1,72; bei 0,3 Prozent je Seite blieben
+141,155 USDT und PF 1,62. Der Screen verwendet 15m-Ausführung und ist keine
Freqtrade-Bestätigung.

## Genau eine neue Entscheidung

Nur `XRP/USDT` ersetzt seinen V12.33-Donchian-Pfad:

1. Auf einer vollständig geschlossenen 4h-Kerze kreuzt die Sieben-Tage-
   Rendite (`Close / Close.shift(42) - 1`) erstmals über +5 Prozent.
2. Der 4h-Schluss liegt über EMA100, EMA100 ist höher als sechs 4h-Kerzen
   zuvor und ADX14 ist mindestens 18.
3. Innerhalb der folgenden abgeschlossenen 4h-Signalkerze wird nur die erste
   15m-Ausführung mit Schluss über EMA20, RSI14 höchstens 75 und positivem
   Volumen zugelassen.
4. XRP erhält genau einen 80-USDT-Block und kein Pyramiding.
5. Exit bei Sieben-Tage-Momentum höchstens null oder 4h-Schluss unter EMA100;
   Hard-Stop −5,5 Prozent, ROI, Gebühren und Protections bleiben unverändert.

Die übrigen neun Paare bleiben V12.33. Unverändert bleiben 250 USDT, maximal
drei gleichzeitig belegte 80-USDT-Plätze, 240 USDT Exposition, Spot long-only
1x, kein Verlustnachkauf, Futures, Margin oder Short und `dry_run: true`.

## Vor dem ersten exakten Ergebnis bindende Hürden

1. XRP drei Jahre bei 0,2 Prozent Gebühr je Seite: mehr als V12.33
   (+92,733 USDT), mindestens 30 Trades, PF mindestens 1,50 und geschlossener
   Drawdown höchstens 15 Prozent.
2. XRP jüngstes Jahr: mindestens acht Trades und positiver Nettogewinn.
3. XRP drei Jahre bei 0,3 Prozent Gebühr je Seite: positiv, PF mindestens
   1,35 und mindestens +70 USDT.
4. Gemeinsames Zehn-Paare-Wallet: Gewinn über +421,9152 USDT, PF mindestens
   2,4530 und geschlossener Drawdown höchstens 12,1794 Prozent. Jedes unter
   V12.33 positive Pair bleibt positiv.
5. Höchstens drei 80-USDT-Plätze; Freigabe erst nach endgültigem Trade-Exit.
   Alle Datei-, Kausalitäts-, Kapital-, Dry-run- und Sicherheitstests bleiben
   grün.

Scheitert die erste Hürde, enden die exakten Finanzläufe und V12.33 bleibt
aktiv. Nach Ergebnisansicht werden keine XRP-Schwellen verändert. Ein
bestandener historischer Versuch wäre nur ein neuer Paper-/Dry-run-Kandidat,
keine Echtgeldfreigabe und keine Gewinngarantie.

## Ergebnis

Der erste bindende exakte Lauf wurde am 28.08.2026 mit dem unveränderten
Kandidaten, `--timeframe-detail 1m`, aktivierten Protections und 0,2 Prozent
Gebühr je Seite ausgeführt. Tatsächlicher Zeitraum: 25.08.2023 bis
24.08.2026. Ergebnis:

- Start 250,000 USDT, Ende 231,541 USDT;
- **−18,459 USDT** beziehungsweise −7,383 Prozent;
- 38 Trades, acht Gewinner und 30 Verlierer;
- Profit-Faktor 0,7799;
- geschlossener Maximal-Drawdown 13,334 Prozent;
- zehn Stop-Loss-Exits kosteten zusammen −47,018 USDT; ein einzelner
  50-Prozent-ROI-Gewinner lieferte +40,068 USDT.

Die Datei-/Candle-Aufzeichnung sah genau die vorgesehenen XRP-Dateien für
1m, 15m, 1h und 4h und keine Kindprozesse. Test-Fingerprint:
`c24bac1eaf7a3710697be21de864312949b6aa58dc97835a205462bdfc96cd35`.

Damit scheiterten Gewinn und Profit-Faktor bereits an Hürde 1. Der jüngste
Jahreslauf, Gebührenstress und gemeinsame Zehn-Paare-Lauf wurden entsprechend
der Vorregistrierung nicht geöffnet. Die aktive V12.33 blieb byte-identisch.

## Erkenntnis und nächster zulässiger XRP-Schritt

Der kausale 15m-Screen überschätzte diese Route, weil die echte Bot-Ausführung
mit 1m-Detail, Stopps, ROI und Protections eine wesentlich schwächere
Trade-Verteilung erzeugte. Die betrachteten Schwellen 5 Prozent, EMA100,
ADX18, RSI75 und der Momentum/EMA100-Exit werden nicht nachträglich angepasst.
Ein weiterer XRP-Versuch braucht eine materiell andere, vorab registrierte
Familie oder frische Forward-Evidenz; der bestehende positive V12.33-XRP-Pfad
bleibt aktiv.
