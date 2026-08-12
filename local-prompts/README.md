# Local research overlays

These overlays adapt the upstream DaviddTech research discipline to the local Python/Freqtrade
runtime. They supplement rather than replace the original prompts.
They are templates for a future externally isolated runner; autonomous same-user execution in this
checkout is hard-disabled.

Every local research cycle must:

1. Read the relevant upstream role and this directory's `research-cycle.md`.
2. Produce exactly one candidate or one audit; change one major idea at a time.
3. Use only OHLCV-derived, closed-candle information available to Freqtrade.
4. Freeze and hash the candidate before evaluation. Isolated agents never write
   the local SQLite ledger; reviewed results may be imported by a human.
5. Run the validation commands and report failures honestly.
6. Never edit a promoted artifact or live configuration.
7. Never read API credentials or place orders.
8. Never access the quarantined holdout; it is evaluated outside the research agent.

The local runtime is Binance Spot long-only. Any upstream suggestion involving shorts, leverage,
margin, futures, funding rates, sentiment feeds, DCA, Kelly leverage, or martingale is research-only
and must not enter this runtime.
