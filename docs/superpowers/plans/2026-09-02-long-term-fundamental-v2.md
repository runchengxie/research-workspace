# A-Share Long-Term Fundamental Selection v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PIT-safe research-only v2 that identifies persistent operating quality, filters value traps, incorporates earnings-expectation changes where data exists, and evaluates quarterly low-turnover portfolios with mature-return diagnostics.

**Architecture:** Keep data acquisition and vintage provenance in `market-data-platform`, reusable targets/scores in `alpha-research`, and research composition in `strategy-research`. The first implementation uses explicit target contracts and simple baselines; it does not promote a strategy or add production wiring.

**Tech Stack:** Python, pandas, NumPy, Parquet, pytest, existing alpha and portfolio-backtester APIs.

**Spec:** `strategy-research/research/experiments/fundamental_state_forecasting/README.md`

## Global Constraints

- Every feature and label must be point-in-time safe and carry its availability semantics.
- Stable-compounder labels are descriptive until they pass out-of-sample tests.
- Quarterly rebalance and incumbent buffer must use one declared cost and one OOS calendar.
- No production promotion before multi-period OOS, cost, exposure, and data-lineage gates pass.
- Analyst forecast/revision data must be proven available before it is used; otherwise record a data-gap result.

### Task 1: Freeze v2 research specification

**Files:**
- Create: `strategy-research/research/experiments/long_term_fundamental_v2/README.md`
- Test: `strategy-research/tests/test_long_term_fundamental_v2_spec.py`

- [ ] Define stable-compounder loose/strict labels, value-trap exclusions, quarterly update rules, and failure gates in the README.
- [ ] Add a test that the declared specification records research-only status, PIT requirements, and no-production eligibility.
- [ ] Run the focused test and verify it fails before adding the implementation contract.
- [ ] Implement the minimal specification loader/validator and rerun the focused test.

### Task 2: Add persistent-quality and value-trap research functions

**Files:**
- Modify: `strategy-research/research/experiments/long_term_fundamental_v2/quality.py`
- Test: `strategy-research/tests/test_long_term_fundamental_v2_quality.py`

- [ ] Test that labels use only observations visible on the formation date, require three annual observations, and distinguish loose from strict labels.
- [ ] Test that the value-trap filter excludes non-positive profitability, deteriorating growth, extreme leverage, and extreme valuation according to explicit thresholds.
- [ ] Implement deterministic date-by-date label construction and diagnostics.
- [ ] Run focused tests and record label coverage.

### Task 3: Add operating-quality persistence targets

**Files:**
- Modify: `alpha-research/src/alpha_research/fundamental_state.py`
- Test: `alpha-research/tests/test_fundamental_state.py`

- [ ] Add targets for future ROA deterioration, margin durability, positive growth persistence, and cash-conversion deterioration where source columns exist.
- [ ] Preserve target report period, target available date, and label end date.
- [ ] Compare persistence, Ridge, and XGB only on the same strict OOS folds.
- [ ] Run alpha focused tests and save target coverage diagnostics.

### Task 4: Audit earnings-expectation-change availability

**Files:**
- Create: `strategy-research/research/experiments/long_term_fundamental_v2/expectations_audit.py`
- Test: `strategy-research/tests/test_long_term_fundamental_v2_expectations.py`

- [ ] Inspect available PIT forecast, express, analyst revision, and earnings-surprise assets.
- [ ] If announcement-time revision history is available, add a revision-safe feature contract and tests.
- [ ] If it is unavailable, emit an explicit data-gap receipt and do not substitute future-known values.

### Task 5: Run quarterly low-turnover portfolio evaluation

**Files:**
- Modify: `strategy-research/research/experiments/fundamental_state_forecasting/four_arm_backtest.py`
- Create: `strategy-research/research/experiments/long_term_fundamental_v2/run_quarterly_research.py`
- Test: `strategy-research/tests/test_long_term_fundamental_v2_quarterly.py`

- [ ] Build quarterly rebalance dates from the declared calendar and apply new-entry/ incumbent-exit buffers.
- [ ] Compare quality-only, quality-plus-value, quality-plus-expectations, and DailyWatch20 control under one cost.
- [ ] Save return maturity coverage, turnover, drawdown, size, industry, and valuation exposure receipts.
- [ ] Run focused tests and a bounded real-data smoke before any broader replay.

### Task 6: Publish research report and gate decision

**Files:**
- Create: `strategy-research/research/experiments/long_term_fundamental_v2/20260902_results.md`
- Modify: `strategy-research/research/experiments/fundamental_state_forecasting/20260902_four_arm_recent_diagnostic.md`

- [ ] Separate strict comparable results, diagnostic results, and data gaps.
- [ ] Record whether each gate passed, failed, or remains unverified.
- [ ] Keep the strategy research-only unless all required evidence passes.
- [ ] Run the full relevant test suite and verify the final report against generated receipts.
