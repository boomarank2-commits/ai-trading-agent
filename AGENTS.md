# Local AI trading desk instructions

## Current operating context

The current development branch is `agent/v12-adaptive-league`.

V12 is a **research branch**, not a promoted live/paper strategy version. The strategy currently loaded by `STARTBOT.bat` is still `runtime/user_data/strategies/CompressionBreakout250.py` with `STRATEGY_VERSION = "V11"`.

V11 is a deterministic pair-local adaptive router. BTC/USDT, ETH/USDT and SOL/USDT classify only their own 15m/1h/4h data into `TREND/BREAKOUT`, `RANGE/MEAN_REVERSION` or `NO_TRADE`, then route to `ORB_RETEST`, `ICHIMOKU_TREND` or `BOLLINGER_MR`.

V11 is **not assumed profitable or promoted**. V12 research exists to test stronger pair-/family-specific candidates using Development/Validation/Blind and rolling Walk-Forward evidence.

## Authoritative project sources

Use these in this order:

1. `RESEARCH_MASTERPLAN_DE.md` – research/governance framework.
2. `docs/DEEP_RESEARCH_GAP_AUDIT_DE.md` – current technical gap ledger.
3. `research/trial_ledger.csv` – experiment history, including rejected candidates.
4. `runtime/user_data/strategies/CompressionBreakout250.py` – actual strategy source loaded by the bot.
5. V12 research runners under `runtime/` – research-only candidate search, never hot-path self-modification.

Historical V8/V9/V10/V11 documents and baselines are evidence, not parallel active roadmaps. If an old document conflicts with the files above, the current operating context wins.

## Preserve useful history without preserving confusion

- Keep frozen baselines and rejected results when needed for reproducibility, comparison, PBO/DSR and trial accounting.
- Do not keep obsolete status reports or duplicate instructions in the repository root.
- Prefer one current start guide and one current research plan over multiple competing instructions.
- Old PRs/branches may remain as Git history, but they must not be treated as active development paths.

## Hard safety boundary

- Binance Spot / USDT, long-only, 1x.
- No futures, margin, shorts, leverage, DCA or martingale.
- Maximum virtual capital: 250 USDT.
- Maximum stake: 80 USDT per position.
- Maximum total exposure: 240 USDT and at most three open positions.
- No automatic capital scaling.
- No automatic real-money promotion.
- Research agents never receive a free exchange-order path or secret access.
- LLM/AI logic belongs in the cold research path, not the synchronous order path.
- Risk, OMS, execution and reconciliation remain deterministic.

## Pair independence

BTC, ETH and SOL must be evaluated independently unless a separate portfolio-risk test explicitly studies correlation/exposure. Do not inject BTC regime state into ETH or SOL trading decisions.

Pair-specific parameters and even different winning strategy families are allowed when supported by evidence.

## Research discipline

Primary economic objective is robust **net USDT PnL after costs**, not raw trade count or an attractive in-sample curve.

Every candidate must be judged with as much of the following as the data supports:

- fees and additional cost stress;
- Development / Validation / Blind separation;
- rolling Walk-Forward folds;
- pair and time-slice attribution;
- Profit Factor, expectancy and max drawdown;
- trade/family concentration;
- 1-bar-lag or execution-delay sensitivity;
- 1m detail for final Freqtrade verification;
- parameter-neighbour/plateau checks;
- trial ledger accounting, PBO/DSR where appropriate;
- no future leakage or repainting.

Do not optimize repeatedly against the same blind/holdout window and then continue calling it blind. Once a holdout result informs a strategy change, that window is consumed for that experiment lineage.

## V12 family-league intent

The V12 research layer may compare strategy families such as:

- slow breakout / Donchian trend;
- Ichimoku trend;
- Bollinger mean reversion;
- other pre-registered challengers.

A family that looks good only in development but fails validation/blind or reasonable cost stress is rejected or quarantined. `NO_TRADE` is a valid result when no robust edge exists.

The research runners must not silently modify the active V11 strategy while searching. A promoted strategy change requires an explicit new strategy version/hash and a separate verification step.

## Frozen V8 baseline

The validated historical V8 baseline remains preserved under `research/baselines/V8/` with LF-normalized SHA-256:

`9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280`

This is a comparison baseline, not the current active development target. Never rewrite the frozen baseline in place.

## Repository hygiene

Treat upstream/open-source material such as `README.md`, `SKILL.md`, `LICENSE`, `CONTRIBUTING.md`, `skills/`, `prompts/`, `loop/` and `examples/` as upstream unless a task explicitly requires changes there.

Keep generated market data, databases, logs, replay results, backtest exports, credentials and secrets out of Git.

After meaningful changes, run the narrowest relevant tests and keep CI green. Do not delete runtime/test/workflow files merely because their names look old; verify references and purpose first.
