# Fester Ichimoku-Transfer – älterer kausaler Screen

Stand: 28.08.2026

## Vorab festgelegte Route

Der Screen prüfte genau einen klassischen 4h-Ichimoku-Satz 9/26/52/26 ohne
Parameter-Sweep auf SOL, BNB, LINK, TRX und LTC:

- Tenkan kreuzt Kijun nach oben;
- Schluss über der zum aktuellen Zeitpunkt bekannten Cloud;
- die aus der aktuellen Kerze berechenbare künftige Cloud ist bullisch;
- aktueller Schluss liegt über dem Schluss vor 26 4h-Kerzen;
- Exit bei bärischem Tenkan/Kijun-Kreuz oder Schluss unter der aktuellen Cloud;
- unverändert −5,5 Prozent Hard-Stop, 50-Prozent-ROI, ein 80-USDT-Block,
  kein Pyramiding.

Die Cloud-Werte für den aktuellen Zeitpunkt wurden um 26 Kerzen verschoben;
es wurden keine zukünftigen Kerzen gelesen. Fünf feste Jahresfenster von
August 2020 bis Juli 2025 dienten als drei Auswahl- und zwei
Validierungsfenster. Der Zeitraum ab August 2025 wurde nicht gelesen.

## Ergebnis

| Pair | P/L 0,2 % | Trades | PF | Auswahl positiv | Validierung positiv | 0,3-%-Stress | Exakt öffnen? |
|---|---:|---:|---:|---:|---:|---:|---|
| SOL | **+231,79** | 74 | **2,40** | **3/3** | **2/2** | **+219,50 / PF 2,28** | **Ja** |
| BNB | +46,33 | 75 | 1,36 | 3/3 | 1/2 | +34,25 / PF 1,25 | Nein |
| LINK | +50,67 | 63 | 1,35 | 1/3 | 2/2 | +40,50 / PF 1,27 | Nein |
| TRX | +30,57 | 68 | 1,26 | 2/3 | 2/2 | +19,64 / PF 1,16 | Nein |
| LTC | +25,45 | 73 | 1,16 | 2/3 | 0/2 | +13,73 / PF 1,08 | Nein |

Nur SOL bestand die vorab gesetzten Regeln: mindestens zwei positive
Auswahlfenster, beide Validierungsfenster positiv, mindestens 15 Trades sowie
im Kostenstress mindestens +30 USDT und PF 1,30. Die anderen vier Paare
dürfen mit dieser Familie auf dem bekannten Fenster nicht nachjustiert werden.

Der Screen ist nur ein Kandidatenfilter. Er simuliert nicht Freqtrades
1m-Detail, Protections oder die gemeinsame 3×80-USDT-Slotchronologie. Diese
Prüfungen sind bindende spätere Hürden eines separat gehashten Kandidaten.
