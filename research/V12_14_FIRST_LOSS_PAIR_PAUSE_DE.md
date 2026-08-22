# V12.14 – Pairpause nach dem ersten Verlust

## Entscheidung

**REJECT_BACKTEST – nicht in den aktiven Dry-run-Bot übernehmen.**

Die Hypothese war nachvollziehbar, aber falsch: Eine 72-Stunden-Pause nach dem
ersten statt zweiten unprofitablen Pair-Trade senkte die Verlustzahl von 100 auf
95, blockierte jedoch zu viele profitable Folgesignale. Gewinn, Profit Factor,
Kapitalnutzung und Drawdown verschlechterten sich.

## Exakter Vertrag und Audit

- Run: `20260822T123801Z-715d5a9e`
- Strategy-Hash:
  `0141348dda98810508f23e6c1b63ed19fb9f5e384841b35a4d49f84d870a77f2`
- Logik-Hash:
  `e94489b502bc63a47b33ff1bacf29f8f88368cb40c7aa135a107d4cdf18c7a45`
- Fingerabdruck:
  `96ca0968e7cb333e8b63a8aac5e91459d40bc96cad1729313f4a4ed23b0b0583`
- Commit: `81893d9d286cc58f1c8d2ac27893fa2389b6821c`
- 250 USDT, 80 USDT je Position, maximal drei Positionen
- sechs Pairs gemeinsam, Spot/long-only, 15m plus 1m-Ausführungsdetails,
  0,002 Gebühr je Seite, Protections aktiv, Cache aus

Der Audit bestand. Alle 24 vorgesehenen Pair-/Timeframe-Dateien wurden ohne
Lücke oder Duplikat gelesen. Keine ungeplante Candle-Datei, keine nachträgliche
Dateiänderung, kein fremder Repository-Zugriff und kein Kindprozess wurden
beobachtet.

## Ergebnis

| Kennzahl | V12.12 | V12.14 | Veränderung |
|---|---:|---:|---:|
| Endkapital | 538,646 | 491,401 | −47,246 USDT |
| Nettogewinn | 288,646 | 241,401 | −47,246 USDT |
| Trades | 122 | 113 | −9 |
| Gewinne / Verluste | 22 / 100 | 18 / 95 | −4 / −5 |
| Profit Factor | 2,4833 | 2,2603 | −0,2230 |
| Sharpe | 0,44 | 0,3705 | niedriger |
| geschlossener Max-Drawdown | 9,62 % | 11,96 % | +2,34 Punkte |
| Kapitalzeit | 23,61 % | 20,70 % | −2,91 Punkte |
| Zeit ohne Position | 61,25 % | 65,87 % | +4,62 Punkte |

| Pair | Trades | Gewinn |
|---|---:|---:|
| BTC | 15 | +82,642 USDT |
| ETH | 36 | +53,254 USDT |
| XRP | 14 | +46,307 USDT |
| DOGE | 13 | +45,499 USDT |
| BNB | 11 | +19,159 USDT |
| SOL | 24 | −5,460 USDT |

## Dauerhafte Lehre

Weniger Verlusttrades sind kein ausreichendes Ziel. Bei seltenen
Trendfolge-Signalen kann der erste Verlust unmittelbar vor einem validen neuen
Ausbruch liegen. Eine globale Dreitagespause nach jedem ersten Verlust senkt
damit sowohl Verlust- als auch Gewinnerzahl, verschlechtert die Slotnutzung und
kann ein bisher positives Pair negativ machen. Diese konkrete Verschärfung darf
nicht erneut getestet werden.
