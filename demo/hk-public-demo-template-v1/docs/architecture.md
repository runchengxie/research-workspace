# Architecture

```text
fixtures/synthetic_prices.csv
        |
        v
src/hk_strategy_demo/pipeline.py
  rank synthetic trailing returns
  select top symbols
        |
        +--> samples/summary.json
        |
        +--> samples/targets.json
```

The demo deliberately omits data-provider adapters, historical market data,
broker credentials, private artifacts, and production execution code.
