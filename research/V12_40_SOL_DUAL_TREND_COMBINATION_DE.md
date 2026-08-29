# V12.40 – SOL-Kombination aus Donchian und Supertrend

Stand: 28.08.2026

Experiment: `V12.40-SOL-DONCHIAN-SUPERTREND-COMBINATION`

Finanzieller Elternstand: `V12.33-LTC-NO-TRADE-COUNTERFACTUAL`

Strategie: `CompressionBreakout250V1240`, Version `V12.40`

Vor dem ersten exakten Finanzlauf registrierter Kandidaten-SHA-256:

`4154d49d65d9d1d5915578d918fd7f2c095ac6af63392ea1a09bf497cf2af985`

Unveränderter Eltern-SHA-256:

`58d59413ef41b798c75c41bab0f98e377316ad3b289b6ba874876e841cdfb263`

Status: **ABGELEHNT – JÜNGSTE-JAHR-HÜRDE NICHT BESTANDEN.**

## Warum dies kein wiederholter Test ist

Der aktive SOL-Donchian-Pfad erzielte unter V12.33 drei Jahre lang nur
+8,021 USDT. Die getrennte V12.37-Supertrend-Reserve erzielte +31,960 USDT,
bestand mit zehn statt der vorab geforderten zwölf Trades aber die
Stichprobenhürde nicht und wurde nicht promoviert. V12.40 verändert keine
Schwelle dieser beiden angesehenen Familien. Es prüft erstmals ihre feste
Kombination als zwei getrennte Signalquellen für dasselbe Pair.

## Genau eine neue Entscheidung

Nur SOL erhält zusätzlich zu seinem unveränderten V12.33-Donchian-Pfad die
unveränderte V12.37-Reserve:

1. 4h-Supertrend(14, 3,5) wechselt auf long.
2. 4h-Schluss liegt über einer gegenüber sechs geschlossenen 4h-Kerzen zuvor
   steigenden EMA200; ADX14 ist mindestens 20 und 30-Tage-Momentum mindestens
   5 Prozent.
3. Innerhalb der ersten vier geschlossenen 15m-Kerzen wird nur das erste
   Signal mit Schluss über EMA20, RSI14 zwischen 50 und 72 und positivem
   Volumen zugelassen. Ein gleichzeitiges Donchian-Signal hat Vorrang.
4. Donchian-Trades behalten ihren langsamen Struktur-/Regime-Exit und den
   Failed-Breakout-Callback. Supertrend-Trades verwenden nur den Shortflip,
   Hard-Stop, ROI und Protections. Die Exit-Familien werden über den
   unveränderlichen Entry-Tag getrennt.
5. SOL bleibt bei genau einem 80-USDT-Block; kein Pyramiding.

Die übrigen neun Paare bleiben V12.33. Unverändert bleiben 250 USDT, maximal
drei gleichzeitig belegte 80-USDT-Plätze, höchstens 240 USDT Exposition,
Spot long-only 1x, kein Verlustnachkauf, Futures, Margin oder Short und
`dry_run: true`.

## Vor dem ersten exakten Ergebnis bindende Hürden

1. SOL drei Jahre bei 0,2 Prozent Gebühr je Seite: mindestens +35 USDT,
   mindestens zwölf Trades, PF mindestens 1,50 und geschlossener Drawdown
   höchstens 12 Prozent. Beide Entry-Familien müssen mindestens einen Trade
   liefern und dürfen jeweils keinen negativen Nettobeitrag haben.
2. SOL jüngstes Jahr: mindestens vier Trades und positiver Nettogewinn.
3. SOL drei Jahre bei 0,3 Prozent Gebühr je Seite: mindestens +20 USDT und PF
   mindestens 1,30.
4. Gemeinsames Zehn-Paare-Wallet: Gewinn über +421,9152 USDT, PF mindestens
   2,4530 und geschlossener Drawdown höchstens 12,1794 Prozent. SOL sowie
   jedes unter V12.33 positive Pair bleiben positiv.
5. Höchstens drei 80-USDT-Plätze; ein Platz wird erst nach endgültigem Exit
   wieder frei. Alle Datei-, Kausalitäts-, Kapital-, Dry-run- und
   Sicherheitstests bleiben grün.

Scheitert Hürde 1, enden die exakten Folgeprüfungen. Nach Ergebnisansicht
werden keine betrachteten SOL-Schwellen verändert. Ein bestandener
historischer Versuch wäre nur ein Paper-/Dry-run-Kandidat, keine
Echtgeldfreigabe und keine Gewinngarantie.

## Ergebnis

### Exakter Drei-Jahreslauf – Hürde 1 bestanden

Der unveränderte Kandidat wurde mit 1m-Ausführungsdetail, Protections und
0,2 Prozent Gebühr je Seite vom 29.08.2023 bis 28.08.2026 ausgeführt:

- Start 250,000 USDT, Ende 313,800 USDT;
- **+63,800 USDT**, 29 Trades, PF 2,00;
- geschlossener Drawdown 7,09 Prozent;
- Donchian: 19 Trades und +5,782 USDT;
- Supertrend: 10 Trades und +58,017 USDT.

Damit bestanden Gewinn, Stichprobe, PF, Drawdown und die bindende Forderung,
dass beide Familien nicht negativ beitragen. Test-Fingerprint:
`40cafddd4c4fcaf5071d58f9357dc457e337f7927130c24e96d8cd0a50402e46`.

### Jüngstes Jahr – Hürde 2 gescheitert

Der deshalb zulässige getrennte Lauf vom 29.08.2025 bis 28.08.2026 endete
mit **−6,362 USDT**, sieben Trades, PF 0,41 und 4,29 Prozent geschlossenem
Drawdown. Donchian verlor −4,158 USDT und Supertrend −2,204 USDT. Der
Test-Fingerprint lautet
`905aa138f7127938f79becce692f4361ff9bc4bae9f0b566e840d5af39e0104f`.

Die positive Dreijahreszahl ist damit zeitlich nicht robust genug. Der
0,3-Prozent-Gebührentest und der gemeinsame Zehn-Paare-Lauf wurden nicht
geöffnet. Die aktive V12.33 blieb unverändert.

## Erkenntnis und nächster zulässiger SOL-Schritt

Die feste Kombination löst die niedrige Gesamtaktivität und verbessert den
langen Zeitraum deutlich, trägt im jüngsten, fallenden SOL-Marktregime aber
keinen positiven Edge. Ein nachträglicher Marktregime-Schalter auf demselben
Fenster wäre unzulässige Anpassung. Donchian-, Supertrend-, EMA-, ADX-,
Momentum- und RSI-Schwellen dieser Version werden daher nicht verändert.
Zulässig sind nur frische Paper-Forward-Evidenz oder eine materiell andere,
vorab registrierte SOL-Familie mit eigenständiger Entwicklungsgrundlage.
