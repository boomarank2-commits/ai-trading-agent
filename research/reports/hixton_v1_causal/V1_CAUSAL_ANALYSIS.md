# Hixton V1 – Causal Analysis Screen

Source archive: `HIXTON_V1_DIAGNOSTIK_KOMPLETT_20260830.zip`  
Experiment: `HIXTON-V1-TRADE-DIAGNOSTICS` / `HIXTON-V1-DIAG`  
Strategy SHA256: `d43da032ad8aac714da60027702f84b584fc9cbc7e84038ca06847b5c2342290`

## Methodische Leitplanken

- Tradezahl ist keine Optimierungsmetrik; sie ist nur eine Retention-Guardrail.
- Entry-Screen verwendet ausschließlich Werte aus dem gespeicherten Entry-Snapshot.
- Kandidatenschwellen sind feste Discovery-Quantile (untere/obere 20 %) bzw. boolesche 1h/4h-Zustände; keine Schwellen-Mikrooptimierung.
- Kandidatenauswahl benutzt Discovery (60 %) + Validation (20 %). Holdout (20 %) wird nur berichtet und darf die Auswahl nicht steuern.
- MFE/MAE dienen als Outcomes/Diagnose, nicht als rückblickende Entry-Features.
- Kein Dead-Trend-Exit wird aus `max_rate` allein simuliert; dafür ist die zeitliche Candle-Sequenz zwingend.

## V1 Diagnose pro Coin

| Pair | Trades | Net P/L | PF | Failed starts | Profitable→lost | Failed-start damage | Profitable→lost damage |
|---|---:|---:|---:|---:|---:|---:|---:|
| BTC/USDT | 674 | -149.16 | 0.709 | 165 | 319 | 222.78 | 290.01 |
| ETH/USDT | 651 | -93.64 | 0.847 | 110 | 344 | 188.18 | 425.45 |
| SOL/USDT | 664 | -57.09 | 0.927 | 73 | 365 | 171.06 | 615.29 |
| XRP/USDT | 624 | -46.16 | 0.933 | 121 | 323 | 236.59 | 447.90 |
| BNB/USDT | 587 | -170.06 | 0.665 | 136 | 281 | 200.49 | 307.36 |
| DOGE/USDT | 648 | -49.66 | 0.936 | 97 | 355 | 215.24 | 563.56 |
| LINK/USDT | 676 | -130.64 | 0.847 | 99 | 366 | 241.28 | 610.00 |
| TRX/USDT | 784 | -37.23 | 0.910 | 219 | 324 | 208.36 | 206.31 |
| LTC/USDT | 420 | -172.04 | 0.642 | 68 | 229 | 140.74 | 339.23 |
| BCH/USDT | 600 | -170.64 | 0.758 | 90 | 333 | 201.36 | 504.18 |

## Entry-Filter-Kandidaten

**Keine Einzelfeature-Regel erfüllt derzeit die konservativen Discovery+Validation-Kriterien.** Das ist ein valider negativer Befund und kein Grund, Schwellen nachzuoptimieren.

Insbesondere darf daraus aktuell keine einfache V6-Regel wie `ADX > X`, `RSI > X`, `4h grün` oder `Entry-Candle > X ATR` abgeleitet werden.

## Dead-Trend-Forschungsqueue

Diese Tabelle ist **keine Exit-Regel**. Sie priorisiert nur, bei welchen Coins die Candle-Pfad-Rekonstruktion den größten Hebel hat.

| Pair | Profitable→lost | davon >=1 % MFE | Verlustschaden | Median MFE | Median Giveback |
|---|---:|---:|---:|---:|---:|
| SOL/USDT | 365 | 250 | 615.29 | 1.53 % | 3.71 % |
| LINK/USDT | 366 | 260 | 610.00 | 1.63 % | 3.73 % |
| DOGE/USDT | 355 | 265 | 563.56 | 1.66 % | 3.76 % |
| BCH/USDT | 333 | 233 | 504.18 | 1.61 % | 3.38 % |
| XRP/USDT | 323 | 219 | 447.90 | 1.39 % | 2.93 % |
| ETH/USDT | 344 | 216 | 425.45 | 1.26 % | 2.83 % |
| LTC/USDT | 229 | 155 | 339.23 | 1.33 % | 3.14 % |
| BNB/USDT | 281 | 167 | 307.36 | 1.21 % | 2.57 % |
| BTC/USDT | 319 | 190 | 290.01 | 1.13 % | 2.29 % |
| TRX/USDT | 324 | 116 | 206.31 | 0.83 % | 1.56 % |

## Nächster zwingender Schritt vor V6

1. Für `PROFITABLE_THEN_LOST` und Fat-Tail-Gewinner die tatsächliche 1m/15m-Candle-Sequenz zwischen Entry und Exit rekonstruieren.
2. Nur kausal verfügbare Zustandswechsel untersuchen: Zeit seit letztem Hoch, Drawdown vom laufenden Hoch, VIDYA-Slope-Knick, Rückfall relativ zu VIDYA/ATR, Volumen-/Momentum-Verlust, bestätigte 1h/4h-Zustandsänderung.
3. Dead-Trend-Kandidaten zuerst offline auf Discovery definieren, auf Validation bestätigen und erst danach einmalig auf Holdout prüfen.
4. Erst danach Entry-Filter und Exit-Mechanismus kombinieren und im echten 250-USDT/3×80-Portfolio simulieren.

**Kein V6-Tradingcode darf allein aus diesem Entry-Screen abgeleitet werden.**
