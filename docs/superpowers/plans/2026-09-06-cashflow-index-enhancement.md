# Cashflow Index Enhancement Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a reproducible comparison of cash-flow Top-K portfolios and benchmark-relative ML tilts under monthly, quarterly, and D11-H5 staggered rebalancing.

**Architecture:** `quant-platform` owns generic benchmark-relative portfolio construction, rebalance event generation, and comparison metrics. `quant-research` owns the cash-flow input adapter and experiment runner that feeds private ranked signals into those public APIs. The first slice emits research artifacts only and does not alter live eligibility or execution publication.

**Tech Stack:** Python, pandas, NumPy, dataclasses, pytest, Ruff, existing `portfolio_backtester` and `strategy_app` packages.

**Spec:** `docs/superpowers/specs/2026-09-06-cashflow-index-enhancement-design.md`

## Global Constraints

- Keep cash-flow factor definitions, PIT data, model parameters, and strategy decisions in `quant-research`.
- Keep reusable construction and calendar mechanics in `quant-platform`; do not add strategy-specific names or inputs there.
- Preserve `research_only=true`, `eligible_for_live=false`, and reconstructed-PIT gates.
- Preserve existing Top-K equal-weight behavior exactly for legacy callers.
- Use deterministic stable sorting, explicit validation, and versioned receipts.
- Do not modify or stage unrelated existing worktree changes.

---

### Task 1: Add public portfolio construction variants

**Files:**
- Create: `/home/richard/code/.public-staging/quant-platform/packages/portfolio-backtester/src/portfolio_backtester/benchmark_enhancement.py`
- Modify: `/home/richard/code/.public-staging/quant-platform/packages/portfolio-backtester/src/portfolio_backtester/__init__.py`
- Test: `/home/richard/code/.public-staging/quant-platform/tests/test_benchmark_enhancement.py`

**Interfaces:**
- `build_target_weights(frame, variant, top_k=20, tilt_strength=0.0) -> pd.Series`
- `PortfolioConstructionVariant`: `topk_equal_weight`, `topk_benchmark_weight`, `benchmark_ml_tilt`
- Required input columns: `symbol`, `selection_rank`, `ml_score`, `benchmark_weight`.

- [ ] Write failing tests for input validation, stable Top-K selection, weight sums, and the three variant definitions.
- [ ] Run `uv run pytest tests/test_benchmark_enhancement.py -q` and confirm import/behavior failures.
- [ ] Implement deterministic validation and the three weight builders. Preserve zero-score/zero-tilt behavior and reject invalid benchmark weights.
- [ ] Add public exports without changing existing imports.
- [ ] Run the focused tests and `uv run ruff check` on changed files.

### Task 2: Add generic rebalance policy events

**Files:**
- Modify: `/home/richard/code/.public-staging/quant-platform/packages/portfolio-backtester/src/portfolio_backtester/rebalance.py`
- Test: `/home/richard/code/.public-staging/quant-platform/tests/test_rebalance.py`

**Interfaces:**
- `get_rebalance_events(trading_sessions, policy, sleeve_count=5) -> pd.DataFrame`
- Policies: `monthly`, `quarterly`, `d11_h5`.
- Event columns: `signal_date`, `execution_date`, `sleeve_id`, `sleeve_count`, `policy`.

- [ ] Write failing tests for monthly and quarterly single-date events, deterministic five-sleeve D11-H5 events, and invalid/short calendars.
- [ ] Run the focused rebalance tests and confirm the new API is absent.
- [ ] Implement the event generator using the existing calendar helpers. D11-H5 must assign each execution session exactly one sleeve while retaining one signal vintage for the full five-session cycle.
- [ ] Run all existing rebalance tests plus the new tests and Ruff.

### Task 3: Add public comparison metrics and artifact contract

