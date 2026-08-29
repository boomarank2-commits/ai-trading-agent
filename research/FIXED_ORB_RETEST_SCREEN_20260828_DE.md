# Fester UTC-Opening-Range-Retest – älterer kausaler Screen

Stand: 28.08.2026

## Vorab festgelegte Route

Ohne Parameter-Sweep wurde eine deterministische Crypto-ORB-Definition auf
SOL, BNB, LINK, TRX und LTC geprüft:

- Opening Range aus den geschlossenen 15m-Kerzen 00:00 bis 04:00 UTC;
- bestätigter Schluss über dem Range-Hoch;
- innerhalb der nächsten vier Stunden Retest des Hochs und Schluss wieder
  darüber;
- Entry am nächsten 15m-Open, Ziel eine volle Range-Breite über dem Entry;
- sonst Exit zum UTC-Tagesende, −5,5 Prozent Hard-Stop;
- ein 80-USDT-Block, kein Pyramiding.

Fünf feste ältere Jahresfenster von August 2020 bis Juli 2025 wurden in drei
Auswahl- und zwei Validierungsfenster geteilt. Der Zeitraum ab August 2025
wurde nicht gelesen.

## Ergebnis

| Pair | P/L 0,2 % | Trades | PF | Auswahl positiv | Validierung positiv | 0,3-%-Stress | Exakt öffnen? |
|---|---:|---:|---:|---:|---:|---:|---|
| SOL | −372,74 | 860 | 0,68 | 0/3 | 0/2 | −509,45 | Nein |
| BNB | −311,87 | 845 | 0,55 | 0/3 | 0/2 | −446,31 | Nein |
| LINK | −244,28 | 880 | 0,76 | 1/3 | 0/2 | −384,45 | Nein |
| TRX | −227,16 | 914 | 0,64 | 0/3 | 0/2 | −372,80 | Nein |
| LTC | −218,41 | 809 | 0,70 | 1/3 | 0/2 | −347,28 | Nein |

Kein Pair bestand die Stabilitäts- oder Kostenregeln. Daher wurde kein
exakter Freqtrade-Kandidat geöffnet und der Paperbot blieb unverändert. Diese
feste UTC-4h-ORB-Nachbarschaft darf auf dem bekannten Zeitraum nicht
nachträglich passend gestimmt werden.
