# Fundamental State Forecasting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an auditable research MVP that forecasts one-year-ahead fundamental states, compares them with persistence, and converts forecasts plus valuation inputs into a cross-sectional research score.

**Architecture:** Keep strategy identity and literature in `strategy-research`, reusable label/evaluation/scoring logic in `alpha-research`, and reuse `portfolio-backtester` unchanged. The label layer carries explicit target availability dates so purging and embargo can operate on actual information windows instead of guessed holding periods.

**Tech Stack:** Python 3.12+, pandas, numpy, pytest, existing `alpha_research.ResearchModel` and `portfolio_backtester` public APIs.

**Spec:** `docs/superpowers/specs/2026-09-01-fundamental-state-forecasting-design.md`

## Global Constraints

- Research lifecycle starts at `exploration` and is not production eligible.
- Do not add runtime dependencies from `alpha-research` to `portfolio-backtester` or `strategy-pipeline`.
- Require one canonical PIT-audited annual observation per `(symbol, report_period)` in the first label contract.
- Persist `feature_as_of_date`, `target_report_period`, `target_available_date`, and `fundamental_label_end_date` with labels.
- Reuse single-target `ResearchModel`; do not add multi-task deep learning.
- Reuse `portfolio-backtester` without strategy-specific changes unless a missing generic capability is demonstrated.

---

### Task 1: Fundamental target contract

**Files:**
- Create: `alpha-research/src/alpha_research/fundamental_state.py`
- Create: `alpha-research/tests/test_fundamental_state.py`

**Interfaces:**
- Produces: `FundamentalTargetSpec`, `FundamentalTargetPanel`, `build_annual_fundamental_target_panel`.

- [ ] **Step 1: Write failing tests for exact one-year target alignment and availability metadata**

```python
specs = (
    FundamentalTargetSpec("delta_roa_1y", "roa", "delta"),
    FundamentalTargetSpec("revenue_growth_1y", "revenue", "pct_change"),
)
result = build_annual_fundamental_target_panel(frame, specs)
assert result.frame.loc[0, "target_report_period"] == pd.Timestamp("2023-12-31")
assert result.frame.loc[0, "fundamental_label_end_date"] == pd.Timestamp("2024-03-20")
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `pytest tests/test_fundamental_state.py -q`
Expected: import failure because `alpha_research.fundamental_state` does not exist.

- [ ] **Step 3: Implement the strict annual label builder**

Implement exact-period matching, duplicate rejection, level/delta/pct-change transforms, and target availability audit metadata.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `pytest tests/test_fundamental_state.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/alpha_research/fundamental_state.py tests/test_fundamental_state.py
git commit -m "feat: add PIT fundamental state targets"
```

### Task 2: Baseline, OOS metrics, and leakage controls

**Files:**
- Modify: `alpha-research/src/alpha_research/fundamental_state.py`
- Modify: `alpha-research/tests/test_fundamental_state.py`

**Interfaces:**
- Produces: `build_persistence_baseline`, `evaluate_fundamental_forecast`, `purge_and_embargo_fundamental_rows`.

- [ ] **Step 1: Add failing tests for persistence semantics and purge/embargo**

```python
baseline = build_persistence_baseline(frame, FundamentalTargetSpec("delta_roa", "roa", "delta"))
assert baseline.tolist() == [0.0, 0.0]

result = purge_and_embargo_fundamental_rows(
    training_candidates,
    test_start="2020-01-01",
    test_end="2020-12-31",
    embargo_days=31,
)
assert "overlap" not in set(result.frame["symbol"])
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `pytest tests/test_fundamental_state.py -q`
Expected: missing baseline/evaluation/purge functions.

- [ ] **Step 3: Implement minimal functions**