**Files:**
- Create: `/home/richard/code/.public-staging/quant-platform/packages/portfolio-backtester/src/portfolio_backtester/benchmark_comparison.py`
- Modify: `/home/richard/code/.public-staging/quant-platform/contracts/style-factor-backtest-v1.schema.json` only if the existing contract can safely host the generic comparison envelope; otherwise create `contracts/benchmark-enhancement-comparison-v1.schema.json`
- Test: `/home/richard/code/.public-staging/quant-platform/tests/test_benchmark_comparison.py`

**Interfaces:**
- `compare_portfolio_returns(portfolio_returns, benchmark_returns, weights, benchmark_weights, previous_weights=None) -> dict[str, float]`
- Metrics: total return, annualized return, excess return, tracking error, information ratio, turnover, and active share.
- Receipt keys: `schema_version`, `variant`, `rebalance_policy`, `input_sha256`, `research_only`.

- [ ] Write failing tests with synthetic returns and weights, including zero-volatility excess and empty inputs.
- [ ] Run focused tests and confirm missing implementation failures.
- [ ] Implement numerically stable metrics with explicit annualization and deterministic input hashing.
- [ ] Add/validate the public JSON schema and keep private strategy fields out of it.
- [ ] Run focused tests, schema tests, full public pytest, and Ruff.

### Task 4: Add private cash-flow experiment adapter

**Files:**
- Create: `/home/richard/code/.private-staging/quant-research/src/strategy_app/cashflow/construction_experiment.py`
- Modify: `/home/richard/code/.private-staging/quant-research/src/strategy_app/cashflow/__init__.py`
- Test: `/home/richard/code/.private-staging/quant-research/tests/test_cashflow_construction_experiment.py`

**Interfaces:**
- `run_cashflow_construction_experiment(selection, returns, trading_sessions, benchmark_returns, benchmark_weights, *, top_k, tilt_strengths) -> pd.DataFrame`
- The adapter may import only stable public APIs from `quant-platform` and must not expose private feature columns.

- [ ] Write failing tests asserting the 3 × 3 variant/policy matrix, same signal vintage across D11-H5 events, legacy Top-K equality, and research-only receipt fields.
- [ ] Run focused tests and confirm the adapter is absent.
- [ ] Implement input normalization, public API calls, and long-form matrix output with `variant`, `rebalance_policy`, `signal_date`, and metrics.
- [ ] Add deterministic output sorting and explicit failure for missing required columns or empty calendars.
- [ ] Run focused private tests, existing cash-flow calendar/runner tests, and Ruff.

### Task 5: Add private experiment CLI and evidence report

**Files:**
- Modify: `/home/richard/code/.private-staging/quant-research/src/strategy_app/cashflow/cli.py`
- Create: `/home/richard/code/.private-staging/quant-research/research/experiments/cashflow_indices/run_construction_comparison.py`
- Create: `/home/richard/code/.private-staging/quant-research/research/experiments/cashflow_indices/construction_comparison_protocol.md`
- Test: `/home/richard/code/.private-staging/quant-research/tests/test_cashflow_construction_cli.py`

- [ ] Write failing CLI tests for required inputs, output path, and explicit research-only labeling.
- [ ] Run the focused CLI tests and confirm failure.
- [ ] Implement a thin CLI that loads existing cash-flow ranking/return artifacts, runs the matrix, and writes CSV plus JSON receipt. Do not add live or Feishu delivery.
- [ ] Document the fixed comparison protocol, including no re-training, no future prices, and identical signal inputs across variants.
- [ ] Run focused tests, private package checks, and Ruff.

### Task 6: Joint verification and handoff

**Files:**
- Modify: `/home/richard/code/research-workspace/docs/evidence/cashflow-construction-comparison-20260906.md`

- [ ] Run public `uv sync --locked --all-groups`, `uv run pytest`, and `uv run ruff check .`.
- [ ] Run private cash-flow tests and the comparison CLI on a synthetic fixture only.
- [ ] Verify the legacy Top-K output is unchanged and all new artifacts carry research-only status.
- [ ] Record commands, pass/fail results, known gaps, and next experiment candidates in the evidence note.
- [ ] Review git diffs in each repository and stage only files belonging to this plan.
