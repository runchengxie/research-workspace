# HK Research Lane Template

This template is a synthetic-only staging shape for an independent 港股 research lane. It does not contain licensed market data, provider cache, credentials, broker adapters, or execution audit logs.

The smoke workflow demonstrates the intended closed loop:

```text
synthetic fixtures -> universe/features -> signals -> positions -> targets.json
```

Real 中国香港市场 data production remains owned by `market-data-platform`. Execution remains owned by `quant-execution-engine`; this template only writes the standard target file shape.

## Smoke

```bash
python scripts/run_smoke.py --out-dir samples
```
