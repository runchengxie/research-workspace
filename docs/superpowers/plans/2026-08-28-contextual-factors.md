# Contextual Factors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add framework-neutral context transforms, explainable company exposures, PIT-safe joins, and deterministic `context × exposure` features to `alpha-research`.

**Architecture:** `alpha-research` consumes ordinary PIT-safe DataFrames supplied by callers; it never opens provider files or imports provider SDKs. Transform specs create state variables, exposure specs create bounded stock sensitivities from PIT industry/fundamentals, and interaction specs join the two using explicit as-of rules. Existing trainers/rankers consume the resulting columns unchanged.

**Tech Stack:** Python 3, pandas/numpy, existing `alpha_research` feature evidence and model infrastructure, pytest, Ruff, ty.

**Spec:** `docs/superpowers/specs/2026-08-28-contextual-alpha-platform-design.md`

## Global Constraints

- No TuShare, AKShare, Qlib, NBS, or NEA objects enter public contextual-factor APIs.
- Context visibility must satisfy `available_at <= trade_date/session cutoff`.
- Exposure inputs must be PIT-valid for the stock date.
- Missing context/history/exposure stays missing unless a spec explicitly defines a bounded fallback; never silently fill missing values with zero.
- First exposure values are clipped to `[-1, 1]`.
- First transform set is `level`, `change_1p`, `change_np`, `yoy`, `rolling_zscore`, `acceleration`, `rolling_percentile`.
- First enabled exposure families are `rate_sensitivity`, `credit_sensitivity`, `industrial_activity_sensitivity`, `energy_input_sensitivity`, `energy_output_sensitivity`.
- New production code follows verified-red TDD.

---

### Task 1: Add context transform specs and deterministic transforms

**Files:**
- Create: `src/alpha_research/contextual/__init__.py`
- Create: `src/alpha_research/contextual/transforms.py`
- Test: `tests/test_contextual_transforms.py`
- Modify: `docs/README.md`

**Interfaces:**
- Produces: `ContextTransformSpec(series_id: str, transform: str, window: int | None, minimum_history: int, staleness_limit_days: int | None, feature_name: str)`
- Produces: `build_context_features(observations: pd.DataFrame, specs: Sequence[ContextTransformSpec], *, date_col="available_at") -> pd.DataFrame`

- [ ] **Step 1: Write failing transform tests**

Cover `level`, period-aware one-period change, N-period change, monthly YoY using series order rather than 252 trading-day lag, rolling z-score with zero-standard-deviation output missing, acceleration as change-of-change, and rolling percentile.

- [ ] **Step 2: Write missing-history/staleness tests**

Assert a 12-period YoY has no value before 12 historical periods. Assert a row whose age exceeds `staleness_limit_days` is missing and carries an age column rather than being silently forward-filled.

- [ ] **Step 3: Verify RED**

Run: `uv run --locked --extra dev python -m pytest tests/test_contextual_transforms.py -q`

Expected: import failure.

- [ ] **Step 4: Implement transform spec validation**

Reject unknown transform names, non-positive windows, duplicate `feature_name`, and negative history/staleness values. Keep each transform a pure function over a sorted single-series frame.

- [ ] **Step 5: Implement feature construction and `context_age_days`**

Output one row per visible observation/date and one deterministic feature column per spec. Include `<feature_name>__age_days` whenever the caller expands context to stock dates later.

- [ ] **Step 6: Verify GREEN and commit**

Run: `uv run --locked --extra dev python -m pytest tests/test_contextual_transforms.py -q`

```bash
git add src/alpha_research/contextual/transforms.py src/alpha_research/contextual/__init__.py tests/test_contextual_transforms.py docs/README.md
git commit -m "feat: add contextual state transforms"
```

### Task 2: Add explainable `ExposureSpec` and industry priors

**Files:**
- Create: `src/alpha_research/contextual/exposures.py`
- Create: `src/alpha_research/contextual/default_exposures.py`
- Test: `tests/test_contextual_exposures.py`

