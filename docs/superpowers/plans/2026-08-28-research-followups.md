# Research Follow-ups Implementation Plan

> **For agentic workers:** Use isolated worktrees and a separate PR for each repository change. Keep execution evidence comparison-only until canonical-path equivalence is proven.

**Goal:** Finish the safe follow-up work after the three-layer ownership migration without weakening research, portfolio, or execution boundaries.

**Architecture:** Review execution-impact work before merging it. Make repository tests independent of checkout paths. Keep reusable hashing in an explicit owner. Add semantic parity fixtures between simulated and execution-ledger behavior, while treating E2 promotion evidence as a separate data-backed campaign.

**Tech Stack:** Python, pytest, Ruff, ty, uv, Git worktrees, GitHub pull requests.

**Spec:** `docs/adr/0007-style-replica-ownership.md` and `docs/roadmap.md`.

## Global Constraints

- `alpha-research` owns signal research and diagnostics.
- `portfolio-backtester` owns portfolio construction and simulated economics.
- `quant-execution-engine` owns real order lifecycle, broker behavior, and reconciliation.
- `strategy-pipeline` remains orchestration-only.
- Every repository change uses a separate worktree and PR.
- No E2 result is promoted without reproducible input, output, and lineage receipts.

### Task 1: Review open execution PRs

- [ ] Inspect PR #224 and PR #225 file-by-file.
- [ ] Verify that owner-ledger output remains comparison-only.
- [ ] Verify dependency pins and tests use merged revisions.
- [ ] Record concrete blockers or approve only after local reproduction.

### Task 2: Make tests worktree-independent

- [ ] Replace hard-coded repository path assertions with repository-root discovery or package metadata.
- [ ] Add regression tests that run from a non-canonical worktree path.
- [ ] Run each affected repository's full local gate.

### Task 3: Audit duplicate hash helpers

- [ ] Inventory all `file_sha256` and `sha256_file` definitions.
- [ ] Classify identical helpers versus intentionally local wrappers.
- [ ] Move only safe shared behavior to the existing contracts owner.
- [ ] Update ownership budgets and tests.

### Task 4: Add execution semantic parity fixtures

- [ ] Cover lot-size rounding, T+1, suspended/limit securities, partial fills, fees, and slippage.
- [ ] Compare normalized semantics, not internal runtime types.
- [ ] Keep the owner ledger explicitly non-canonical until equivalence is demonstrated.

### Task 5: Prepare E2 evidence campaign

- [ ] Freeze candidate, universe, date range, data revisions, execution rules, and cost model.
- [ ] Produce test, final OOS, CPCV, capacity, and lineage receipts.
- [ ] Add a reproducible promotion checklist and abstain when evidence is incomplete.
