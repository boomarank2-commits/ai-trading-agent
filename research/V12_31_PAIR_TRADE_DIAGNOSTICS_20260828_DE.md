# Pair-lokale Trade-Diagnose

Strategie-Hash: `e13a324560a4941350edd30b53e69ed6286eeb77f2b31673a859c3144e8965d5`

| Pair | P/L | Trades | PF | Top-1 Gewinner | MFE Ø | MAE Ø | Dauer Ø | Zusatzblöcke |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BCH/USDT | +18.43 | 20 | 1.39 | 60.6 % | 10.5 % | -3.6 % | 157.9 h | 0 |
| BNB/USDT | +17.82 | 18 | 1.66 | 59.8 % | 10.1 % | -2.1 % | 217.2 h | 0 |
| BTC/USDT | +163.27 | 15 | 8.31 | 34.6 % | 9.7 % | -2.6 % | 348.2 h | 11 |
| DOGE/USDT | +106.48 | 25 | 2.80 | 24.2 % | 16.4 % | -3.6 % | 104.9 h | 0 |
| ETH/USDT | +136.03 | 44 | 2.38 | 51.1 % | 4.8 % | -2.2 % | 93.2 h | 32 |
| LINK/USDT | +62.73 | 30 | 1.63 | 73.9 % | 5.2 % | -3.4 % | 72.4 h | 11 |
| LTC/USDT | -45.01 | 18 | 0.00 | 0.0 % | 4.3 % | -3.5 % | 56.2 h | 0 |
| SOL/USDT | +9.87 | 24 | 1.20 | 68.5 % | 12.8 % | -3.2 % | 190.5 h | 0 |
| TRX/USDT | +15.23 | 5 | 2.53 | 100.0 % | 8.3 % | -3.8 % | 358.1 h | 1 |
| XRP/USDT | +92.73 | 19 | 3.95 | 32.3 % | 12.2 % | -2.2 % | 67.0 h | 0 |

## Block-Attribution

Die Werte teilen den realisierten Exit proportional auf die Entry-Fills auf. Sie sind eine Buchhaltungsattribution, kein gemeinsames Wallet-Gegenexperiment: Das Entfernen eines Blocks kann die spätere Slot- und Protection-Chronologie verändern.

- BTC/USDT: 11 spätere Fills erzielten zusammen +92.95 USDT.
- ETH/USDT: 32 spätere Fills erzielten zusammen +79.99 USDT.
- LINK/USDT: 11 spätere Fills erzielten zusammen +54.40 USDT.
- TRX/USDT: 1 spätere Fills erzielten zusammen +7.28 USDT.

## BCH/USDT

- Exit-Gründe: `{"force_exit": {"trades": 1, "profit_usdt": 9.8633}, "roi": {"trades": 1, "profit_usdt": 39.8998}, "stop_loss": {"trades": 5, "profit_usdt": -23.4713}, "v12_31_bch_ema30_80_exit": {"trades": 13, "profit_usdt": -7.8611}}`
- Entry-Familien: `{"v12_31_bch_ema30_80_trend": {"trades": 20, "profit_usdt": 18.4306}}`
- Eröffnungsjahre: `{"2023": {"trades": 3, "profit_usdt": 0.4366}, "2024": {"trades": 6, "profit_usdt": 34.76}, "2025": {"trades": 7, "profit_usdt": -25.645}, "2026": {"trades": 4, "profit_usdt": 8.8791}}`
- Block-Attribution: `{"chunk_1": {"fills": 20, "positive_fills": 6, "profit_usdt": 18.4306, "average_profit_usdt": 0.9215, "slot_hours": 3158.77}}`

## BNB/USDT

- Exit-Gründe: `{"stop_loss": {"trades": 2, "profit_usdt": -9.362}, "trailing_stop_loss": {"trades": 1, "profit_usdt": 3.9705}, "v12_17_bnb_failed_breakout": {"trades": 11, "profit_usdt": -17.605}, "v12_17_slow_trend_exit": {"trades": 4, "profit_usdt": 40.8173}}`
- Entry-Familien: `{"v12_17_bnb_champion_donchian": {"trades": 18, "profit_usdt": 17.8208}}`
- Eröffnungsjahre: `{"2023": {"trades": 2, "profit_usdt": 6.6203}, "2024": {"trades": 7, "profit_usdt": 15.783}, "2025": {"trades": 6, "profit_usdt": -0.3842}, "2026": {"trades": 3, "profit_usdt": -4.1983}}`
- Block-Attribution: `{"chunk_1": {"fills": 18, "positive_fills": 5, "profit_usdt": 17.8208, "average_profit_usdt": 0.99, "slot_hours": 3910.48}}`

## BTC/USDT