**Interfaces:**
- Produces: `FundamentalModifier(field: str, direction: float, weight: float, normalization: str, missing: str)`
- Produces: `ExposureSpec(name: str, industry_prior_map: Mapping[str, float], fundamental_modifiers: tuple[FundamentalModifier, ...], clip_min=-1.0, clip_max=1.0, version="v1")`
- Produces: `build_company_exposures(stock_frame: pd.DataFrame, specs: Sequence[ExposureSpec], *, date_col="trade_date", symbol_col="symbol", industry_col="industry") -> pd.DataFrame`

- [ ] **Step 1: Write failing industry-prior tests**

Create bank, utility, chemical, coal, software, and machinery rows. Assert configured priors are deterministic, unknown industries follow the spec's explicit missing policy, and no result exceeds `[-1, 1]`.

- [ ] **Step 2: Write fundamental-modifier tests**

For `rate_sensitivity`, add leverage/interest-burden test inputs and assert the modifier changes the prior in the declared direction. For `credit_sensitivity`, use leverage/cash inputs. Assert modifiers are cross-sectionally normalized using only rows from the same `trade_date`.

- [ ] **Step 3: Verify RED**

Run: `uv run --locked --extra dev python -m pytest tests/test_contextual_exposures.py -q`

Expected: import failure.

- [ ] **Step 4: Implement exposure mechanics**

Support normalization values `rank_pct` and `zscore_clip`. `rank_pct` maps valid same-date values to `[-1, 1]`; `zscore_clip` clips standardized values at ±3 before rescaling. Missing modifier values follow only `ignore_modifier` or `missing_exposure`; reject any other policy.

- [ ] **Step 5: Add default v1 specs**

Define versioned priors for the five first enabled families. Keep maps intentionally coarse and documented; do not add stock-specific manual values. Default specs must be data, not branching code.

- [ ] **Step 6: Verify GREEN and commit**

Run: `uv run --locked --extra dev python -m pytest tests/test_contextual_exposures.py -q`

```bash
git add src/alpha_research/contextual/exposures.py src/alpha_research/contextual/default_exposures.py tests/test_contextual_exposures.py
git commit -m "feat: add company context exposures"
```

### Task 3: Add strict as-of joins and interaction specs

**Files:**
- Create: `src/alpha_research/contextual/interactions.py`
- Test: `tests/test_contextual_interactions.py`

**Interfaces:**
- Produces: `ContextInteractionSpec(context_feature: str, exposure_name: str, output_name: str)`
- Produces: `attach_context_as_of(stock_frame, context_frame, *, trade_date_col="trade_date", available_at_col="available_at", series_age_limits=None) -> pd.DataFrame`
- Produces: `build_context_interactions(stock_frame, context_frame, exposure_frame, specs, *, symbol_col="symbol", trade_date_col="trade_date") -> pd.DataFrame`

- [ ] **Step 1: Write future-release leakage test**

A stock row dated January 15 and a context value available January 16 must not join. Add a January 16 stock row and assert it can join only after the configured session cutoff rule has made the observation visible.

- [ ] **Step 2: Write exposure-date leakage test**

Create an exposure effective January 20 and assert it cannot attach to January 15. If exposure rows use exact `trade_date`, require exact-date match; no current exposure may be backfilled into older stock dates.

- [ ] **Step 3: Write deterministic naming and missing tests**

Assert `ctx__shibor_3m_change20__x__rate_sensitivity` equals state times exposure, missing input yields missing output, and duplicate output names are rejected.

- [ ] **Step 4: Verify RED**

Run: `uv run --locked --extra dev python -m pytest tests/test_contextual_interactions.py -q`

Expected: import failure.

- [ ] **Step 5: Implement backward as-of merge**

For each context feature, stable-sort by `available_at` and use backward as-of semantics. Reject any post-join row where the selected context timestamp exceeds the stock timestamp. Apply per-feature age limits after the join.

- [ ] **Step 6: Implement exposure merge and interaction output**

