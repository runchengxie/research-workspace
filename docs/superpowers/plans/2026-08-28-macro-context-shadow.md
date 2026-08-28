# Macro Context Shadow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible market-wide A-share shadow experiment that compares baseline, context state, context interactions, and PIT fundamentals across frozen 5/20/60-trading-day horizons with 20 days primary.

**Architecture:** The top-level `strategy-research` runner composes published owner APIs only. It reads A-share and `cn_context` current contracts, asks `alpha-research` to construct contextual feature frames and train/score challengers, asks `portfolio-backtester` for existing cost/turnover/capacity outputs, and writes ignored run artifacts plus tracked experiment config/evidence navigation. Production strategy defaults and execution contracts remain untouched.

**Tech Stack:** Python 3, pandas, existing `market_data_platform`, `alpha_research`, `portfolio_backtester`, strategy-research experiment/evidence conventions, pytest/YAML.

**Spec:** `docs/superpowers/specs/2026-08-28-contextual-alpha-platform-design.md`

## Global Constraints

- Experiment lifecycle starts as `exploration`; `production_eligible=false`.
- Universe is the published A-share PIT by-date universe.
- Frozen horizons are 5, 20, and 60 trading days; 20 days is the only primary selection horizon.
- Challenger sets are `C0`, `C1`, `C2`, `C3` exactly as defined by the spec.
- Final OOS is run only after feature, transform, exposure, interaction, model, and cost specs are frozen.
- Reconstructed context may be explored but any conclusion depending on it is not promotion eligible.
- Runner must not implement generic data, alpha, portfolio, or execution logic.
- New experiment code follows TDD where behavior changes are introduced.

---

### Task 1: Register the experiment identity and frozen configuration

**Files:**
- Create: `strategy-research/experiments/macro_context_shadow/README.md`
- Create: `strategy-research/experiments/macro_context_shadow/experiment.yml`
- Create: `strategy-research/experiments/macro_context_shadow/__init__.py`
- Modify: `strategy-research/catalog.json`
- Modify: `strategy-research/README.md`
- Test: `strategy-research/tests/test_macro_context_shadow_config.py`

**Interfaces:**
- Produces stable experiment id `macro_context_shadow_v1`.
- Produces config sections `horizons`, `challengers`, `context_features`, `exposures`, `interactions`, `model`, `cost`, `oos`, `regimes`.

- [ ] **Step 1: Write failing config-schema tests**

Assert horizons equal `[5, 20, 60]`, primary is `20`, challenger keys are exactly `C0..C3`, lifecycle is `exploration`, and no production eligibility flag can be true.

- [ ] **Step 2: Verify RED**

Run: `uv run --project strategy-research --extra dev python -m pytest tests/test_macro_context_shadow_config.py -q`

Expected: experiment files do not exist.

- [ ] **Step 3: Write the frozen experiment config**

`C0` names the existing price/volume + stock-level baseline feature group through configuration. `C1` adds context state, `C2` adds interaction columns, `C3` adds the existing PIT fundamental group. Do not duplicate feature calculation code.

- [ ] **Step 4: Register experiment and failure conditions**

README must state the thesis, time semantics, reconstructed-data limitation, and the six failure conditions from the approved spec. Catalog entry must remain non-production.

- [ ] **Step 5: Verify GREEN and commit**

Run: `uv run --project strategy-research --extra dev python -m pytest tests/test_macro_context_shadow_config.py -q`

```bash
git add strategy-research/experiments/macro_context_shadow strategy-research/catalog.json strategy-research/README.md strategy-research/tests/test_macro_context_shadow_config.py
git commit -m "docs: register macro context shadow experiment"
```

### Task 2: Add contract loading and promotion-safe preflight

**Files:**
- Create: `strategy-research/experiments/macro_context_shadow/run_contextual_alpha_shadow.py`
- Test: `strategy-research/tests/test_macro_context_shadow_runner.py`

**Interfaces:**
- Produces: `load_inputs(data_root, config) -> ContextShadowInputs`
- Produces: `preflight_context(inputs, *, require_promotion_safe: bool) -> ContextShadowAudit`

- [ ] **Step 1: Write failing two-contract loading test**

Use temporary published contracts and assert the runner loads `market="a_share"` and `market="cn_context"` independently. Assert it refuses a missing `context_pit` asset with a clear error.

- [ ] **Step 2: Write reconstructed-history gate test**

