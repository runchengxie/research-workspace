# Small-cap Low-turnover Robustness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the exploratory small-cap × low-turnover comparison with turnover-definition, prior-amount participation, and integer-lot sensitivity evidence.

**Architecture:** Keep the experiment in `strategy-research`. Add optional capacity and rounded-target inputs to the existing constrained simulator without changing its default behavior, then let the experiment runner reuse one loaded market contract for a compact robustness matrix. Treat 2015–2023 as development and 2024–2026 as a fixed holdout for reporting only.

**Tech Stack:** Python 3.12+, pandas, NumPy, pytest, the existing `robustness_execution` simulator, and the existing `strategy-research` data contract.

**Spec:** `strategy-research/experiments/style_factors/small-cap-low-turnover-exploration-20260826.md`

## Global Constraints

- Keep this as `exploration_only`; do not modify `strategy-research/catalog.json` or production configuration.
- Preserve the default behavior of `simulate_leg` and all existing robustness callers.
- Use 100-share A-share lot rounding and report continuous-weight limitations explicitly.
- Use 5%, 10%, and 20% of prior observed traded amount as ADV participation sensitivities.
- Use lagged turnover only; never include the formation session in the lookback.
- Do not select a parameter using the 2024–2026 holdout.

---

### Task 1: Add tested execution sensitivities

**Files:**
- Modify: `strategy-research/style_factors/robustness_execution.py`
- Modify: `strategy-research/style_factors/small_cap_low_turnover.py`
- Test: `strategy-research/tests/test_small_cap_low_turnover_exploration.py`

**Interfaces:**
- `simulate_leg(..., max_trade_weight: np.ndarray | None = None)` caps each day’s per-symbol weight change when supplied; `None` keeps current behavior.
- `round_target_weights_to_lots(targets, daily_clean, initial_capital, lot_size=100)` returns target weights after share-count flooring.
- `build_trade_capacity_matrix(daily_clean, returns, initial_capital, participation_rate)` returns a date-by-symbol maximum trade-weight matrix.
- `build_lagged_turnover_panel(..., statistic="mean")` emits `turnover_lagged_<statistic>_<window>d`.

- [x] **Step 1: Write failing tests** for a capped pending order, 100-share target rounding, lagged median turnover, and a zero-capacity matrix row.
- [x] **Step 2: Run the focused test file** and confirm the new tests fail because the interfaces do not exist.
- [x] **Step 3: Implement the optional execution cap and the two small-cap helper functions** without changing default simulation behavior.
- [x] **Step 4: Extend the turnover helper with mean/median aggregation** while preserving the default 60-day mean output.
- [x] **Step 5: Run focused tests, lint, and type checks** and confirm they pass.

### Task 2: Produce the robustness matrix

**Files:**
- Modify: `strategy-research/experiments/style_factors/small_cap_low_turnover_exploration_20260826.py`
- Test: `strategy-research/tests/test_small_cap_low_turnover_exploration.py`

**Interfaces:**
- Add a runner helper that labels each row with `turnover_definition`, `participation_rate`, `lot_size`, and `holdout_period`.
- Reuse `simulate_long_only_candidates` for the raw composite only in the sensitivity matrix; retain the full seven-arm baseline comparison.
- Add `candidate_robustness_matrix.csv` and include development/holdout net returns in the Markdown report.

- [x] **Step 1: Write a failing unit test** for the development/holdout period return helper.
- [x] **Step 2: Run the focused test and confirm it fails because the helper is missing.**
- [x] **Step 3: Implement turnover definitions `mean_20`, `mean_60`, `median_60`, and `mean_120` plus participation cases `unconstrained`, `0.05`, `0.10`, and `0.20`.**
- [x] **Step 4: Apply 100-share rounding in the sensitivity cases** and write the matrix CSV, report section, and metadata.
- [x] **Step 5: Run the focused tests and a small synthetic runner check.**

### Task 3: Run, document, and verify

**Files:**
- Modify: `strategy-research/experiments/style_factors/small-cap-low-turnover-exploration-20260826.md`
- Generated externally: `/tmp/small_cap_low_turnover_exploration_20260826/*`

- [x] **Step 1: Run the full 2015–2026 experiment** with outputs in `/tmp`.
- [x] **Step 2: Inspect the robustness matrix** for cost/capacity collapse, turnover sensitivity, and holdout behavior.
- [x] **Step 3: Update the tracked readout** with the observed matrix and explicit limitations.
- [x] **Step 4: Run the full `strategy-research` tests, Ruff, format check, type check, and `git diff --check`.**
- [x] **Step 5: Commit the verified extension locally without pushing or merging.**
