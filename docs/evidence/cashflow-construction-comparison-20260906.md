# Cashflow construction comparison evidence

**Date:** 2026-09-06  
**Status:** Research-only implementation slice complete

## Implemented

- `quant-platform` public branch `feat/cashflow-index-enhancement`
  - `topk_equal_weight`
  - `topk_benchmark_weight`
  - `benchmark_ml_tilt`
  - `monthly`, `quarterly`, `d11_h5` event generation
  - tracking error, information ratio, turnover, active share and input hash
- `quant-research` private branch `feat/cashflow-index-enhancement`
  - fixed-input cashflow 3 × 3 comparison runner
  - research-only CLI and protocol

## Verification

```text
quant-platform focused comparison/rebalance tests: 33 passed
quant-platform Ruff: passed
quant-research cashflow runner/calendar/construction tests: 21 passed
quant-research changed-file Ruff: passed
```

The private verification used the public worktree source through `PYTHONPATH` so the new public API was tested before publication. The public full-suite baseline remains blocked by the existing optional `torch` dependency in microstructure tests. The private full-suite baseline remains blocked by the existing duplicate test-module/import-mismatch condition. Neither failure occurred in the new tests.

## Interpretation limits

This slice proves the construction and scheduling contracts, not economic alpha. The current runner uses a fixed synthetic or supplied return panel and does not yet add industry/size attribution, transaction costs, or real cash-flow historical replay. D11-H5 keeps one signal vintage across five sessions, but its sleeve split is a deterministic rank partition and should be replaced by the final production sleeve definition only after a dedicated research decision.

No live eligibility, order routing, Feishu delivery, or production artifact was changed.
