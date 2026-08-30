# Portfolio / Strategy-Research Boundary Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Use TDD for every new owner API.

**Goal:** Move generic target normalization, replay-period construction, native replay convenience, and delayed-fill attribution into `portfolio-backtester`, while keeping the existing `strategy-research.style_factors.portfolio_backtester_adapter` API as a thin compatibility layer.

**Architecture:** `portfolio-backtester` owns stable portfolio input/replay/execution-diagnostic semantics. `strategy-research` keeps research-specific orchestration and the `comparison_only` receipt/governance summary. The research adapter may translate names and delegate, but must not retain copies of owner algorithms.

**Spec:** `docs/superpowers/specs/2026-08-30-cross-repo-boundary-cleanup-design.md`, sections 4, 5, 7, 12-15.

## Owner API design

Add these stable public APIs in `portfolio-backtester`:

```python
positions_by_rebalance_from_targets(...)
build_position_replay_periods(...)
run_native_position_replay(...)
attribute_delayed_fills(...)
```

Suggested modules:

```text
src/portfolio_backtester/position_inputs.py
src/portfolio_backtester/position_replay.py
src/portfolio_backtester/execution_diagnostics.py
```

Do not move `owner_execution_receipt` into portfolio in this slice. Its hard-coded `canonical_status="comparison_only"` is research-governance policy, so it remains in `strategy-research` and summarizes the canonical owner result there.

---

## Task 1: Add portfolio owner tests first

**Repository:** `runchengxie/portfolio-backtester`

**Files:**
- Add: `tests/test_position_inputs.py`
- Add: `tests/test_position_replay_public.py`
- Add: `tests/test_execution_diagnostics.py`
- Modify: `tests/test_package_smoke.py`

- [ ] Add tests porting the current `strategy-research` behavior for mapping normalization/sorting, duplicate rejection, replay-period construction, native replay result, ledger/slippage forwarding, and delayed-fill attribution.
- [ ] Add at least one extra fail-closed test for negative target weights and one for a sell-side delayed-fill opportunity cost sign.
- [ ] Update package-smoke expectations for the three new owned modules and four new root entry points.
- [ ] Run the focused tests and verify RED because the owner modules/exports do not yet exist.

Expected RED command:

```bash
uv run --extra dev pytest \
  tests/test_position_inputs.py \
  tests/test_position_replay_public.py \
  tests/test_execution_diagnostics.py \
  tests/test_package_smoke.py -q
```

---

## Task 2: Implement portfolio owner APIs minimally

**Repository:** `runchengxie/portfolio-backtester`

**Files:**
- Add: `src/portfolio_backtester/position_inputs.py`
- Add: `src/portfolio_backtester/position_replay.py`
- Add: `src/portfolio_backtester/execution_diagnostics.py`
- Modify: `src/portfolio_backtester/__init__.py`

- [ ] Implement `positions_by_rebalance_from_targets` with the exact existing research-adapter behavior:
  - mapping input or DataFrame;
  - `target_weight` compatibility alias;
  - optional entry-date mapping;
  - normalized rebalance/entry dates;
  - trimmed symbols;
  - numeric non-negative weights;
  - unique `(rebalance_date, symbol)`;
  - long-only side validation;
  - deterministic sort;
  - final `assert_positions_by_rebalance_frame`.
- [ ] Implement `build_position_replay_periods` with exact current semantics: each rebalance exits at the next entry date; the final period exits on maximum available pricing date.
- [ ] Implement public `run_native_position_replay` as a convenience wrapper around `NativePositionReplayRequest` / `NativePositionReplayBackend`. Support all current request fields so downstream adapters do not need to grow backend-specific construction logic again.
- [ ] Implement `attribute_delayed_fills` with the current research semantics and no strategy-specific constants.
- [ ] Export all four APIs from the package root and update `__all__`.
- [ ] Run focused tests and package smoke; expected GREEN.

Then run repository gates:

```bash
scripts/dev/run_tests.sh lint
scripts/dev/run_tests.sh format
scripts/dev/run_tests.sh typecheck
scripts/dev/run_tests.sh all
scripts/dev/run_tests.sh maintainability
```

If the current connector cannot run a complete checkout, keep the PR Draft and state the exact limitation.

---

## Task 3: Open portfolio B1 PR

- [ ] Commit tests before production code to preserve the RED/GREEN history.
- [ ] Open a Draft PR titled similar to:

```text
[DRAFT] refactor: expose portfolio research owner APIs
```

- [ ] PR body must identify `strategy-research` as the intended first consumer and state that no strategy identity or research lifecycle policy was moved into portfolio.

---

## Task 4: Convert strategy-research adapter to thin delegation

**Repository:** `runchengxie/strategy-research`

**Dependency:** portfolio B1 must merge first, or the research PR must remain Draft pinned to the B1 head until the provider merge commit exists.

**Files:**
- Modify: `src/style_factors/portfolio_backtester_adapter.py`
- Modify: `tests/test_portfolio_backtester_adapter.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock` if dependency pin changes require it

- [ ] Add a RED boundary test that inspects the adapter source and fails while owner algorithms remain implemented locally. The test should require delegation imports from public portfolio APIs and forbid local definitions of the displaced algorithmic helpers.
- [ ] Replace `targets_to_positions_by_rebalance` body with delegation to `portfolio_backtester.positions_by_rebalance_from_targets`.
- [ ] Replace `periods_from_positions` body with delegation to `portfolio_backtester.build_position_replay_periods`.
- [ ] Replace `run_native_position_replay` body with delegation to `portfolio_backtester.run_native_position_replay`.
- [ ] Replace `attribute_delayed_fills` body with delegation to `portfolio_backtester.attribute_delayed_fills`.
- [ ] Keep `owner_execution_receipt` local because `canonical_status="comparison_only"` is research policy. It may continue to summarize owner result capabilities without reproducing execution mechanics.
- [ ] Keep public function names/signatures in `style_factors.portfolio_backtester_adapter` to avoid breaking existing research imports.
- [ ] Update the portfolio dependency pin to the merged B1 commit.
- [ ] Run the existing adapter parity tests; they should pass unchanged except for the new boundary test.

Expected focused verification:

```bash
uv run --extra dev pytest tests/test_portfolio_backtester_adapter.py -q
ruff check src/style_factors/portfolio_backtester_adapter.py tests/test_portfolio_backtester_adapter.py
```

Then run the repository full suite / configured gates in a managed checkout.

---

## Task 5: Inventory remaining style_factors extraction debt

**Repository:** `runchengxie/strategy-research`

- [ ] Classify reusable modules under `src/style_factors/` into `research-only`, `alpha-candidate`, `portfolio-candidate`, or `data-access-candidate`.
- [ ] Do not mechanically move experiment-specific code.
- [ ] Record only clearly unresolved reusable capabilities in a short debt document or existing catalog/roadmap field with owner + migration condition.
- [ ] Include the newly merged small-cap execution research core in this audit. Research-only execution studies may remain, but stable reusable execution/accounting primitives must not become a second portfolio/execution engine.

This inventory may be documentation-only if no further code should move in the same PR.

---

## Completion Criteria

- [ ] `portfolio-backtester` owns and tests the four generic APIs.
- [ ] `strategy-research` retains the same adapter public surface but no longer implements the four algorithms locally.
- [ ] `owner_execution_receipt` stays research-owned and is the only substantive local adapter policy in this slice.
- [ ] No strategy-specific identity or lifecycle policy leaks into portfolio owner code.
- [ ] Provider-first dependency pin points to a merged portfolio commit before the research PR is Ready.
- [ ] Remaining extraction debt is explicitly classified instead of silently left ambiguous.
