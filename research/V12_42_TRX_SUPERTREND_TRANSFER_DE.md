# V12.42 – Fester Supertrend-Transfer auf TRX

Experiment: `V12.42-TRX-SUPERTREND20X3-TRANSFER`

Elternstand: `V12.33-LTC-NO-TRADE-COUNTERFACTUAL`

Vor dem ersten exakten Finanzergebnis registrierter SHA-256:
`300c16613da7dce52b0c2b788f00b8cbf683f2d08f8097b5943e377019e157f1`

Status: **VERWORFEN – GEMEINSAME PROFIT-FAKTOR-HÜRDE VERFEHLT.**

## Entwicklungsgrundlage

Die bei DOGE bereits angenommene feste Supertrend(20,3)-Route wurde ohne
Parameter-Sweep auf fünf schwache Coins und fünf ältere Jahresfenster
übertragen. Nur TRX bestand den festgelegten Kandidatenfilter:

- +129,388 USDT, 62 Trades, PF 2,105 im älteren 15m-Screen;
- zwei von drei Auswahljahren positiv;
- beide getrennten Validierungsjahre positiv;
- +119,220 USDT und PF 1,968 bei 0,3 Prozent Gebühr je Seite.

Das ist noch kein exakter Freqtrade-Beweis. Der Screen enthält weder
1m-Detail noch Protections oder die gemeinsame Slotchronologie.

## Genau eine pair-lokale Änderung

TRX ersetzt den V12.33-Broad-Core durch:

- Entry beim 4h-Supertrend(20,3)-Longwechsel;
- 4h-Schluss über EMA100, EMA100 höher als zwölf 4h-Kerzen zuvor;
- Ausführung auf der ersten 15m-Zeile nach dem bestätigten 4h-Flip bei
  positivem Volumen; kein zusätzliches EMA20-Gate;
- Exit beim 4h-Supertrend(20,3)-Shortwechsel;
- genau ein 80-USDT-Block; TRX-Pyramiding ist aus der Freigabeliste entfernt.

Hard-Stop −5,5 Prozent, 50-Prozent-ROI, Protections, Spot long-only 1x,
Dry-run, 250 USDT und alle übrigen neun Paarentscheidungen bleiben V12.33.

Der vorgelagerte ältere Screen hatte als konservative Näherung zusätzlich
`15m close > EMA20` verlangt. Er war damit nur ein Richtungsfilter. Der
exakte Kandidat übernahm bewusst die bereits aktive DOGE-Route unverändert;
Hash und Hürden wurden vor Sichtung des exakten Ergebnisses festgeschrieben.

## Vor Ergebnisansicht bindende Hürden

1. Exakter TRX-Dreijahreslauf bei 0,2 Prozent Gebühr: mehr als +50 USDT,
   mindestens 20 Trades, PF mindestens 1,50 und geschlossener Drawdown
   höchstens 15 Prozent.
2. Jüngstes Jahr: mindestens +5 USDT und fünf Trades.
3. Dreijahres-Gebührenstress bei 0,3 Prozent je Seite: mindestens +40 USDT
   und PF mindestens 1,30.
4. Gemeinsames Zehn-Paare-Wallet: mehr als +421,9152 USDT, PF mindestens
   2,4530, Drawdown höchstens 12,1794 Prozent und jedes unter V12.33 positive
   Pair bleibt positiv.
5. Maximal drei 80-USDT-Plätze, kein Verlustnachkauf und Freigabe eines Slots
   erst nach endgültigem Trade-Exit.

Scheitert eine Hürde, enden alle späteren Finanzläufe und die aktive Quelle
wird byte-identisch auf V12.33 zurückgestellt. Nach Ansicht eines Ergebnisses
werden keine Schwellen dieser Familie verändert.

## Ergebnis

Die drei paarlokalen Hürden bestanden:

| Prüfung | Ergebnis |
|---|---:|
| TRX drei Jahre, 0,2 % | +72,321 USDT · 42 Trades · PF 2,44 · DD 6,72 % |
| TRX jüngstes Jahr | +8,786 USDT · 11 Trades · PF 2,32 |
| TRX drei Jahre, 0,3 % | +65,757 USDT · PF 2,23 · DD 7,17 % |

Der gemeinsame exakte Lauf verwendete ein einziges 250-USDT-Wallet, maximal
drei 80-USDT-Plätze, 1m-Detail und alle zehn Paare:

- Endkapital 699,720 USDT, Gewinn **+449,720 USDT**;
- 178 Trades, 50 Gewinner und 128 Verlierer;
- Profit-Faktor **2,4328**;
- geschlossener Drawdown 8,3925 Prozent;
- TRX +24,673 USDT bei 33 ausgeführten Trades;
- alle unter V12.33 positiven Paare blieben positiv; SOL blieb mit
  −0,288 USDT negativ, LTC entsprechend V12.33 ohne Entry.

Gewinn und Drawdown waren besser als V12.33 (+421,915 USDT, PF 2,4530,
DD 12,1794 Prozent). Der Profit-Faktor verfehlte jedoch die bindende
Mindesthürde um 0,0202. V12.42 wird deshalb nicht promoviert.

Ein zulässiger Folgeschritt ist genau eine vorregistrierte Kombination aus
dem unveränderten seltenen V12.33-TRX-Pfad und der unveränderten
V12.42-Supertrend-Reserve, weiter als Einzelblock. Kein Schwellenwert beider
Komponenten darf auf dem angesehenen Fenster nachjustiert werden.
