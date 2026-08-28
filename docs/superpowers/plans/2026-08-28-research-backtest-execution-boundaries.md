# Research Backtest and Execution Boundaries Implementation Plan

**Goal:** Move StyleReplica strategy policy, portfolio construction, and signal research responsibilities into their canonical repositories.

**Architecture:** `alpha-research` owns signals and alpha diagnostics. `strategy-app` owns StyleReplica policy. `portfolio-backtester` owns generic sleeve selection and position construction. `strategy-pipeline` owns orchestration and export, while `quant-execution-engine` remains unchanged and starts at `targets.json`.

**Validation:** Each repository is changed in an isolated worktree, submitted through a PR, merged before downstream pins are updated, and then removed.

## Completed repository sequence

- [x] `portfolio-backtester` PR #49: generic sleeve portfolio owner API.
- [x] `strategy-app` PR #48: StyleReplica policy owner.
- [x] `alpha-research` PR #39: remove final portfolio construction and add signal churn semantics.
- [x] `strategy-app` PR #49: pin merged alpha boundary owner.
- [x] `strategy-pipeline` PR #90: compose canonical owners and refresh immutable pins.
- [ ] Update this superproject's gitlinks and governance ledger.
- [ ] Run workspace contract, doctor, and delegated submodule checks.