Supply a context PIT audit containing `reconstructed_series`. Assert exploratory mode records the limitation while promotion-safe mode blocks the run.

- [ ] **Step 3: Verify RED**

Run: `uv run --project strategy-research --extra dev python -m pytest tests/test_macro_context_shadow_runner.py -k 'contract or reconstructed' -q`

Expected: runner module/function missing.

- [ ] **Step 4: Implement owner-API-only input loading**

Use `PublishedAssetContract` for both current contracts. Use market-data public PIT loader; do not open provider raw paths from the experiment.

- [ ] **Step 5: Verify GREEN and commit**

Run: `uv run --project strategy-research --extra dev python -m pytest tests/test_macro_context_shadow_runner.py -k 'contract or reconstructed' -q`

```bash
git add strategy-research/experiments/macro_context_shadow/run_contextual_alpha_shadow.py strategy-research/tests/test_macro_context_shadow_runner.py
git commit -m "feat: preflight macro context shadow inputs"
```

### Task 3: Build C0/C1/C2/C3 feature variants through alpha APIs

**Files:**
- Modify: `strategy-research/experiments/macro_context_shadow/run_contextual_alpha_shadow.py`
- Test: `strategy-research/tests/test_macro_context_shadow_runner.py`

**Interfaces:**
- Produces: `build_feature_variants(inputs, config) -> Mapping[str, pd.DataFrame]`
- Every variant has identical `(trade_date, symbol, label)` rows; only opt-in feature columns differ.

- [ ] **Step 1: Write failing variant-increment tests**

Assert `features(C0) ⊂ features(C1) ⊂ features(C2) ⊂ features(C3)` according to configured groups. Assert C2 contains configured `ctx__...__x__...` columns and no row has a context provenance timestamp later than its trade date.

- [ ] **Step 2: Verify RED**

Run: `uv run --project strategy-research --extra dev python -m pytest tests/test_macro_context_shadow_runner.py -k feature_variants -q`

Expected: function missing.

- [ ] **Step 3: Implement composition only**

Call `alpha_research.contextual` transform/exposure/interaction builders. Reuse existing market-wide price/volume and PIT fundamental feature APIs. If no public market-wide base-frame API exists, stop and expose the smallest owner API in `alpha-research`; do not reimplement it under `strategy-research`.

- [ ] **Step 4: Verify GREEN and commit**

Run: `uv run --project strategy-research --extra dev python -m pytest tests/test_macro_context_shadow_runner.py -k feature_variants -q`

```bash
git add strategy-research/experiments/macro_context_shadow/run_contextual_alpha_shadow.py strategy-research/tests/test_macro_context_shadow_runner.py
git commit -m "feat: build contextual challenger variants"
```

### Task 4: Add frozen multi-horizon scoring and final-OOS protocol

**Files:**
- Modify: `strategy-research/experiments/macro_context_shadow/run_contextual_alpha_shadow.py`
- Create: `strategy-research/experiments/macro_context_shadow/protocol.py`
- Test: `strategy-research/tests/test_macro_context_shadow_protocol.py`

**Interfaces:**
- Produces: `ContextShadowProtocol`
- Produces: `score_variants(feature_variants, protocol) -> ContextShadowScores`

- [ ] **Step 1: Write protocol immutability tests**

Assert primary horizon 20 cannot be changed by CLI flags in canonical mode. Assert final OOS dates are excluded from model/feature selection inputs. Assert 5/60-day results are diagnostics and cannot choose the winner in the result object.

- [ ] **Step 2: Verify RED**

Run: `uv run --project strategy-research --extra dev python -m pytest tests/test_macro_context_shadow_protocol.py -q`

Expected: protocol module missing.

- [ ] **Step 3: Implement protocol using existing research backends**

Use current walk-forward/CPCV/PBO APIs rather than adding statistical implementations. Protocol records training window, embargo, folds, model parameters, feature-set ids, cost assumptions, and final-OOS boundaries.

- [ ] **Step 4: Add synthetic no-leakage scoring test**

Create a tiny panel where a future-only feature would perfectly predict labels if leaked. Assert canonical as-of construction prevents that column/value from appearing before availability and the score path remains valid.

- [ ] **Step 5: Verify GREEN and commit**

Run: `uv run --project strategy-research --extra dev python -m pytest tests/test_macro_context_shadow_protocol.py -q`

