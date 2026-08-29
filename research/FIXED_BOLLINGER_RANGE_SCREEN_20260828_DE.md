# Feste Bollinger-Range-Reversion – älterer kausaler Screen

Stand: 28.08.2026

## Vorab festgelegte Route

Ohne Parameter-Sweep wurde die Masterplan-Route auf SOL, BNB, LINK, TRX und
LTC geprüft:

- Range-Regime: 4h-ADX14 höchstens 18 und Abstand EMA50 zu EMA200 höchstens
  drei Prozent des Schlusskurses;
- 15m-Bollinger 20/2,0;
- Long, wenn der vorherige Schluss am/unter dem unteren Band lag und die
  aktuelle Kerze zurück ins Band, aber noch unter dem Mittelband schließt;
- Exit am 15m-Mittelband;
- −5,5 Prozent Hard-Stop, 50-Prozent-ROI, ein 80-USDT-Block, kein Pyramiding.

Fünf feste ältere Jahresfenster von August 2020 bis Juli 2025 wurden in drei
Auswahl- und zwei Validierungsfenster geteilt. Der Zeitraum ab August 2025
wurde nicht gelesen.

## Ergebnis

| Pair | P/L 0,2 % | Trades | PF | Auswahl positiv | Validierung positiv | 0,3-%-Stress | Exakt öffnen? |
|---|---:|---:|---:|---:|---:|---:|---|
| SOL | −46,05 | 133 | 0,31 | 0/3 | 0/2 | −67,21 | Nein |
| BNB | −143,48 | 439 | 0,13 | 0/3 | 0/2 | −213,36 | Nein |
| LINK | −59,54 | 158 | 0,30 | 0/3 | 0/2 | −84,67 | Nein |
| TRX | −108,89 | 463 | 0,24 | 0/3 | 0/2 | −182,68 | Nein |
| LTC | −87,91 | 283 | 0,28 | 1/3 | 0/2 | −132,97 | Nein |

Kein Pair bestand die vorab gesetzten Stabilitäts- und Kostenregeln. Daher
wurde kein exakter Freqtrade-Kandidat geöffnet und am Paperbot nichts
geändert. Diese feste Bollinger20/2-Range-Nachbarschaft darf auf dem bekannten
Fenster nicht nachträglich pro Coin passend gestimmt werden.
