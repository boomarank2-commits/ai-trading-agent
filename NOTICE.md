# Notices and dependency boundaries

The original prompt and research material is derived from
[`DaviddTech/ai-trading-agent`](https://github.com/DaviddTech/ai-trading-agent) at commit
`11ac32173cdd993af517265cac502e5d914c997d` and remains covered by its MIT license and retained
copyright notice.

The local files under `src/local_trader/`, `runtime/`, `local-prompts/`, `research/`, and the
corresponding tests are independent additions. They do not contain Trader Dev server code and are
not affiliated with or endorsed by DaviddTech, Trader Dev, Binance, or Freqtrade.

Freqtrade is an external, separately installed dependency. It is not copied into this repository.
Freqtrade is distributed under GPL-3.0; consult its own repository and license before distributing
a combined runtime image or derivative work. Binance names and marks belong to their respective
owners.

This software is provided for research and engineering purposes. It cannot guarantee profit, and
historical, simulated, or paper-trading results do not predict future performance.