Metrics must include `count`, `mae`, `rmse`, rank IC, and optional direction accuracy. Purging removes rows whose `[feature_as_of_date, fundamental_label_end_date]` interval overlaps the test interval; embargo removes rows whose feature date falls immediately after the test interval.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `pytest tests/test_fundamental_state.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/alpha_research/fundamental_state.py tests/test_fundamental_state.py
git commit -m "feat: add fundamental forecast diagnostics"
```

### Task 3: Forecast and valuation score bridge

**Files:**
- Modify: `alpha-research/src/alpha_research/fundamental_state.py`
- Modify: `alpha-research/tests/test_fundamental_state.py`
- Create: `alpha-research/docs/concepts/fundamental-state-forecasting.md`
- Modify: `alpha-research/docs/README.md`

**Interfaces:**
- Produces: `FundamentalScoreSpec`, `build_fundamental_forecast_score`.

- [ ] **Step 1: Add a failing score test**

```python
scored = build_fundamental_forecast_score(
    frame,
    (
        FundamentalScoreSpec("pred_quality", weight=2.0),
        FundamentalScoreSpec("pred_growth"),
        FundamentalScoreSpec("earnings_yield"),
    ),
)
assert scored.sort_values("fundamental_rank").iloc[0]["symbol"] == "A"
```

- [ ] **Step 2: Verify RED, then implement weighted same-date percentile scoring**

Run: `pytest tests/test_fundamental_state.py -q`
Expected before implementation: missing score API. Expected after implementation: PASS.

- [ ] **Step 3: Document the research workflow**

Document target semantics, persistence baseline, use of existing `ResearchModel`, the score bridge, and the rule that portfolio evaluation happens only after OOS fundamental prediction is established.

- [ ] **Step 4: Run alpha-research local gates**

Run when a full checkout is available:

```bash
scripts/dev/run_tests.sh lint
scripts/dev/run_tests.sh typecheck
scripts/dev/run_tests.sh all
```

- [ ] **Step 5: Commit**

```bash
git add src tests docs
git commit -m "docs: describe fundamental state forecasting workflow"
```

### Task 4: Strategy research identity and literature map

**Files:**
- Create: `strategy-research/research/experiments/fundamental_state_forecasting/README.md`
- Modify: `strategy-research/catalog.json`
- Modify: `strategy-research/README.md`

**Interfaces:**
- Produces: `fundamental_state_forecasting_v1` exploration entry with no production runtime.

- [ ] **Step 1: Register the experiment as exploration**

Use `production_eligible: false`, executable owners `alpha-research` and `portfolio-backtester`, and no execution control plane.

- [ ] **Step 2: Write falsifiable experiment gates**

The experiment must compare persistence, linear, and ML forecasts; stop escalation if ML cannot beat persistence OOS; only then compare forecast+valuation scores with current-fundamental baselines.

- [ ] **Step 3: Run strategy-research tests when a full checkout is available**

```bash
uv run --project strategy-research --extra dev python -m pytest tests -q
```

- [ ] **Step 4: Commit**

```bash
git add catalog.json README.md research/experiments/fundamental_state_forecasting/README.md
git commit -m "research: register fundamental state forecasting"
```

### Task 5: Pull requests and workspace lock

**Files:**
- Modify gitlinks in `research-workspace` for `alpha-research` and `strategy-research` after sub-repository commits are available.

- [ ] **Step 1: Open sub-repository PRs**

Create PRs from `feat/fundamental-state-forecasting` to `main` in `alpha-research` and `strategy-research`.

- [ ] **Step 2: Record real verification status in each PR**

Do not claim the disabled GitHub Actions ran. Include focused tests actually executed and list full local gates as pending if the current environment cannot clone the private repositories.

- [ ] **Step 3: Update workspace gitlinks to the feature commits**

The aggregate workspace PR may reference unmerged feature commits for review; merge order remains sub-repositories first, workspace last.

- [ ] **Step 4: Open the workspace PR**

Include links to both child PRs, design/spec documents, test evidence, and explicit note that `portfolio-backtester` is unchanged.