- Exit-Gründe: `{"v12_17_btc_failed_breakout": {"trades": 2, "profit_usdt": -2.2915}, "v12_17_btc_reclaim_failed": {"trades": 6, "profit_usdt": -7.0968}, "v12_17_btc_reclaim_time_stop": {"trades": 2, "profit_usdt": -1.5589}, "v12_17_slow_trend_exit": {"trades": 5, "profit_usdt": 174.2219}}`
- Entry-Familien: `{"v12_17_btc_champion_donchian": {"trades": 6, "profit_usdt": 111.2939}, "v12_17_btc_trend_reclaim": {"trades": 9, "profit_usdt": 51.9808}}`
- Eröffnungsjahre: `{"2023": {"trades": 1, "profit_usdt": 60.6365}, "2024": {"trades": 6, "profit_usdt": 114.9303}, "2025": {"trades": 4, "profit_usdt": -6.9948}, "2026": {"trades": 4, "profit_usdt": -5.2974}}`
- Block-Attribution: `{"chunk_1": {"fills": 15, "positive_fills": 4, "profit_usdt": 70.3293, "average_profit_usdt": 4.6886, "slot_hours": 5223.27}, "chunk_2": {"fills": 6, "positive_fills": 3, "profit_usdt": 49.9628, "average_profit_usdt": 8.3271, "slot_hours": 4174.88}, "chunk_3": {"fills": 5, "positive_fills": 3, "profit_usdt": 42.9827, "average_profit_usdt": 8.5965, "slot_hours": 3720.25}}`

## DOGE/USDT

- Exit-Gründe: `{"roi": {"trades": 2, "profit_usdt": 80.0617}, "stop_loss": {"trades": 11, "profit_usdt": -51.7334}, "v12_30_doge_supertrend_exit": {"trades": 12, "profit_usdt": 78.1471}}`
- Entry-Familien: `{"v12_30_doge_supertrend20x3": {"trades": 25, "profit_usdt": 106.4754}}`
- Eröffnungsjahre: `{"2023": {"trades": 3, "profit_usdt": 2.9487}, "2024": {"trades": 12, "profit_usdt": 83.6887}, "2025": {"trades": 5, "profit_usdt": 13.7275}, "2026": {"trades": 5, "profit_usdt": 6.1104}}`
- Block-Attribution: `{"chunk_1": {"fills": 25, "positive_fills": 11, "profit_usdt": 106.4754, "average_profit_usdt": 4.259, "slot_hours": 2622.53}}`

## ETH/USDT

- Exit-Gründe: `{"force_exit": {"trades": 1, "profit_usdt": -0.1892}, "roi": {"trades": 1, "profit_usdt": 120.0652}, "v12_17_eth_failed_breakout": {"trades": 6, "profit_usdt": -22.0139}, "v12_17_eth_reclaim_failed": {"trades": 25, "profit_usdt": -41.3043}, "v12_17_eth_reclaim_time_stop": {"trades": 7, "profit_usdt": -26.572}, "v12_17_slow_trend_exit": {"trades": 4, "profit_usdt": 106.0404}}`
- Entry-Familien: `{"v12_17_eth_champion_donchian": {"trades": 10, "profit_usdt": 188.8335}, "v12_17_eth_trend_reclaim": {"trades": 34, "profit_usdt": -52.8073}}`
- Eröffnungsjahre: `{"2023": {"trades": 4, "profit_usdt": 46.7184}, "2024": {"trades": 18, "profit_usdt": 74.2581}, "2025": {"trades": 9, "profit_usdt": 39.8231}, "2026": {"trades": 13, "profit_usdt": -24.7735}}`
- Block-Attribution: `{"chunk_1": {"fills": 44, "positive_fills": 7, "profit_usdt": 56.0404, "average_profit_usdt": 1.2736, "slot_hours": 4101.88}, "chunk_2": {"fills": 19, "positive_fills": 4, "profit_usdt": 37.9671, "average_profit_usdt": 1.9983, "slot_hours": 3607.28}, "chunk_3": {"fills": 13, "positive_fills": 4, "profit_usdt": 42.0187, "average_profit_usdt": 3.2322, "slot_hours": 3431.42}}`

## LINK/USDT

- Exit-Gründe: `{"force_exit": {"trades": 1, "profit_usdt": 38.8635}, "roi": {"trades": 1, "profit_usdt": 120.2001}, "stop_loss": {"trades": 1, "profit_usdt": -4.7011}, "trailing_stop_loss": {"trades": 3, "profit_usdt": -37.5529}, "v12_17_link_failed_breakout": {"trades": 23, "profit_usdt": -57.6252}, "v12_17_slow_trend_exit": {"trades": 1, "profit_usdt": 3.5429}}`
- Entry-Familien: `{"v12_17_link_champion_donchian": {"trades": 30, "profit_usdt": 62.7272}}`
- Eröffnungsjahre: `{"2023": {"trades": 7, "profit_usdt": 102.7869}, "2024": {"trades": 12, "profit_usdt": -27.7802}, "2025": {"trades": 7, "profit_usdt": -33.5437}, "2026": {"trades": 4, "profit_usdt": 21.2642}}`
- Block-Attribution: `{"chunk_1": {"fills": 30, "positive_fills": 3, "profit_usdt": 8.3262, "average_profit_usdt": 0.2775, "slot_hours": 2170.95}, "chunk_2": {"fills": 7, "positive_fills": 3, "profit_usdt": 37.9163, "average_profit_usdt": 5.4166, "slot_hours": 1766.6}, "chunk_3": {"fills": 4, "positive_fills": 1, "profit_usdt": 16.4847, "average_profit_usdt": 4.1212, "slot_hours": 1195.28}}`

