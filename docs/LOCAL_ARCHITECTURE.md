# Local architecture and rollout gates

## What is reproduced

The public DaviddTech project describes a persistent research loop: propose a
hypothesis, implement one major change, backtest, diagnose, test robustness,
record the failure or success, and repeat. It is not a published profitable
strategy or an executable exchange backend.

This repository preserves that research model while replacing the unavailable
Trader Dev backend with pinned Freqtrade 2026.7, an append-only local registry,
an order-free MCP server, and a prepared but hard-disabled Codex scheduler
prototype.

## Trust boundaries

```text
Untrusted research plane (future external runner; disabled here)
  low-privilege VM/container + staging workspace
  candidate Python + report
  public OHLCV / no exchange key
              |
              v human review/import
Deterministic evidence plane
  immutable candidate SHA-256 + evidence
  byte-identical promoted version reset to IDEA
  stage-specific metrics and provenance
  holdout -> shadow -> paper -> canary evidence
  one-time TTY human approvals
              |
              v separate source audit
Paused execution plane
  exact in-memory strategy loader
  frozen config + dependency hashes
  exclusive instance lock + entry kill-switch
  Binance Spot key / no AI or MCP order tool
```

Autonomous scheduler execution is hard-disabled. Although its workspace sandbox
would prevent canonical writes, it would not prevent a same-user process from
reading the host repository, holdout, or home directory. It may only be enabled
inside a separately provisioned low-privilege VM/container with staged inputs
and a host-controlled result channel. The MCP server can research and record
evidence but rejects CANARY/PRODUCTION operations and exposes no exchange or
process-start capability.

## Why metrics are not enough

A Freqtrade strategy is arbitrary Python. Even code with safe-looking class
constants could override callbacks or call a network API directly. Therefore a
positive backtest and Registry promotion never automatically grant exchange
credentials.

Live recovery requires a second exact-hash source audit in
`runtime/trusted-live-artifacts.json`. The list is currently empty. The locked
bootstrap reads and hashes one already-open source file, compiles those exact
bytes in memory, and replaces Freqtrade's directory resolver. Adjacent
parameter JSON and competing strategy files are not loaded.

This is a local operational boundary, not protection against an attacker who
already controls the Windows user or can replace the repository, Python
environment, database, or launcher. File ownership/ACLs and a dedicated
Binance account remain necessary. A future system that executes unreviewed
generated code would require a separate privileged order service enforcing the
risk envelope server-side.

## Risk envelope

- Binance Spot and USDT only.
- Pairs: BTC/USDT, ETH/USDT, SOL/USDT.
- Maximum capital: 250 USDT.
- Maximum stake: 80 USDT.
- Maximum concurrent positions: 3.
- Maximum aggregate exposure: 240 USDT.
- Maximum realized daily loss before new-entry lock: 10 USDT.
- Maximum allowed evaluation drawdown: 15%.
- Long-only, 1x; no margin, futures, short, DCA, or martingale.
- Dry-run starts `stopped`; live recovery starts and remains `paused`.

Software configuration is not an exchange-side spending limit. Real operation
requires a dedicated account/subaccount containing no more than the intended
250 USDT and a key limited to read + Spot trading, without withdrawals,
transfers, margin, or futures, ideally with an IP allowlist.

## Evidence order

Candidate evidence is useful for deciding whether an exact source artifact is
worth a deployment review. Copying those same bytes to the promoted root creates
a separate version at `IDEA`; all gates below must then be passed again for that
specific promoted version. Evidence and approvals are never inherited across
the handoff.

1. RESEARCH: in-sample/backtest development.
2. VALIDATED: new BACKTEST/VALIDATION/OUT_OF_SAMPLE evidence with at least 100
   trades, two symbols, two timeframes, every slice profitable, per-slice
   profit factor >= 1.2, drawdown <= 15%, and daily loss <= 10 USDT.
3. HOLDOUT_PASSED: new positive HOLDOUT evidence collected only in VALIDATED.
4. SHADOW: enter after the passed holdout; then collect new SHADOW evidence.
5. PAPER: enter using SHADOW evidence; then collect new PAPER evidence.
6. CANARY: enter using PAPER evidence plus TTY and exact one-time human
   approval; then collect genuine CANARY evidence.
7. PRODUCTION: enter using new CANARY evidence and a second exact human
   approval.

Evidence IDs and dataset hashes are deduplicated when supplied, and exact
duplicate rows are rejected. A stage only consumes new, appropriate evidence
since the preceding promotion; the same self-reported rows cannot be replayed
through the lifecycle. These provenance fields are not signatures, and the
current local caller can omit them, so raw-data review remains necessary.

## Current operating invariant

No existing strategy passed the holdout. No artifact is registered, promoted,
or source-approved. Research and simulated integration are available;
real-money entries are not implemented or enabled.
