# Local Binance research and execution layer

German setup and current validation status: [`START_HERE_DE.md`](START_HERE_DE.md).

This repository starts with the MIT-licensed prompt and research layer from
[`DaviddTech/ai-trading-agent`](https://github.com/DaviddTech/ai-trading-agent).
The local registry, Freqtrade integration, Binance configuration, and execution safeguards are
independent additions. They are not part of, affiliated with, or endorsed by Trader Dev or
DaviddTech.

The original project is a research desk, not a live-trading bot. This extension preserves that
boundary:

```text
DaviddTech research roles
        -> candidate Python strategy
        -> immutable candidate version + trial ledger
        -> backtest / lookahead / recursive / holdout checks
        -> byte-identical promoted version reset to IDEA
        -> repeat all gates through paper and explicit human promotion
        -> deterministic Freqtrade execution on Binance Spot
```

Live trading is disabled and no strategy hash is currently approved for live use. The initial risk policy is long-only Binance Spot, 1x,
250 USDT maximum bot capital, no more than three simultaneous 80 USDT positions, no DCA, no
martingale, and no futures or margin. Backtests and video claims are not guarantees of future
returns.

Two independent strategy attempts are recorded and both were rejected on negative train and
holdout results. Research and dry-run infrastructure are usable; real-money entries remain absent.

See [`docs/LOCAL_ARCHITECTURE.md`](docs/LOCAL_ARCHITECTURE.md),
[`docs/LOCAL_VALIDATION.md`](docs/LOCAL_VALIDATION.md), and
[`docs/REGISTRY_WORKFLOW_DE.md`](docs/REGISTRY_WORKFLOW_DE.md) for the complete
setup and safety gates. Runtime commands are documented in
[`runtime/README.md`](runtime/README.md).
