# Local validation record

Validation date: 2026-08-12 (Europe/Berlin)

## Environment and data

- Python 3.12
- Freqtrade 2026.7
- CCXT 4.5.73
- Binance Spot 15-minute OHLCV
- Pairs: BTC/USDT, ETH/USDT, SOL/USDT
- Downloaded candles: 70,145 per pair
- Available range: 2024-08-12 00:00 UTC through 2026-08-12 16:00 UTC
- Starting wallet: 250 USDT
- Maximum concurrent positions: 3
- Stake cap: 80 USDT
- Cost proxy: 0.002 per side, applied on both entry and exit

The public-data overlay sets CCXT's internal `apiKey` to `null`. This works
around CCXT 4.5.73 treating Freqtrade's empty dry-run key as present and trying
one private Binance market-discovery endpoint. The overlay contains no secret,
uses public market endpoints, and is never loaded by the live launcher.

## Baseline result: rejected

Strategy: `CompressionBreakout250`

| Slice | Trades | Net result | Profit factor | Max drawdown | Verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| 2024-08-16 to 2026-08-12 | 217 | -100.539 USDT (-40.22%) | 0.50 | 40.75% | Reject |
| Holdout 2025-08-12 to 2026-08-12 | 77 | -46.149 USDT (-18.46%) | 0.34 | 18.87% | Reject |

The full-period wallet fell from 250 USDT to 149.461 USDT. These results fail
the local requirements of profit factor >= 1.2, drawdown <= 15%, positive
holdout, multiple symbols/timeframes, and at least 100 aggregated trades. The
baseline must not be promoted or started with real money.

## Independent research candidate: rejected

Strategy: `TrendPullback250V1`

The isolated research cycle changed the major signal idea, froze the candidate
before seeing the final holdout, and evaluated the holdout exactly once.

| Slice | Trades | Net result | Profit factor | Max drawdown | Win rate | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Train 2024-08-12 to 2025-08-12 | 183 | -44.760 USDT (-17.90%) | 0.59 | 21.12% | 33.9% | Reject |
| Holdout 2025-08-12 to 2026-08-12 | 143 | -29.284 USDT (-11.71%) | 0.63 | 12.86% | 32.2% | Reject |

All three pairs were negative in both windows. Recursive analysis found no
indicator-only lookahead. The forced-market lookahead run captured too few
trades and is therefore recorded as inconclusive, not passed. Frozen candidate
SHA-256:
`8790d38c0e38cbcd6446207cba3f63d806d6ccb8354330aef740b117a5361827`.

The candidate was not registered or promoted.

## Bias diagnostics

- Lookahead analysis inspected 50 signals and reported no biased entry signal,
  exit signal, or indicator.
- Recursive analysis reported no indicator lookahead. With the configured 400
  startup candles, the largest displayed residual was 0.007% for EMA 200; the
  indicator converged to 0.000% with 1,599 startup candles.
- Static tests also reject negative shifts and centered rolling windows.

Passing a bias diagnostic only means the implementation did not use future
data in the tested way. It does not repair the negative expectancy and is not
evidence of profitability.

## Reproduction commands

```powershell
.\runtime\scripts\download-data.ps1 -Days 730
.\runtime\scripts\backtest.ps1 -Timerange "20240812-"
.\runtime\scripts\backtest.ps1 -Timerange "20250812-20260812"
.\runtime\scripts\lookahead-analysis.ps1 -Timerange "20240812-20260812"
.\runtime\scripts\recursive-analysis.ps1 -Timerange "20240812-20260812"
```

Generated candles, SQLite files, logs, and backtest archives are intentionally
ignored by Git. The figures above are the tracked audit record.

## Current decision

There is no profitable or live-approved artifact. The registry is intentionally
empty and `runtime/trusted-live-artifacts.json` has no approved source hash.
Research may continue, but neither existing strategy is eligible for paper,
canary, production, or real-money entry.
