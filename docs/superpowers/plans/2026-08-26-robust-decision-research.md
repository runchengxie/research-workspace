# Robust Decision Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add counterexample-driven decision governance, reusable portfolio uncertainty primitives, and a strategy-app prediction-to-decision evaluation receipt without changing existing default behavior.

**Architecture:** The workspace owns evidence navigation and validation; `portfolio-backtester` owns generic uncertainty-aware portfolio primitives; `strategy-app` owns strategy-specific decision-evaluation composition. Alpha contracts remain unchanged in this phase.

**Tech Stack:** Python 3.12+, standard library, NumPy/pandas already present in owner repos, pytest, existing local quality gates.

**Spec:** `docs/superpowers/specs/2026-08-26-robust-decision-research-design.md`

## Global constraints

- No production catalog or lifecycle promotion changes.
- No new third-party solver dependency.
- No claim of full DRO/MILP/C&CG/Benders support.
- Existing files and public behavior remain backward compatible.
- Do not create synthetic research evidence merely to demonstrate the schema.

### Task 1: Counterexample governance

**Files:**
- Create: `strategy-research/schemas/counterexample.v1.schema.json`
- Create: `strategy-research/counterexamples/README.md`
- Modify: `strategy-research/schemas/research_case.v1.schema.json`
- Modify: `scripts/decision_governance_check.py`
- Modify: `tests/test_decision_governance_check.py`
- Modify: `docs/research-decision-governance.md`

- [ ] Add failing tests for counterexample validation, missing claim refs, and case references.
- [ ] Implement `counterexample.v1` validation and CLI scanning.
- [ ] Keep old cases valid when `counterexamples` is absent.
- [ ] Document DG8 counterexample-driven robustness.
- [ ] Run focused governance tests and full workspace gate when an executable checkout is available.

### Task 2: Portfolio uncertainty primitives

**Repository:** `runchengxie/portfolio-backtester`, branch `feat/robust-portfolio-uncertainty`.

**Files:**
- Create: `src/portfolio_backtester/robust_uncertainty.py`
- Create: `tests/test_robust_uncertainty.py`
- Modify: `src/portfolio_backtester/__init__.py`
- Modify: `docs/reference/public-api.md`
- Modify: `README.md`

- [ ] Write failing tests for identity, penalty, invalid inputs, long/short worst-case return and shape mismatch.
- [ ] Implement finite/non-negative validation and box-uncertainty primitives.
- [ ] Export the public API and document limitations.
- [ ] Run focused pytest plus lint/format/typecheck/all/maintainability when an executable checkout is available.
- [ ] Open owner PR.

### Task 3: Decision-focused evaluation receipt

**Repository:** `runchengxie/strategy-app`, branch `feat/decision-focused-evaluation`.

**Files:** choose the existing generic campaign/evidence utility location after inspecting current package structure.

- [ ] Write failing tests for direction-aware deltas, deterministic serialization and invalid metrics.
- [ ] Implement immutable typed receipt with no imports from owner internals.
- [ ] Add public import and documentation in the existing application/evidence docs.
- [ ] Run the strategy-app quality gate when an executable checkout is available.
- [ ] Open owner PR.

### Task 4: Integration and PRs

- [ ] Compare each feature branch against `main` and inspect every changed file.
- [ ] Run any locally executable isolated tests; record exact commands and results.
- [ ] Open portfolio and strategy-app owner PRs first.
- [ ] Open workspace governance PR without advancing submodule gitlinks until owner PRs merge.
- [ ] In PR descriptions, explicitly list full-repo checks that could not run in the connector-only environment.

### Deferred by design

- Full two-stage recourse optimizer.
- MILP/MIQP portfolio solver.
- Distributionally robust optimization or learning.
- C&CG/Benders solver decomposition.

These remain follow-on work triggered by a concrete strategy/scale requirement, not placeholders marketed as implementation.