Merge exposures on exact `(trade_date, symbol, exposure_name)`, pivot only requested exposure names, multiply requested pairs, and retain provenance columns describing transform/exposure versions when provided.

- [ ] **Step 7: Verify GREEN and commit**

Run: `uv run --locked --extra dev python -m pytest tests/test_contextual_interactions.py -q`

```bash
git add src/alpha_research/contextual/interactions.py tests/test_contextual_interactions.py
git commit -m "feat: add pit safe context interactions"
```

### Task 4: Add contextual feature evidence and identity

**Files:**
- Create: `src/alpha_research/contextual/evidence.py`
- Test: `tests/test_contextual_evidence.py`
- Modify: `src/alpha_research/__init__.py`
- Test: `tests/test_public_imports.py`
- Create: `docs/concepts/contextual-factors.md`

**Interfaces:**
- Produces: `ContextualFeatureEvidence`
- Produces: `contextual_feature_set_id(transform_specs, exposure_specs, interaction_specs) -> str`
- Public imports for spec types and builders from `alpha_research` only if package style permits existing top-level public exports; otherwise expose from `alpha_research.contextual` and protect with import smoke tests.

- [ ] **Step 1: Write failing identity tests**

Assert identical semantic specs with different mapping insertion order produce the same SHA-256 identity, while a changed window, exposure version, or interaction pair changes the identity.

- [ ] **Step 2: Verify RED**

Run: `uv run --locked --extra dev python -m pytest tests/test_contextual_evidence.py -q`

Expected: import failure.

- [ ] **Step 3: Implement canonical serialization**

Serialize dataclasses to sorted JSON with explicit schema/version tag. Evidence must record transform ids, exposure versions, interaction names, context series ids, rows missing by reason, and max context age observed.

- [ ] **Step 4: Add public import test and docs**

Document expected input columns, PIT requirements, missing behavior, and a minimal example using only pandas frames.

- [ ] **Step 5: Verify GREEN and commit**

Run:

```bash
uv run --locked --extra dev python -m pytest \
  tests/test_contextual_evidence.py tests/test_public_imports.py -q
```

```bash
git add src/alpha_research/contextual src/alpha_research/__init__.py tests/test_contextual_evidence.py tests/test_public_imports.py docs/concepts/contextual-factors.md
git commit -m "feat: publish contextual factor evidence"
```

### Task 5: Prove trainer compatibility without adding a model framework

**Files:**
- Create: `tests/test_contextual_ranker_integration.py`
- Modify only if required by an existing public feature-selection API: the smallest relevant `src/alpha_research/...` feature-list module.

**Interfaces:**
- Consumes existing native/XGBoost trainer/ranker public API.
- Produces no new trainer type.

- [ ] **Step 1: Write an integration test with a tiny synthetic panel**

Build base price/volume columns plus two contextual columns, train the existing ranker on several dates, and assert predictions are produced with contextual feature names included in the model/feature-set identity.

- [ ] **Step 2: Run and inspect failure**

Run: `uv run --locked --extra dev python -m pytest tests/test_contextual_ranker_integration.py -q`

Expected: either PASS immediately if the trainer already accepts arbitrary numeric columns, or FAIL at the narrow feature-registration boundary. A pass is acceptable here because this test verifies pre-existing generic capability; no production code is needed in that case.

- [ ] **Step 3: If and only if the test exposes a feature-registration boundary, add minimal opt-in registration**

Do not change default DailyWatch20 feature sets. Add contextual columns only when explicitly supplied by the caller/config.

- [ ] **Step 4: Run contextual and full repository gates**

Run:

```bash
uv run --locked --extra dev python -m pytest tests/test_contextual_*.py -q
scripts/dev/run_tests.sh lint
scripts/dev/run_tests.sh format
scripts/dev/run_tests.sh typecheck
scripts/dev/run_tests.sh typecheck-release
scripts/dev/run_tests.sh all
scripts/dev/run_tests.sh maintainability
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add tests/test_contextual_ranker_integration.py src/alpha_research docs/concepts/contextual-factors.md
git commit -m "test: prove contextual ranker integration"
```
