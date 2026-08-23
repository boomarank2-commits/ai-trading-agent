# Local AI trading desk instructions

This repository contains a focused local runtime plus the retained upstream role
files that are still used by the disabled offline Research Desk.

## Current authoritative plan

`RESEARCH_MASTERPLAN_DE.md` is the **authoritative project and research plan**.

Older Codex phase briefs, historical chat notes and archived research documents are context only. If they conflict with `RESEARCH_MASTERPLAN_DE.md`, the masterplan wins.

The current rule is deliberately conservative:

- V8 / `CompressionBreakout250` remains the frozen champion.
- Do not mix Bollinger, Ichimoku, ORB/FVG/BOS or new filters directly into V8.
- Diagnostics and observability may be added without changing decisions.
- Any strategy change requires a separate `research/...` challenger branch and a new experiment/version/hash.
- Respect the phase ordering in the masterplan. Do not skip replay/parity, execution realism, red-team coverage, diagnostics or meta-research gates because a new strategy idea looks attractive.
- The long-term strategy state model is `TREND/BREAKOUT`, `RANGE/MEAN_REVERSION`, or `NO_TRADE`.
- `NO_TRADE` is the default when data quality, regime, signal or risk approval is uncertain.

Runtime clarification (2026-08-24): V8 is the frozen research champion stored
under `research/baselines/V8/`; it is not the file currently loaded by
`STARTBOT.bat`. The active, separately registered paper/dry-run candidate is
`CompressionBreakout250` V12.19. Read
`research/V12_19_PERSISTENT_PAIR_LEARNING_DE.md` before modifying it. V12.19 is
not a real-money promotion and its full ten-pair financial matrix is pending.

## Preserve provenance and used upstream roles

Treat these paths as read-only source/provenance material unless the human
explicitly asks to update the upstream snapshot:

- `LICENSE`, `NOTICE.md`, `docs/UPSTREAM.md`
- role files under `loop/` that are referenced by `research/desk.json`

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

## Hot path / cold path boundary

The production-facing hot path is deterministic:

`market data -> normalization -> features -> data-quality gate -> regime -> strategy -> portfolio/risk -> execution/OMS -> reconciliation`

LLMs, Codex, Hermes/OpenClaw-style agents and research jobs belong to the cold path only. They may analyze logs, propose a falsifiable hypothesis, create a separate candidate and request tests. They may not directly mutate active strategy/risk parameters or submit exchange orders.

The current autonomous Research Desk stays fail-closed disabled until it runs under a genuinely isolated low-privilege account/VM/container that cannot read the real holdout or credentials.

## V8 freeze contract

The current LF-normalized V8 SHA-256 is:

`9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280`

Changing `runtime/user_data/strategies/CompressionBreakout250.py` means the result is no longer the validated V8 baseline. A new strategy version, hash and full research gate are required.

B1 (`volume_ratio >= 1.00`) is documented as rejected as a global filter. B2 (`>= 1.25`) is paused until the replay/diagnostic gates are completed. Do not invent another threshold after seeing B1/B2.

## Deep-Research challenger families

The source reports differ in which trend component they emphasize. Preserve that disagreement instead of silently choosing one:

- ORB-Retest is a standalone trend/breakout challenger family.
- Ichimoku is a separate standalone trend challenger family.
- Bollinger Mean Reversion is the standalone range/mean-reversion family.
- A regime router/hybrid is later work and may only combine components that were separately validated.
- FVG and BOS/Reversal are later extensions, not part of the first ORB baseline.

Implementation order is not a ranking. ORB and Ichimoku must be compared with pre-registered OOS evidence before either is selected as the later trend engine.

## Research discipline

- One falsifiable hypothesis and one major strategy change per version.
- Closed-candle OHLCV data only; no lookahead or repainting.
- Include fees and realistic execution/cost assumptions.
- Validate across multiple symbols, time windows, 1m detail, cost stress, lookahead/causality and recursive-indicator analysis where relevant.
- New challengers require development/validation/holdout separation and Walk-Forward evidence before promotion.
- Persist failed trials as well as wins.
- Do not tune after seeing details from a quarantined holdout.
- Trial Ledger, PBO and Deflated Sharpe are research diagnostics, not profit guarantees.
- Measure parameter plateaus, 1-bar-lag stress, PnL concentration, MAE/MFE and drawdown/time-under-water where data supports them.
- A challenger can only progress after deterministic replay checks and fresh Shadow/Forward evidence.
- AI/LLM work belongs in the research plane. Risk, OMS, execution and reconciliation stay deterministic.

## Required order before new alpha work

1. Full-system replay + data integrity.
2. Checkpoint/restart determinism.
3. Paper-vs-replay parity.
4. Close the realistic execution/cost gaps: spread, latency assumptions, partial-fill/cancel/reconciliation behavior or explicitly conservative substitutes.
5. Complete the Deep-Research red-team/fault matrix or keep every uncovered scenario explicitly marked as missing.
6. Failed-breakout/volume/regime diagnostics with V8 unchanged.
7. Trial-ledger/Walk-Forward/PBO/DSR/plateau evidence.
8. Only then standalone strategy challengers: ORB-Retest, Bollinger MR and Ichimoku as separate experiment families.
9. Only after component validation may a `TREND/BREAKOUT` / `RANGE/MEAN_REVERSION` / `NO_TRADE` router be tested.

Never describe a partial execution simulator, partial fault matrix, disabled research agent, or unimplemented challenger as complete. `docs/DEEP_RESEARCH_GAP_AUDIT_DE.md` is the explicit Soll/Ist ledger for these gaps.

Run the narrowest relevant tests after changes and keep generated market data, databases, logs, replay results, reports, credentials, and promoted live artifacts out of Git.
