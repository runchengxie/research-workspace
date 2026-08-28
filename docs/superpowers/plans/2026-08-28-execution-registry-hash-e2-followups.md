# Execution, Trial Registry, Hash Audit, and E2 Evidence Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make execution semantics comparable across research and live-execution domains, account for all PBO/DSR trials, document hash-helper ownership, and produce a reproducible E2 evidence bundle.

**Architecture:** Keep `portfolio-backtester` and `quant-execution-engine` runtime models independent. Add comparison-only fixtures at the workspace boundary, keep experiment-trial registration owned by `alpha-research`, keep the hash audit as workspace governance, and make E2 evidence an immutable artifact produced by existing pipeline/evidence contracts.

**Tech Stack:** Python 3.13, pytest, pandas, JSON/Parquet evidence artifacts, Git submodules, GitHub PRs.

**Spec:** `docs/superpowers/plans/2026-08-28-research-followups.md`

## Global Constraints

- `alpha-research` owns alpha metrics and trial accounting; `portfolio-backtester` owns portfolio economics; `quant-execution-engine` owns real execution lifecycle.
- Cross-system parity is comparison-only and must not create a runtime dependency between portfolio simulation and execution.
- PBO/DSR trial counts must come from recorded candidate history, not only the retained candidates.
- Hash helpers remain local when runtime dependency boundaries require it; consolidation requires measured dependency and release-boundary evidence.
- E2 evidence must be reproducible, content-hashed, and must not claim production readiness from unavailable live data.

---

### Task 1: Execution semantic parity fixtures

**Files:**
- Create: `tests/fixtures/execution_parity_cases.json`
- Create: `tests/test_execution_semantic_parity.py`
- Modify: `scripts/run_submodule_checks.py` only if the fixture needs a documented smoke entrypoint
- Modify: `docs/architecture-boundaries.md` or the current execution-boundary document

**Interfaces:**
- Consumes: portfolio execution outputs and qexec target/order contracts through serialized fixture data.
- Produces: deterministic comparisons for target quantity, lot rounding, T+1 availability, delayed fills, fees, and reconciliation fields.

- [ ] **Step 1: Write fixture-driven failing tests**

```python
def test_parity_case_has_identical_target_and_fill_semantics(case):
    assert case["portfolio"]["target"] == case["execution"]["target"]
    assert case["portfolio"]["fills"] == case["execution"]["fills"]
```

- [ ] **Step 2: Run the parity tests and verify they fail on missing/incorrect cases**
- [ ] **Step 3: Add the smallest fixture adapter using existing public contracts**
- [ ] **Step 4: Run parity tests plus both repository execution test suites**
- [ ] **Step 5: Commit and open a dedicated PR**

### Task 2: Recorded experiment registry for PBO/DSR

**Files:**
- Create: `alpha-research/src/alpha_research/experiment_registry.py`
- Create: `alpha-research/tests/test_experiment_registry.py`
- Modify: `alpha-research/src/alpha_research/sharpe_inference.py` or its current caller
- Modify: `alpha-research/docs/` documentation for PBO/DSR trial accounting

**Interfaces:**
- Produces: `ExperimentTrial` and `ExperimentRegistry` with stable JSON serialization and `trial_count`.
- Consumes: candidate identity, feature set, universe, holding period, parameter mapping, and result metrics.

- [ ] **Step 1: Write failing tests for deterministic registration, deduplication, and persisted trial counts**
- [ ] **Step 2: Run those tests and confirm the registry API is absent**
- [ ] **Step 3: Implement canonical trial identity and append-only registry serialization**
- [ ] **Step 4: Pass registry trial count into DSR and expose it in PBO/DSR evidence**
- [ ] **Step 5: Run alpha-research tests and document migration for callers without a registry**
- [ ] **Step 6: Commit and open a dedicated PR**

### Task 3: Hash-helper ownership audit

**Files:**
- Create: `docs/hash-helper-ownership-audit.md`
- Create: `tests/test_hash_utility_ownership.py` updates only if the audit changes the explicit allowlist

**Interfaces:**
- Consumes: all SHA-256 helper definitions and imports in the six repositories.
- Produces: an owner table, duplication classification, dependency-boundary rationale, and a rule for future additions.

- [ ] **Step 1: Write a failing governance assertion for undocumented helper definitions**
- [ ] **Step 2: Run the audit test and verify the current six helpers are reported**
- [ ] **Step 3: Add the ownership decision record and exact paths/signatures**
- [ ] **Step 4: Make the test require every allowed helper to be documented and no extra helper to appear**
- [ ] **Step 5: Run workspace quality and boundary checks**
- [ ] **Step 6: Commit and open a dedicated PR**

### Task 4: E2 evidence campaign

**Files:**
- Modify or create: `strategy-research/experiments/` campaign runner and tests
- Create: `docs/evidence/e2-execution-evidence-<date>.json`
- Create: `docs/runbooks/e2-evidence-campaign.md`
- Modify: existing E2 receipt schema only when the campaign exposes a contract gap

**Interfaces:**
- Consumes: frozen market-data contract, strategy-research experiment inputs, portfolio outputs, execution evidence, and existing promotion receipt validators.
- Produces: immutable, hashed E2 evidence with explicit sample window, data versions, experiment configuration, portfolio result, execution result, limitations, and pass/fail status.

- [ ] **Step 1: Add failing validation tests for a complete E2 manifest and missing-data refusal**
- [ ] **Step 2: Run tests and verify the campaign manifest is rejected until all required inputs are present**
- [ ] **Step 3: Implement the campaign runner using existing offline evidence tools**
- [ ] **Step 4: Run the campaign against available frozen data; record blocked dimensions instead of fabricating results**
- [ ] **Step 5: Validate the receipt with existing E2/promotion validators**
- [ ] **Step 6: Commit evidence and open a dedicated PR**

### Task 5: Final integration and cleanup

- [ ] Merge each PR in dependency order.
- [ ] Update submodule gitlinks only after the corresponding PR is merged.
- [ ] Run full workspace quality, boundary, contract, and submodule smoke checks.
- [ ] Remove every temporary worktree and merged local/remote branch created for this plan.
- [ ] Report passing tests, warnings, blocked evidence dimensions, and remaining follow-ups.
