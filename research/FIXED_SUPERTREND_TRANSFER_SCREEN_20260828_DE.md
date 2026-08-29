# Fester Supertrend-Transfer – älterer OOS-Screen

Stand: 28.08.2026

## Fragestellung

Die bereits in V12.30 für DOGE akzeptierte Route wurde ohne Parameteränderung
auf SOL, BNB, LINK, TRX und LTC geprüft:

- 4h-Supertrend(20, 3) wechselt auf Long;
- 4h-Schluss über steigender EMA100;
- konservative Screen-Ausführung auf der ersten verfügbaren abgeschlossenen
  15m-Kerze über EMA20;
- Exit beim 4h-Supertrend-Shortwechsel, sonst unverändert −5,5 Prozent
  Hard-Stop und 50-Prozent-ROI;
- ein 80-USDT-Block, kein Pyramiding.

Der Screen nutzte fünf feste ältere Jahresfenster von August 2020 bis Juli
2025. Die ersten drei waren Auswahl-, die letzten zwei getrennte
Validierungsfenster. Es gab keinen Schwellen-Sweep und noch keinen exakten
Freqtrade-Lauf auf dem bekannten Zeitraum 2023 bis 2026.

## Ergebnis

| Pair | P/L 0,2 % | Trades | PF | Auswahl positiv | Validierung positiv | 0,3-%-Stress | Exakt öffnen? |
|---|---:|---:|---:|---:|---:|---:|---|
| SOL | −12,17 | 36 | 0,90 | 0/3 | 1/2 | −17,90 | Nein |
| BNB | +37,50 | 37 | 1,44 | 1/3 | 1/2 | +31,51 | Nein |
| LINK | −45,37 | 38 | 0,67 | 0/3 | 1/2 | −51,35 | Nein |
| TRX | **+129,39** | 62 | **2,10** | **2/3** | **2/2** | **+119,22** | **Ja** |
| LTC | +49,36 | 44 | 1,48 | 2/3 | 0/2 | +42,22 | Nein |

Alle Archive enthielten dieselben zehn kleinen bekannten Monatsgrenzen-Lücken
(93 fehlende 15m-Kerzen, maximal 4:45 Stunden). Der Forschungsloader markierte
6.175 angrenzende Kerzen als ungültig; daraus durfte kein Signal entstehen.

## Bindende Entscheidung

Nur TRX darf einen exakt vorregistrierten Kandidaten öffnen. SOL, BNB, LINK
und LTC dürfen diese Supertrend(20,3)-Transferidee nicht auf dem bekannten
Dreijahresfenster ausführen oder nachträglich nachjustieren. Der Screen ist
nur ein Kandidatenfilter: Er simuliert weder Freqtrade-Protektionen noch
1m-Detail, Pyramiding oder die gemeinsame 3×80-USDT-Slotkonkurrenz.

## Audit-Hinweis zur Übertragung

Der ältere Screen enthielt zusätzlich `15m close > EMA20`. Die bereits aktive
DOGE-Route enthält dieses Gate nicht; sie handelt die erste 15m-Zeile nach dem
bestätigten 4h-Flip bei positivem Volumen. V12.42 kopierte den aktiven
DOGE-Code unverändert und wurde vor seinem exakten Ergebnis per Hash und
Hürden fixiert. Der ältere Screen ist deshalb nur ein Richtungsfilter und
keine exakte Reproduktion des späteren Freqtrade-Kandidaten.
