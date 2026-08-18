# Local Binance research and execution layer

German start point and current project status: [`START_HERE_DE.md`](START_HERE_DE.md).

This repository extends the MIT-licensed prompt/research layer from `DaviddTech/ai-trading-agent` with an independent local Freqtrade/Binance research and dry-run execution layer. The local runtime is not affiliated with or endorsed by the upstream project.

## Current local state

- Development branch: `agent/v12-adaptive-league`.
- V12 is research infrastructure for pair-/family-specific candidate search.
- The strategy currently loaded by the testbot is still `CompressionBreakout250` / V11.
- BTC, ETH and SOL are evaluated pair-locally; no BTC regime is injected into ETH/SOL decisions.
- Binance Spot, long-only, 1x, dry-run only.
- 250 USDT virtual capital, max. 80 USDT per position, max. three positions / 240 USDT exposure.
- No futures, margin, shorts, leverage, DCA, martingale or automatic real-money promotion.

Historical V8/V9/V10/V11 results remain research evidence and trial history. They are not parallel active roadmaps.

## Research flow

```text
market data
→ deterministic features / data quality
→ pair-local regime / candidate family
→ risk / execution
→ telemetry
→ offline research
→ Development / Validation / Blind / Walk-Forward
→ cost and robustness checks
→ explicit candidate promotion
→ exact local Freqtrade verification
```

AI/LLM research remains outside the synchronous order path. A backtest or research winner is not automatically promoted to the active bot.

Authoritative local project documents:

- [`RESEARCH_MASTERPLAN_DE.md`](RESEARCH_MASTERPLAN_DE.md)
- [`docs/DEEP_RESEARCH_GAP_AUDIT_DE.md`](docs/DEEP_RESEARCH_GAP_AUDIT_DE.md)
- [`research/trial_ledger.csv`](research/trial_ledger.csv)
- [`runtime/README.md`](runtime/README.md)

Live trading remains disabled unless a future, separately reviewed lifecycle explicitly changes that status.
