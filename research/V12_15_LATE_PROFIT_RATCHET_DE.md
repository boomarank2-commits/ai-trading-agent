# V12.15 – späte Gewinnsicherung für Champion-Trends

## Entscheidung

**ACCEPT_DRY_RUN_CANDIDATE.** V12.15 hat alle vorab festgelegten Strategie- und
Audit-Grenzen bestanden und ersetzt V12.12 als aktiven Paper-/Dry-run-Kandidaten.
Das ist keine Echtgeldfreigabe und kein Profitversprechen.

## Exakter Vertrag

- Run: `20260822T125812Z-68ac18a2`
- getesteter Commit: `bcf384fed3297e771a5ce78e2880e14af77346f9`
- Strategy-Hash:
  `3c5aaf823e16c1a2901c4861fcf6dbc21da4dd0f1314385d78be1f2de86c4a97`
- Logik-Hash:
  `0b5739c5e8c8d04f6754fe220d5f77a8051b5db9ea8b3e3202afd750e0e781eb`
- Fingerabdruck:
  `f1d6ff6bbb489e0526b41487e126e509a8f20e1a1b8b84345a3cbeda79a28549`
- 23.08.2023 bis 22.08.2026, 1.095 Tage
- ein gemeinsames 250-USDT-Konto, 80 USDT je Position, maximal drei Positionen
- BTC/ETH/SOL/XRP/BNB/DOGE, Spot/long-only, kein Hebel, kein DCA
- 15m-Strategy, 1m-Ausführungsdetails, 0,002 Gebühr je Seite, Protections an,
  Cache aus

Einzige Handelsänderung gegen V12.12: Nur ein `champion_donchian`-Trade, der
mindestens +30 % laufenden Gewinn erreicht, erhält danach einen +5-%-Stopboden.
Reclaims und alle Trades unterhalb +30 % behalten exakt den V12.12-Stop-/Exit-
Pfad. `LowProfitPairs.trade_limit` steht wieder auf 2.

## Formaler Audit

Der Strategy-Hash stimmte vor und nach dem Lauf. Beide vorgesehenen Configs und
alle 24 Pair-/Timeframe-Candle-Dateien wurden beobachtet. Es gab keine fehlenden
oder unerwarteten Kerzen, keine Lücken, Duplikate oder nachträglichen
Dateiänderungen, keine ungeplanten Repository-Lesezugriffe und keine
Kindprozesse. Der Lauf ist formal gültig.

## Ergebnis gegen V12.12

| Kennzahl | V12.12 | V12.15 | Veränderung |
|---|---:|---:|---:|
| Endkapital | 538,646 | 545,409 | +6,763 USDT |
| Nettogewinn | 288,646 | 295,409 | +6,763 USDT |
| Rendite | 115,46 % | 118,16 % | +2,70 Punkte |
| Trades | 122 | 122 | 0 |
| Gewinne / Verluste | 22 / 100 | 23 / 99 | +1 / −1 |
| Profit Factor | 2,4833 | 2,5554 | +0,0721 |
| Sharpe | 0,44 | 0,4498 | höher |
| geschlossener Max-Drawdown | 9,62 % | 8,19 % | −1,43 Punkte |
| maximale Verlustserie | 34 | 25 | −9 |
| Kapitalzeit | 23,61 % | 23,07 % | −0,54 Punkte |
| Zeit ohne Position | 61,25 % | 61,33 % | +0,08 Punkte |

Die kleine Nutzungsverschlechterung blieb deutlich innerhalb des vorab gesetzten
22/63-Gates. Gewinn, Profit Factor, Drawdown und Verlustserie verbesserten sich.

## Pair- und Exit-Attribution

| Pair | Trades | Gewinn | Gewinne / Verluste |
|---|---:|---:|---:|
| XRP | 12 | +106,760 USDT | 4 / 8 |
| BTC | 16 | +81,359 USDT | 4 / 12 |
| ETH | 38 | +50,164 USDT | 4 / 34 |
| DOGE | 18 | +30,335 USDT | 2 / 16 |
| BNB | 16 | +22,784 USDT | 5 / 11 |
| SOL | 22 | +4,007 USDT | 4 / 18 |

Die drei Ratchet-Exits waren mit zusammen +11,988 USDT positiv. Acht
unveränderte ROI-Exits lieferten +320,210 USDT; die seltene große Trendquelle
wurde also nicht abgeschnitten. Der normale −5,5-%-Hard-Stop bleibt vor dem
+30-%-Trigger unverändert.

## Nächste Arbeit ohne Testkreis

- Diesen exakten Fingerabdruck nie erneut ausführen.
- V12.15 im Dry-run unverändert vorwärts beobachten und Entscheidungen/Exits
  mit den Backtest-Tags vergleichen.
- Vor einer weiteren Strategy-Änderung ein neues, nicht identisches Fenster und
  eine einzelne Hypothese festlegen.
- Keine frühere Pair-Sperre, keinen allgemeinen 36h-/48h-Zeitstopp und keinen
  frühen +5→+1-Ratchet wieder einführen; diese Richtungen sind dokumentiert
  verworfen.