## LTC/USDT

- Exit-Gründe: `{"stop_loss": {"trades": 3, "profit_usdt": -14.1102}, "v12_17_ltc_failed_breakout": {"trades": 12, "profit_usdt": -24.3126}, "v12_17_slow_trend_exit": {"trades": 3, "profit_usdt": -6.5921}}`
- Entry-Familien: `{"v12_17_ltc_champion_donchian": {"trades": 18, "profit_usdt": -45.0149}}`
- Eröffnungsjahre: `{"2023": {"trades": 2, "profit_usdt": -3.4758}, "2024": {"trades": 9, "profit_usdt": -24.395}, "2025": {"trades": 5, "profit_usdt": -11.7457}, "2026": {"trades": 2, "profit_usdt": -5.3983}}`
- Block-Attribution: `{"chunk_1": {"fills": 18, "positive_fills": 0, "profit_usdt": -45.0149, "average_profit_usdt": -2.5008, "slot_hours": 1011.05}}`

## SOL/USDT

- Exit-Gründe: `{"force_exit": {"trades": 1, "profit_usdt": 1.8522}, "roi": {"trades": 1, "profit_usdt": 40.0805}, "stop_loss": {"trades": 4, "profit_usdt": -18.8136}, "trailing_stop_loss": {"trades": 3, "profit_usdt": 12.0259}, "v12_17_slow_trend_exit": {"trades": 3, "profit_usdt": 0.8725}, "v12_17_sol_failed_breakout": {"trades": 12, "profit_usdt": -26.1445}}`
- Entry-Familien: `{"v12_17_sol_champion_donchian": {"trades": 24, "profit_usdt": 9.873}}`
- Eröffnungsjahre: `{"2023": {"trades": 4, "profit_usdt": 43.3976}, "2024": {"trades": 10, "profit_usdt": -20.7175}, "2025": {"trades": 6, "profit_usdt": -5.8843}, "2026": {"trades": 4, "profit_usdt": -6.9228}}`
- Block-Attribution: `{"chunk_1": {"fills": 24, "positive_fills": 6, "profit_usdt": 9.873, "average_profit_usdt": 0.4114, "slot_hours": 4571.13}}`

## TRX/USDT

- Exit-Gründe: `{"stop_loss": {"trades": 1, "profit_usdt": -4.6919}, "v12_17_slow_trend_exit": {"trades": 1, "profit_usdt": 25.2168}, "v12_17_trx_failed_breakout": {"trades": 3, "profit_usdt": -5.2906}}`
- Entry-Familien: `{"v12_17_trx_champion_donchian": {"trades": 5, "profit_usdt": 15.2343}}`
- Eröffnungsjahre: `{"2023": {"trades": 1, "profit_usdt": 25.2168}, "2024": {"trades": 1, "profit_usdt": -3.282}, "2025": {"trades": 1, "profit_usdt": -1.1189}, "2026": {"trades": 2, "profit_usdt": -5.5816}}`
- Block-Attribution: `{"chunk_1": {"fills": 5, "positive_fills": 1, "profit_usdt": 7.9511, "average_profit_usdt": 1.5902, "slot_hours": 1790.37}, "chunk_2": {"fills": 1, "positive_fills": 1, "profit_usdt": 7.2832, "average_profit_usdt": 7.2832, "slot_hours": 672.0}}`

## XRP/USDT

- Exit-Gründe: `{"roi": {"trades": 3, "profit_usdt": 120.0711}, "v12_17_slow_trend_exit": {"trades": 2, "profit_usdt": 1.9028}, "v12_17_xrp_failed_breakout": {"trades": 14, "profit_usdt": -29.2412}}`
- Entry-Familien: `{"v12_17_xrp_champion_donchian": {"trades": 19, "profit_usdt": 92.7326}}`
- Eröffnungsjahre: `{"2023": {"trades": 1, "profit_usdt": -2.1698}, "2024": {"trades": 9, "profit_usdt": 64.251}, "2025": {"trades": 6, "profit_usdt": 36.4188}, "2026": {"trades": 3, "profit_usdt": -5.7674}}`
- Block-Attribution: `{"chunk_1": {"fills": 19, "positive_fills": 4, "profit_usdt": 92.7326, "average_profit_usdt": 4.8807, "slot_hours": 1273.15}}`
