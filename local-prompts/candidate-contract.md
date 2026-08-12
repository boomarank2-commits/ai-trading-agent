# Candidate artifact contract

An isolated strategy-creation cycle writes a new, uniquely named pair below
`output/candidates/`. After review, a human may copy the pair into
`runtime/user_data/strategies/candidates/`:

```text
<slug>.py
<slug>.candidate.json
```

Never overwrite an existing pair. The Python file must expose exactly one new Freqtrade strategy
class and follow the guarded local runtime contract. The JSON object must contain:

```json
{
  "schema_version": 1,
  "name": "unique strategy-version name",
  "strategy_class": "PythonClassName",
  "role": "source upstream role filename",
  "hypothesis": "falsifiable hypothesis",
  "mechanism": "why the edge might exist",
  "major_change": "the one change from its parent/baseline",
  "parent_version_id": null,
  "timeframe": "1h",
  "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
  "research_timerange": "YYYYMMDD-YYYYMMDD",
  "validation_timerange": "YYYYMMDD-YYYYMMDD",
  "holdout_label": "quarantined-v1",
  "fee_ratio": 0.001,
  "slippage_ratio": 0.001
}
```

Do not include secrets, account details, API output, or holdout observations. Do not set a lifecycle
state in the manifest; only the deterministic registry controls lifecycle.
