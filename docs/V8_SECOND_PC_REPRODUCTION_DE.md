# V8 Reproduzierbarkeitstest auf zweitem Windows-PC

Stand: 16.08.2026

## Zweck

Nach der Promotion von V8 wurde das Repository auf einem zweiten Windows-System frisch aus GitHub geladen und die drei autoritativen 3-Jahres-Einzelpaar-Backtests erneut ueber die normale Testbot-Backtest-Oberflaeche ausgefuehrt. Ziel war nicht eine weitere Optimierung, sondern eine unabhaengige Reproduzierbarkeitspruefung des bereits validierten Kandidaten.

## Laufvertrag

Alle drei Runs verwendeten:

- Strategieklasse `CompressionBreakout250` (V8 Slow Donchian)
- 250 USDT Backtest-Wallet
- 80 USDT Stake
- Binance Spot, long-only
- 15m Haupttimeframe
- 1m Detail-Timeframe
- `--fee 0.002` je Orderseite
- `--enable-protections`
- `--cache none`
- exakt den vom laufenden Bot geladenen Strategy-Quelltext ueber `locked_backtest_freqtrade.py`

Der auf Windows geloggte Raw-SHA256 ist aufgrund CRLF-Zeilenenden:

`a079c7fe73b151618ddc48559763d70da990a35d9d424fea6b0458463cdff8fc`

Nach Normalisierung der Zeilenenden auf LF ergibt derselbe Quelltext exakt den Research-Fingerprint:

`9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280`

Die normalisierten Strategy-Dateien sind byte-identisch mit dem V8-Research-Quelltext. Der unterschiedliche Raw-Hash ist daher kein Strategy-Unterschied, sondern ausschliesslich Windows-CRLF gegen LF.

## Ergebnis auf dem zweiten PC

Der rollende 3-Jahres-Zeitraum lief am 16.08.2026 von 17.08.2023 bis 16.08.2026 und umfasste in allen drei Runs 1095 Tage.

| Pair | Trades | P/L USDT | Rendite | Profit Factor | Winrate | Max. DD |
|---|---:|---:|---:|---:|---:|---:|
| BTC/USDT | 20 | +52.488 | +20.995 % | 3.386 | 30.0 % | 3.07 % |
| ETH/USDT | 20 | +55.485 | +22.194 % | 2.827 | 20.0 % | 7.58 % |
| SOL/USDT | 21 | +44.125 | +17.650 % | 1.875 | 23.8 % | 10.91 % |

## Exakte Reproduktion

Die drei Trade-Listen wurden gegen die zuvor gesicherten autoritativen V8-Research-Runs verglichen.

Ergebnis:

- BTC: 20 von 20 Trades exakt identisch
- ETH: 20 von 20 Trades exakt identisch
- SOL: 21 von 21 Trades exakt identisch
- Open-/Close-Zeitpunkte, Preise, Profitwerte und Exit-Gruende sind trade-by-trade identisch
- die Aggregatmetriken stimmen exakt mit dem urspruenglichen V8-Research ueberein

Der neue rollende Test beginnt einen Kalendertag spaeter als der Research-Run vom Vortag (17.08.2023 statt 16.08.2023). In diesem Randbereich lag jedoch kein zusaetzlicher V8-Trade, daher bleiben alle Trades und Resultate identisch.

## Exit-Verteilung reproduziert

### BTC

- `failed_4h_breakout`: 12 Trades, -17.014 USDT
- `stop_loss`: 1 Trade, -4.664 USDT
- `slow_trend_exit`: 6 Trades, +34.220 USDT
- `roi`: 1 Trade, +39.946 USDT

### ETH

- `failed_4h_breakout`: 15 Trades, -25.667 USDT
- `stop_loss`: 1 Trade, -4.703 USDT
- `slow_trend_exit`: 3 Trades, +45.849 USDT
- `roi`: 1 Trade, +40.006 USDT

### SOL

- `failed_4h_breakout`: 10 Trades, -23.688 USDT
- `stop_loss`: 5 Trades, -23.532 USDT
- `slow_trend_exit`: 4 Trades, +11.215 USDT
- `roi`: 2 Trades, +80.130 USDT

## Schlussfolgerung

Dieser zweite-PC-Lauf ist ein starker Reproduzierbarkeitsnachweis fuer den klassischen V8-Backtest: frischer GitHub-Checkout, anderer Windows-Pfad und neuer Laufzeitpunkt erzeugen trade-by-trade dieselben Resultate wie der zuvor gesicherte V8-Research.

Das aendert den Freigabestatus nicht:

**READY FOR EXTENDED PAPER TEST – NOT READY FOR REAL MONEY.**

Die Reproduktion bestaetigt die deterministische klassische Backtest-Pipeline, ersetzt aber weder einen ausreichend langen unveraenderten Paper-Forward-Test noch den spaeter geplanten historischen Live-Replay.