```bash
git add strategy-research/experiments/macro_context_shadow/protocol.py strategy-research/experiments/macro_context_shadow/run_contextual_alpha_shadow.py strategy-research/tests/test_macro_context_shadow_protocol.py
git commit -m "feat: freeze macro context shadow protocol"
```

### Task 5: Add portfolio, cost, capacity, exposure, and regime evaluation

**Files:**
- Modify: `strategy-research/experiments/macro_context_shadow/run_contextual_alpha_shadow.py`
- Create: `strategy-research/experiments/macro_context_shadow/reporting.py`
- Test: `strategy-research/tests/test_macro_context_shadow_reporting.py`

**Interfaces:**
- Produces report metrics for IC/RankIC, net return, risk-adjusted result, turnover, cost drag, capacity proxy, industry/style drift, and frozen regime slices.

- [ ] **Step 1: Write failing report-shape tests**

Assert each challenger/horizon has prediction metrics and that portfolio metrics are present for the primary 20-day horizon. Assert regime keys are exactly `rates_up`, `rates_down`, `credit_expanding`, `credit_contracting`, `industrial_accelerating`, `industrial_decelerating`, `high_vol`, `low_vol`, `benchmark_uptrend`, `benchmark_downtrend`.

- [ ] **Step 2: Verify RED**

Run: `uv run --project strategy-research --extra dev python -m pytest tests/test_macro_context_shadow_reporting.py -q`

Expected: reporting module missing.

- [ ] **Step 3: Reuse portfolio-backtester public APIs**

Call existing portfolio construction, turnover/cost, capacity, and exposure functions. Add a new `portfolio-backtester` regime summary PR only if a required metric cannot be computed through current public outputs without importing internal modules.

- [ ] **Step 4: Freeze regime rules outside final OOS**

Compute direction/threshold parameters using pre-final-OOS data or fixed sign rules. Persist the rules in report metadata and do not recompute them from final OOS.

- [ ] **Step 5: Verify GREEN and commit**

Run: `uv run --project strategy-research --extra dev python -m pytest tests/test_macro_context_shadow_reporting.py -q`

```bash
git add strategy-research/experiments/macro_context_shadow/reporting.py strategy-research/experiments/macro_context_shadow/run_contextual_alpha_shadow.py strategy-research/tests/test_macro_context_shadow_reporting.py
git commit -m "feat: evaluate macro context shadow challengers"
```

### Task 6: Add evidence receipt, CLI entry, and research-layer gates

**Files:**
- Modify: `strategy-research/experiments/macro_context_shadow/run_contextual_alpha_shadow.py`
- Create: `strategy-research/experiments/macro_context_shadow/evidence.py`
- Test: `strategy-research/tests/test_macro_context_shadow_evidence.py`
- Modify: `docs/roadmap.md`

**Interfaces:**
- Produces ignored run outputs under the configured research artifact root.
- Produces tracked evidence navigation only after a real run exists; no synthetic performance numbers are committed.

- [ ] **Step 1: Write failing receipt tests**

Receipt must record both current-contract hashes, selected context vintages, `revision_covered`, reconstructed series, contextual feature-set id, exposure versions, model version, horizons, OOS boundaries, cost assumptions, git/source identities, and failure-condition evaluation.

- [ ] **Step 2: Verify RED**

Run: `uv run --project strategy-research --extra dev python -m pytest tests/test_macro_context_shadow_evidence.py -q`

Expected: evidence module missing.

- [ ] **Step 3: Implement receipt and abstain/reject logic**

If stable incremental evidence is absent or promotion-safe context is unavailable, report `no_view`/`rejected` according to the frozen failure conditions. Do not infer missing evidence as pass.

- [ ] **Step 4: Add CLI parsing and `--dry-run`**

`--dry-run` resolves contracts/config/protocol and prints or writes no performance claim. Canonical mode does not permit changing the frozen primary horizon or challenger definitions.

- [ ] **Step 5: Run experiment tests and workspace gates**

Run:

```bash
uv run --project strategy-research --extra dev python -m pytest tests -q
python scripts/decision_governance_check.py
python scripts/run_quality_checks.py --profile hard
python scripts/run_submodule_checks.py --profile smoke
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```bash
git add strategy-research/experiments/macro_context_shadow strategy-research/tests docs/roadmap.md
git commit -m "feat: add market wide macro context shadow"
```
