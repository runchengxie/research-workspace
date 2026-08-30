# Execution Cash-Ledger Ownership Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Use TDD for each owner API.

**Goal:** Move generic settlement of historical execution fills into `portfolio-backtester` while preserving the strategy-research VWAP-receipt convenience API as a thin facade.

**Architecture:** `portfolio-backtester` owns broker-independent portfolio accounting and execution replay. The reusable `settle_execution_fills` function therefore becomes a public portfolio API. `strategy-research` keeps `settle_vwap_replay` because selecting one research capital path from VWAP receipts is research-specific orchestration; it delegates settlement to the portfolio owner. No live broker/order-state logic moves into portfolio.

**Spec:** `docs/superpowers/specs/2026-08-30-cross-repo-boundary-cleanup-design.md`, ownership matrix and strategy-research cleanup sections.

## Task 1: Define the portfolio owner contract with tests

**Repository:** `runchengxie/portfolio-backtester`

**Files:**
- Add: `tests/test_execution_ledger.py`
- Modify: `tests/test_package_smoke.py`

- [ ] Port the existing strategy-research settlement tests before production code:
  - fees + round lots + next-day sale;
  - same-day buy cannot be sold under A-share T+1;
  - insufficient cash blocks buys;
  - invalid initial capital fails closed.
- [ ] Add package-smoke expectations for module `portfolio_backtester.execution_ledger` and top-level `settle_execution_fills`.
- [ ] Run focused tests and verify RED because the module/public API does not exist on `main`.

## Task 2: Implement the portfolio owner minimally

**Repository:** `runchengxie/portfolio-backtester`

**Files:**
- Add: `src/portfolio_backtester/execution_ledger.py`
- Modify: `src/portfolio_backtester/__init__.py`

- [ ] Move the current generic `settle_execution_fills` semantics without changing the fill/mark column contract:
  - input columns `trade_date`, `instrument_id`, `side`, `filled_notional`, `average_fill_price`;
  - marks `trade_date`, `instrument_id`, `price`;
  - sell proceeds can fund same-day buys;
  - same-day buys remain unavailable for sale (T+1);
  - buys respect round lots and available cash;
  - sells may use odd lots but cannot exceed opening inventory;
  - configurable buy/sell fee and stamp-tax bps;
  - output daily cash, holdings value, NAV, blocked shares/notional and fees.
- [ ] Do not move research-specific `settle_vwap_replay` into portfolio.
- [ ] Export `settle_execution_fills` at package root.
- [ ] Run focused tests and package smoke; expected GREEN.
- [ ] Run the repository's normal lint/format/typecheck/full/maintainability gates in a complete checkout before Ready/Merge.

## Task 3: Thin the strategy-research ledger facade

**Repository:** `runchengxie/strategy-research`

**Dependency:** portfolio provider PR merges first.

**Files:**
- Modify: `src/style_factors/execution_cash_ledger.py`
- Modify: `tests/test_execution_cash_ledger.py`
- Add: `tests/test_execution_ledger_boundary.py`
- Modify: `pyproject.toml`
- Regenerate: `uv.lock`

- [ ] Add RED boundary test requiring import/delegation to public `portfolio_backtester.settle_execution_fills` and forbidding a local implementation body.
- [ ] Keep the existing research import path `style_factors.execution_cash_ledger.settle_execution_fills` as a compatibility facade that delegates to portfolio.
- [ ] Keep `settle_vwap_replay` local; it filters the research VWAP receipt table by `capital` then calls the delegated owner settlement API.
- [ ] Update portfolio dependency pin to the merged provider commit and regenerate `uv.lock`.
- [ ] Existing behavior tests must continue passing unchanged.

## Completion Criteria

- [ ] One canonical implementation of generic historical fill settlement exists in `portfolio-backtester`.
- [ ] Strategy-research preserves its old imports without retaining the accounting algorithm.
- [ ] `settle_vwap_replay` stays research-owned and delegates.
- [ ] No live broker/execution-engine responsibility moves into portfolio.
- [ ] Provider-first pin uses a default-branch-reachable commit before consumer PR becomes Ready.
