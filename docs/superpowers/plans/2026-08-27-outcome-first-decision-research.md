# Outcome-first Decision Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add machine-checkable outcome profiles, reusable outcome/path metrics, Pareto-aware decision receipts, and a research-only DailyWatch20 path-aware exit challenger without changing production behavior.

**Architecture:** Governance remains in the top-level `strategy-research`, generic realized-outcome metrics live in `portfolio-backtester`, and strategy-specific comparison and exit logic live in `strategy-app`. The three PRs are independently reviewable. P4 general barrier infrastructure is deliberately deferred.

**Tech Stack:** Python 3.12+, pandas, NumPy, JSON Schema, pytest, Ruff, ty, uv.

**Spec:** `docs/superpowers/specs/2026-08-27-outcome-first-decision-research-design.md`

## Global Constraints

- Keep prediction, portfolio construction, strategy logic and governance in their current owner repositories.
- Do not synthesize uncertainty from alpha scores.
- Do not create a scalar utility or aggregate confidence score.
- Do not add parameter-grid search for the exit challenger.
- Keep all new behavior opt-in and preserve current production outputs.
- P4 generic path/barrier infrastructure remains out of scope.

---

### Task 1: Outcome profile governance

**Files:**
- Create: `strategy-research/schemas/outcome_profile.v1.schema.json`
- Modify: `strategy-research/schemas/research_case.v1.schema.json`
- Modify: `scripts/decision_governance_check.py`
- Modify: `tests/test_decision_governance_check.py`
- Modify: `docs/research-decision-governance.md`

**Interfaces:**
- Consumes: existing `research_case.v1` and governance validator conventions.
- Produces: `outcome_profile.v1`, `check_outcome_profile()`, optional `research_case.v1.outcome_profiles` references.

- [ ] Write failing tests proving a valid outcome profile passes, duplicate metric names fail, incomplete constraints fail, and a case reference to a missing profile fails.
- [ ] Run `python -m pytest tests/test_decision_governance_check.py -q` and confirm failures are caused by missing outcome-profile support.
- [ ] Add the JSON Schema with decision-type, status, metric-role, direction and constraint validation.
- [ ] Extend `decision_governance_check.py` with `OUTCOME_PROFILE_SCHEMA_VERSION`, profile validation, file-name identity checks, case-reference checks, `--outcome-profile`, and full-scan discovery.
- [ ] Extend `research_case.v1.schema.json` with optional `outcome_profiles` string references.
- [ ] Update `docs/research-decision-governance.md` to explain preference-versus-prediction semantics and empirical feasibility wording.
- [ ] Run targeted governance tests and the decision-governance CLI scan.

### Task 2: Generic realized-outcome metrics

**Files:**
- Create: `portfolio-backtester/src/portfolio_backtester/outcome_metrics.py`
- Create: `portfolio-backtester/tests/test_outcome_metrics.py`
- Modify: `portfolio-backtester/src/portfolio_backtester/__init__.py`
- Modify: `portfolio-backtester/tests/test_package_smoke.py`
- Modify: `portfolio-backtester/docs/reference/public-api.md`
- Modify: `portfolio-backtester/README.md`

**Interfaces:**
- Produces: immutable `OutcomeDistributionReport` and `summarize_outcome_distribution()`.
- Inputs: equal-length realized return, MFE, MAE, peak-giveback and holding-period series.

- [ ] Write failing tests for exact quantiles, loss probability, 5% CVaR, MFE/MAE, peak-giveback and holding-period summaries.
- [ ] Add failing tests for empty input, non-finite values, negative holding periods and length mismatch.
- [ ] Run `uv run --locked --extra dev python -m pytest tests/test_outcome_metrics.py -q` and confirm RED.
- [ ] Implement `OutcomeDistributionReport` and `summarize_outcome_distribution()` with fail-closed validation.
- [ ] Export the new public API and repair the pre-existing robust-uncertainty export mismatch in `test_package_smoke.py`.
- [ ] Update user-facing API docs without changing existing backtest output contracts.
- [ ] Run targeted tests, package smoke, Ruff, format, ty, maintainability and the full test suite.

### Task 3: Pareto-aware decision receipt

**Files:**
- Modify: `strategy-app/src/strategy_app/decision_evaluation.py`
- Modify: `strategy-app/src/strategy_app/__init__.py`
- Modify: `strategy-app/tests/test_decision_focused_evaluation.py`

**Interfaces:**
- Produces: `ParetoRelation`, `pareto_relation()` and `DecisionEvaluationReceipt.pareto_relation`.

- [ ] Write failing tests for candidate dominance, baseline dominance, equivalence and mixed trade-off.
- [ ] Run the decision-evaluation tests and confirm RED.
- [ ] Implement direction-normalized Pareto comparison with no tolerance or aggregate scoring.
- [ ] Add deterministic serialization of the relation while preserving the existing builder call signature.
- [ ] Run targeted tests, lint and type checks.

### Task 4: DailyWatch20 path-aware exit research overlay

**Files:**
- Create: `strategy-app/src/strategy_app/daily_watch20/path_aware_exit.py`
- Modify: `strategy-app/src/strategy_app/daily_watch20/__init__.py`
- Create: `strategy-app/tests/test_daily_watch20_path_aware_exit.py`
- Modify: `strategy-app/docs/application-catalog.md`

**Interfaces:**
- Produces: `PathAwareExitPolicy`, `PathAwareExitResult`, `evaluate_path_aware_exit_episode()` and `evaluate_path_aware_exit_challenger()`.
- Inputs: baseline trade episodes with `trade_id`, `trade_date`, `price`, `score`, `uncertainty`.
- Output: per-trade baseline/challenger exit results and a non-promotable receipt.

- [ ] Write failing tests for peak drawdown triggering, tighter thresholds under score decay/uncertainty/age, baseline fallback, invalid normalized inputs and duplicate or unordered episode rows.
- [ ] Write a failing test proving one run accepts one immutable policy and emits `parameter_search_allowed=false`, `automatic_promotion_allowed=false` and required validation names.
- [ ] Run the new test file and confirm RED.
- [ ] Implement the immutable policy and scalar threshold calculation with `[min_drawdown, base_drawdown]` clipping.
- [ ] Implement episode evaluation using the first row as entry and the last row as baseline exit. Challenger exit may only occur on or before the baseline exit.
- [ ] Implement grouped evaluation across `trade_id`, preserving deterministic order and emitting policy SHA-256 plus validation requirements.
- [ ] Document the application as research-only and explicitly state that it does not reallocate capital after an early exit.
- [ ] Run targeted tests, all strategy-app tests except the documented pre-existing style failure, Ruff, format, ty and maintainability.

### Task 5: PR preparation and integration evidence

**Files:**
- Modify only generated branch metadata or top-level gitlinks if owner PRs are ready for pinning.

- [ ] Review each repository diff for owner-boundary violations and unrelated changes.
- [ ] Run each repository's required local gate and record any pre-existing failures separately from feature failures.
- [ ] Commit the three branches with scoped messages.
- [ ] Push owner branches and open `portfolio-backtester` and `strategy-app` PRs first.
- [ ] Push the top-level governance branch and open its PR. Do not pin unmerged owner gitlinks unless the PR is explicitly marked dependent.
- [ ] Request review and report exact test results, known baseline failures and deferred P4 scope.
