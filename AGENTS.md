# Local AI trading desk instructions

This repository contains an upstream prompt layer plus an independent local runtime.

## Current authoritative plan

`RESEARCH_MASTERPLAN_DE.md` is the **authoritative project and research plan**.

Older Codex phase briefs, historical chat notes and archived research documents are context only. If they conflict with `RESEARCH_MASTERPLAN_DE.md`, the masterplan wins.

The current rule is deliberately conservative:

- V8 / `CompressionBreakout250` remains the frozen champion.
- Do not mix Bollinger, Ichimoku, ORB/FVG/BOS or new filters directly into V8.
- Diagnostics and observability may be added without changing decisions.
- Any strategy change requires a separate `research/...` challenger branch and a new experiment/version/hash.
- Respect the phase ordering in the masterplan. Do not skip replay/parity, diagnostics and meta-research gates just because a new strategy idea looks attractive.

## Preserve upstream

Treat these paths as read-only upstream source material unless the human explicitly asks to update the upstream snapshot:

- `README.md`, `SKILL.md`, `LICENSE`, `CONTRIBUTING.md`
- `skills/`, `prompts/`, `loop/`, `examples/`
- upstream documentation under `docs/`, except repository-owned local/research documentation

Put local work in `src/local_trader/`, `runtime/`, `local-prompts/`, `research/`, and `tests/`.

## Hard safety boundary

- Research agents never place orders, start live trading, edit live credentials, or read secret files/environment variables.
- Binance is Spot/USDT, long-only, 1x. Futures, margin, shorts, DCA, and martingale are forbidden.
- Risk ceilings may only be lowered by an agent, never increased: 250 USDT capital, 80 USDT per position, 240 USDT total open exposure, and three open positions.
- `dry_run` remains true unless the human invokes the documented, Registry-authorized recovery launcher. That launcher remains `paused` and cannot enable real-money entries.
- CANARY and PRODUCTION promotions require explicit human approval through the deterministic CLI.
- Registry promotion never makes generated Python trusted. Live recovery additionally requires an independent manual source audit for the exact hash in `runtime/trusted-live-artifacts.json`.
- Candidate strategies are immutable after registration. Create a new version instead of editing a registered artifact.
- Never copy exchange secrets into code, config, tests, logs, reports, prompts, or chat output.
- No automatic capital scaling from 250 to 500/750/1000 USDT.

## V8 freeze contract

The current LF-normalized V8 SHA-256 is:

`9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280`

Changing `runtime/user_data/strategies/CompressionBreakout250.py` means the result is no longer the validated V8 baseline. A new strategy version, hash and full research gate are required.

B1 (`volume_ratio >= 1.00`) is documented as rejected as a global filter. B2 (`>= 1.25`) is paused until the replay/diagnostic gates are completed. Do not invent another threshold after seeing B1/B2.

## Research discipline

- One falsifiable hypothesis and one major strategy change per version.
- Closed-candle OHLCV data only; no lookahead or repainting.
- Include fees and realistic slippage assumptions.
- Validate across multiple symbols, time windows, 1m detail, cost stress, lookahead/causality and recursive-indicator analysis where relevant.
- Persist failed trials as well as wins.
- Do not tune after seeing details from a quarantined holdout.
- Trial Ledger, PBO and Deflated Sharpe are research diagnostics, not profit guarantees.
- A challenger can only progress after deterministic replay checks and fresh Shadow/Forward evidence.
- AI/LLM work belongs in the research plane. Risk and execution stay deterministic.

## Required order before new alpha work

1. Full-system replay + data integrity.
2. Checkpoint/restart determinism.
3. Paper-vs-replay parity.
4. Failed-breakout/volume/regime diagnostics with V8 unchanged.
5. Trial-ledger/PBO/DSR/plateau evidence.
6. Only then new standalone challengers, with Bollinger mean reversion ahead of Ichimoku/ORB ideas.

Run the narrowest relevant tests after changes and keep generated market data, databases, logs, replay results, reports, credentials, and promoted live artifacts out of Git.
