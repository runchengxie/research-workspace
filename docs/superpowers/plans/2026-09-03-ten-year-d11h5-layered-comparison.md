# Ten-Year D11-H5 Layered Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build and verify a long historical, research-only comparison of fundamental, DailyWatch20, D11-H5, and their layered combinations under identical portfolio conditions.

**Architecture:** Reuse the existing D11-H5 ranker and score-ladder format. Extend the sealed/raw model-frame preparation far enough back to support strict rolling OOS scoring, then join the resulting ladder with the existing fundamental and DailyWatch20 ladders at common monthly formation dates. The comparison remains an offline research artifact; it does not change published strategy state or production targets.

**Tech Stack:** Python, pandas, Parquet, existing strategy-pipeline D11-H5 ranker, existing portfolio replay utilities, pytest.

**Spec:** `strategy-research/research/experiments/fundamental_state_forecasting/README.md` and the current layered-comparison entries in `strategy-research/research/experiments/long_term_fundamental_v2/20260902_results.md`.

## Global Constraints

- All scores must be point-in-time and research-only.
- Training labels must end no later than each refit date.
- Every strategy arm must use the same formation dates, stock universe, position count, cost, and price asset.
- Published D11-H5 state is authoritative where available; reconstructed history must be audited separately.
- No production promotion is allowed from this experiment.
- Missing dates or symbols must be reported, not silently forward-filled.

### Task 1: Isolated workspace and coverage audit

**Files:**
- Create: this plan file
- Inspect: `strategy-research/research/experiments/fundamental_state_forecasting/reconstruct_d11_h5_historical.py`
- Inspect: existing research artifacts under `/home/richard/data/market-data-platform/research/fundamental_state_forecasting/`

- [ ] Verify the feature branch is isolated and the base checkout is clean.
- [ ] Record model-frame, DailyWatch20 ladder, price, and fundamental score coverage.
- [ ] Identify the earliest date supported by the current model frame and the earliest date possible from raw daily data.

### Task 2: Historical D11-H5 ladder

**Files:**
- Modify: `strategy-research/research/experiments/fundamental_state_forecasting/reconstruct_d11_h5_historical.py`
- Test: `strategy-research/research/experiments/fundamental_state_forecasting/test_reconstruct_d11_h5_historical.py` if interface changes require tests

- [ ] Parameterize the reconstruction for an earlier model frame and explicit evaluation window.
- [ ] Preserve 504-date training-window and label-end OOS rules.
- [ ] Emit exact Top-800 per-date ladder, refit receipts, and an audit with earliest valid date and coverage gaps.
- [ ] Use a resumable or block-level execution path so a long run can be inspected without losing completed blocks.

### Task 3: Score validation and common-date alignment

**Files:**
- Create or modify: the historical comparison runner under `strategy-research/research/experiments/long_term_fundamental_v2/`
- Modify: `strategy-research/research/experiments/long_term_fundamental_v2/20260902_results.md`

- [ ] Compare reconstructed D11-H5 scores with published scores on overlapping dates using rank correlation and Top-20 overlap.
- [ ] Define the strict common monthly formation-date intersection across all ladders.
- [ ] Fail loudly or report a separate diagnostic when a ladder has missing symbols/dates.

### Task 4: Unified six/seven-arm replay

**Files:**
- Reuse or modify: existing monthly replay runner and portfolio-backtester interfaces
- Create: a dated research artifact directory under `/home/richard/data/market-data-platform/research/fundamental_state_forecasting/`

- [ ] Run fundamental-only, DailyWatch20-only, D11-H5-only, fundamental+DailyWatch20, fundamental+D11-H5, three-way fusion, and DailyWatch20+D11-H5 control arms.
- [ ] Apply identical Top-K, turnover hysteresis, price source, transaction cost, and OOS date rules.
- [ ] Save positions, returns, summary metrics, exposures, and audit receipts for every arm.

### Task 5: Evidence, risk diagnostics, and gate

**Files:**
- Modify: `strategy-research/research/experiments/long_term_fundamental_v2/20260902_results.md`
- Modify: `strategy-research/research/experiments/long_term_fundamental_v2/production_gate_audit_20260903.json`
- Create: dated coverage/comparison audit if needed

- [ ] Report total return, annualized return, Sharpe, drawdown, turnover, costs, sample counts, and common-period coverage.
- [ ] Add size, industry, turnover, concentration, and missing-data diagnostics where available.
- [ ] Separate strict comparable results from partial or reconstructed diagnostics.
- [ ] Keep production eligibility false unless every existing gate is demonstrably satisfied.
- [ ] Run focused tests, syntax checks, and artifact integrity checks before claiming completion.
