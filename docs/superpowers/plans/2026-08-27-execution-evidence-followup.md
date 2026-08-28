# Execution Evidence Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the small-cap × low-turnover exploration compare strategies and execution paths using the same constrained ledger, with explicit impact and delayed-fill evidence.

**Architecture:** Keep signal construction in `strategy-research`. Extend the existing execution adapter and owner backend so the same slippage model can flow through native ledger replay, reconciliation, and capacity tests. Add research-only attribution and double-sort outputs; do not change signal definitions or promote a canonical backend until the evidence is comparable.

**Tech Stack:** Python 3.13, pandas, NumPy, pytest, portfolio-backtester.

**Spec:** The five follow-up objectives in the user request: propagate impact, attribute delayed fills, compare three arms, run size × turnover double-sort, and assess owner-ledger canonicalization.

## Global Constraints

- Preserve existing signal definitions, eligibility rules, target count, buffer count, and default zero-impact historical outputs.
- Use the public owner execution contract; do not import private implementation modules across repositories.
- Keep all new research outputs deterministic and write tests before production code.
- Do not select parameters from the already-inspected 2024–2026 holdout.

---

### Task 1: Propagate slippage through owner ledger and all ledger matrices

**Files:**
- Modify: `portfolio-backtester/src/portfolio_backtester/backends/native.py`
- Modify: `strategy-research/style_factors/portfolio_backtester_adapter.py`
- Modify: `strategy-research/experiments/style_factors/small_cap_low_turnover_exploration_20260826.py`
- Test: owner backend and strategy exploration tests

- [x] Add failing tests for passing a slippage model through `NativePositionReplayRequest`, and for nonzero impact appearing in reconciliation and capacity outputs.
- [x] Implement the request field and forward it to adjusted-NAV execution.
- [x] Thread `impact_bps` through reconciliation and capacity ladder while preserving the default `0.0` behavior.
- [x] Run focused and full tests.

### Task 2: Add delayed-fill opportunity-cost attribution

**Files:**
- Create or modify: `strategy-research/style_factors/portfolio_backtester_adapter.py`
- Test: `strategy-research/tests/test_portfolio_backtester_adapter.py`
- Modify: exploration runner and report output

- [x] Add a failing synthetic test covering requested quantity, filled quantity, fill delay, reference return during delay, temporary impact, and unfilled quantity.
- [x] Implement a pure attribution helper over orders, fills, and pricing frames.
- [x] Emit aggregate attribution columns in ledger outputs and a detailed CSV when the runner is used.
- [x] Verify no attribution is reported as alpha; label it execution-path evidence.

### Task 3: Compare composite, small-cap-only, and large-cap control on one ledger

**Files:**
- Modify: exploration runner and report
- Test: exploration tests

- [x] Add failing assertions that the constrained comparison contains all three arms with identical execution configuration and impact metadata.
- [x] Reuse existing target construction for the three signal columns and add ledger rows rather than a second simulator.
- [x] Add incremental return columns versus the two controls.
- [x] Run the focused suite.

### Task 4: Add the size × turnover double-sort research output

**Files:**
- Create: `strategy-research/style_factors/size_turnover_double_sort.py`
- Create: corresponding tests
- Modify: exploration runner and report

- [x] Add failing tests for 5×5 bucket assignment, within-size turnover ordering, and missing-data handling.
- [x] Implement deterministic bucket assignment using formation-date cross-sections and return a long-form 25-cell table.
- [x] Add the output to the exploration artifacts without changing the production candidate signal.
- [x] Run tests and validate monotonicity diagnostics.

### Task 5: Decide owner backend status from evidence

**Files:**
- Modify: exploration report and metadata
- Test: adapter and integration tests

- [x] Add a capability receipt showing whether owner ledger output has daily NAV, orders, fills, partial fills, slippage, and matching periods.
- [x] Keep owner ledger as comparison-only until Tasks 1–3 agree on dates, exit semantics, cash, and cost accounting.
- [x] Document the explicit promotion criteria and remaining gaps.
