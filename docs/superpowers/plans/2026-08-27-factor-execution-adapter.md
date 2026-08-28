# Factor Execution Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the small-cap low-turnover experiment produce a standard `portfolio-backtester` positions artifact and provide a tested execution entry point without changing signal construction.

**Architecture:** Keep data preparation, candidate ranking, eligibility, and buffered target construction in `strategy-research`. Add a thin adapter that normalizes those targets into the `positions_by_rebalance` contract, then call the owner package's execution API from a dedicated research helper. The first implementation will preserve the existing runner and add a parallel, testable path so historical outputs are not silently changed.

**Tech Stack:** Python 3.13, pandas, pytest, uv, `portfolio_backtester`.

**Spec:** User request to reuse `research-workspace/portfolio-backtester` for the small-cap low-turnover backtest.

## Global Constraints

- Do not modify signal definitions, candidate eligibility, target count, buffer count, or historical output semantics in this first migration.
- Use the `portfolio_backtester.positions_by_rebalance` contract and owner package APIs rather than importing adjacent source paths at runtime.
- Add tests before production code and verify the expected failure before implementation.
- Do not add generated artifacts, credentials, or local absolute paths to tracked files.

---

### Task 1: Repair and verify the local dependency environment

**Files:**
- Modify: `strategy-research/uv.lock` only if lock validation proves it stale
- Test: existing `strategy-research/tests/test_small_cap_low_turnover_exploration.py`

**Interfaces:**
- Consumes: local path dependency declared in `strategy-research/pyproject.toml`
- Produces: a reproducible environment that imports the current `ExecutionSimConfig`

- [x] **Step 1: Run the failing test baseline**

Run `uv run --project strategy-research --extra dev python -m pytest strategy-research/tests/test_small_cap_low_turnover_exploration.py -q` from the workspace root.

Expected: 26 passed and 3 failures caused by the missing `liquidity_notional_multiplier` constructor field.

- [x] **Step 2: Reinstall the local owner package**

Run `uv sync --project strategy-research --locked --reinstall-package portfolio-backtester`.

- [x] **Step 3: Verify the imported interface**

Run a Python probe that prints `portfolio_backtester.__file__` and asserts `liquidity_notional_multiplier` is present in `ExecutionSimConfig.__dataclass_fields__`.

- [x] **Step 4: Run the focused test file again**

Expected: the three constructor failures are gone. Any new failure is a real behavioral mismatch and must be investigated separately.

### Task 2: Define the standard positions adapter

**Files:**
- Create: `strategy-research/style_factors/portfolio_backtester_adapter.py`
- Test: `strategy-research/tests/test_portfolio_backtester_adapter.py`

**Interfaces:**
- Consumes: buffered target mappings or a target frame with `rebalance_date`, `entry_date`, `symbol`, and target weight/notional data.
- Produces: `to_positions_by_rebalance(targets, portfolio_value) -> pd.DataFrame` with columns `rebalance_date`, `entry_date`, `symbol`, and `weight`.

- [x] **Step 1: Write failing tests**

Cover target normalization, deterministic ordering, duplicate symbol rejection within a rebalance, and empty input behavior.

- [x] **Step 2: Run the adapter tests and confirm the expected missing-import failure**

Run `uv run --project strategy-research --extra dev python -m pytest strategy-research/tests/test_portfolio_backtester_adapter.py -q`.

- [x] **Step 3: Implement the minimal adapter**

Validate required columns, normalize dates, accept either `weight` or `target_weight`, reject duplicate `(rebalance_date, symbol)` rows, preserve explicit cash shortfall, sort deterministically, and call the owner contract validator.

- [x] **Step 4: Run adapter tests**

Expected: all adapter tests pass.

### Task 3: Add a tested owner-package execution helper

**Files:**
- Modify: `strategy-research/style_factors/portfolio_backtester_adapter.py`
- Test: `strategy-research/tests/test_portfolio_backtester_adapter.py`

**Interfaces:**
- Consumes: standard positions frame, pricing frame, execution configuration.
- Produces: a `CanonicalBacktestResult` or owner execution result from `NativePositionReplayBackend`.

- [x] **Step 1: Write a failing synthetic execution test**

Use a small two-symbol, multi-date pricing frame and assert the helper returns daily NAV plus orders/fills with the expected symbols and dates.

- [x] **Step 2: Run the test and confirm the failure identifies the missing helper**

- [x] **Step 3: Implement the thin helper**

Construct the owner backend request, keep configuration creation outside the adapter, and avoid importing `strategy_research` internals into `portfolio-backtester`.

- [x] **Step 4: Run the synthetic execution test**

Expected: pass with the current owner package source installed in the worktree environment.

### Task 4: Wire a parallel research entry point

**Files:**
- Modify: `strategy-research/experiments/style_factors/small_cap_low_turnover_exploration_20260826.py`
- Test: `strategy-research/tests/test_small_cap_low_turnover_exploration.py`

**Interfaces:**
- Consumes: existing `formation_targets` and pricing data.
- Produces: an optional owner-engine execution result while retaining the legacy matrices for comparison.

- [x] **Step 1: Add a failing integration-level test**

Assert that a synthetic buffered target can be passed through the adapter and owner execution helper without changing the existing signal panel.

- [x] **Step 2: Implement the smallest parallel hook**

Add an opt-in helper or CLI flag that writes no output by default and does not replace the historical runner path.

- [x] **Step 3: Run the focused integration tests**

- [x] **Step 4: Run the complete strategy-research test suite**

Run `uv run --project strategy-research --extra dev python -m pytest strategy-research/tests -q`.

### Task 5: Document migration boundary and verification receipt

**Files:**
- Modify: `strategy-research/experiments/style_factors/small-cap-low-turnover-exploration-20260826.md`
- Modify: `strategy-research/README.md` if the new entry point is user-facing

**Interfaces:**
- Consumes: verified test and execution results.
- Produces: documentation stating which path is canonical, which path is comparison-only, and whether impact/slippage is actually active.

- [x] **Step 1: Update documentation from verified behavior only**

- [x] **Step 2: Run relevant documentation/path checks and the full focused test suite**

- [x] **Step 3: Review the diff and report any remaining migration gaps**
