# Upstream provenance

The original research/prompt layer in this repository was cloned from:

- Repository: <https://github.com/DaviddTech/ai-trading-agent>
- Upstream commit: `11ac32173cdd993af517265cac502e5d914c997d`
- Upstream license: MIT; the original `LICENSE` and copyright notice are retained.

The upstream project described an AI research workflow backed by the proprietary Trader Dev MCP
service. It did not contain this backtest engine or a live order executor. This focused fork keeps
only the `loop/` role files still referenced by `research/desk.json`; unused upstream README,
skill/prompt/example packages, contribution material, and promotional documentation were removed
in the repository cleanup. The original license, copyright notice, commit reference, and this
provenance record remain intact.

## Local additions

The following are independent local components and are not upstream Trader Dev functionality:

- `src/local_trader/`: immutable strategy registry, evaluation ledger, promotion gates, and CLI.
- `runtime/`: pinned Freqtrade runtime, Binance Spot configuration, candidate strategy, and scripts.
- `local-prompts/`: overlays that adapt the research discipline from Pine/Bybit to Python/Binance.
- `tests/`: local safety and regression tests.

No Trader Dev server code, private database, strategy catalog, credentials, or proprietary service
implementation is copied here. "Production candidate" in an upstream prompt never means automatic
live deployment locally. Human approval and all local promotion gates still apply.

