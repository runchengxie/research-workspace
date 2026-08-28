# Shibor Regime Exploration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, non-production exploration that tests whether Shibor regimes and Shibor×stock exposures add explanatory power to a daily cross-sectional baseline.

**Architecture:** Keep data ownership in `market-data-platform`; the top-level experiment reads published `a_share` and `cn_context` contracts through owner APIs. The experiment computes only research-specific transforms, joins, labels, and diagnostics, and writes an auditable result artifact without changing execution or production strategy code.

**Tech Stack:** Python, pandas, PyYAML, existing `market_data_platform` and `alpha_research` APIs, pytest.

**Spec:** `strategy-research/experiments/macro_context_shadow/experiment.yml`

## Global Constraints

- Shibor is the primary context; PMI is exploratory only and cannot make a promotion-safe claim.
- The primary label horizon is 20 trading days; 5 and 60 days are secondary.
- The experiment must preserve `available_at <= feature_as_of` and record contract hashes.
- No production strategy, execution, or DailyWatch20 wiring.
- Reconstructed context rows may be reported but must be marked and excluded from strict evidence.

### Task 1: Define the exploration protocol and result schema

**Files:**
- Modify: `strategy-research/experiments/macro_context_shadow/experiment.yml`
- Modify: `strategy-research/experiments/macro_context_shadow/README.md`
- Test: `strategy-research/tests/test_shibor_regime_exploration.py`

**Interfaces:**
- Produces frozen regime names, horizons, cost assumptions, and result field names for later tasks.

- [ ] Write tests for the frozen protocol and strict exclusion of reconstructed rows.
- [ ] Run the focused tests and confirm they fail for the missing protocol helpers.
- [ ] Add the protocol fields and minimal validation helpers.
- [ ] Run focused tests and commit.

### Task 2: Implement PIT-safe Shibor regime and exposure transforms

**Files:**
- Create: `strategy-research/experiments/macro_context_shadow/shibor_regime.py`
- Modify: `strategy-research/tests/test_shibor_regime_exploration.py`

**Interfaces:**
- `build_shibor_regimes(context_pit: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame`
- `build_shibor_exposure_interactions(stock_frame: pd.DataFrame, regimes: pd.DataFrame) -> pd.DataFrame`
- `build_forward_labels(prices: pd.DataFrame, horizons: Sequence[int]) -> pd.DataFrame`

- [ ] Add failing tests for as-of filtering, regime direction, exposure interactions, and forward-label non-lookahead.
- [ ] Run tests and verify expected failures.
- [ ] Implement the smallest pure functions using published rows only.
- [ ] Run focused tests, format/lint, and commit.

### Task 3: Add a real-data exploration runner

**Files:**
- Create: `strategy-research/experiments/macro_context_shadow/run_shibor_regime_exploration.py`
- Modify: `strategy-research/tests/test_shibor_regime_exploration.py`
- Modify: `strategy-research/experiments/macro_context_shadow/README.md`

**Interfaces:**
- CLI arguments: `--data-root`, `--output`, `--as-of`, `--dry-run`.
- Output JSON contains contract hashes, row counts, PIT audit, regime counts, and an explicit `evidence_status`.

- [ ] Add failing runner tests for dry-run output and missing-input failure.
- [ ] Implement contract loading, data discovery, diagnostics, and JSON output.
- [ ] Run the focused tests and local real-data dry run.
- [ ] Commit.

### Task 4: Run evidence-producing diagnostics and document limits

**Files:**
- Create: `strategy-research/experiments/macro_context_shadow/README.md` result section or `results/README.md`
- Test: existing focused tests plus runner smoke test

- [ ] Run the runner against the current data root for 20-day primary horizon.
- [ ] Report sample coverage, reconstructed share, regime balance, and whether strict evidence is eligible.
- [ ] Do not claim alpha where the current data history is insufficient.
- [ ] Run final verification and create a draft PR for review.
