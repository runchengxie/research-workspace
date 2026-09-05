# strategy-pipeline-internal Migration Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reconcile the migration manifest, documentation ownership evidence, and production-readiness record so the repository states only what the current workspace can verify.

**Architecture:** Treat the frozen internal repository as an archive/recovery source, while treating the owner repositories and public `strategy-pipeline` as the active implementation surface. Close repository-local metadata inconsistencies, preserve historical evidence, and leave the production pointer unchanged until a separately authorized promotion is available.

**Tech Stack:** Markdown, JSON, Python/pytest, Git worktrees, existing workspace release scripts.

**Spec:** `docs/migrations/strategy-pipeline-internal-retirement-record.md` and `docs/evidence/strategy-pipeline-internal-retirement-final-20260905.json`.

## Global Constraints

- Do not copy private strategy implementation into public `strategy-pipeline`.
- Preserve the frozen internal tag and historical source commit as recovery references.
- Do not change `/home/richard/code/production/research-workspace/current` without an explicit production promotion decision.
- Every status claim must be backed by a fresh command or an existing checked-in evidence file.

---

### Task 1: Close the workspace migration manifest

**Files:**
- Modify: `docs/migrations/strategy-pipeline-internal-migration-manifest.md`
- Test: `tests/test_strategy_pipeline_internal_migration_manifest.py`

- [x] Change the manifest header from `status: active` to `status: retired`.
- [x] Add separate closeout counts while preserving the frozen source ownership classification.
- [x] Remove the two stale `migration_pr: pending` values for `docs/metric-ownership.md` and `docs/strategy-catalog.md`.
- [x] Add a note that the source repository ownership manifest is frozen historical evidence.
- [x] Run the focused migration-manifest test and confirm it passes.

### Task 2: Clarify current documentation status

**Files:**
- Modify: `docs/strategy-catalog.md`
- Modify: `docs/migrations/strategy-pipeline-internal-retirement-record.md`
- Modify: `docs/evidence/strategy-pipeline-internal-retirement-final-20260905.json`
- Test: `tests/test_strategy_pipeline_internal_retirement_record.py`

- [x] Replace wording that says the migration is still in progress with wording that distinguishes active migration completion from archive-only retention.
- [x] Record the locally observed production pointer separately from the historical claimed release and mark the mismatch as a promotion follow-up.
- [x] Add machine-readable fields for the observed local production workspace release and release-match status.
- [x] Run the focused retirement-record test and confirm it passes.

### Task 3: Verify all active surfaces and release readiness

**Files:**
- No source changes expected.

- [x] Run the focused workspace migration/retirement tests: 45 passed.
- [x] Run the public `strategy-pipeline` tests: 55 passed.
- [x] Re-run the owner-target existence check: 113 code migrations and 16 documentation targets, 0 missing.
- [x] Run the production promotion dry-run and confirm the actual current pointer.
- [x] Confirm that no active import or runtime path references `strategy_pipeline_internal`.

### Task 4: Review and hand off production promotion

**Files:**
- No automatic production symlink change.

- [x] Inspect the final diff and verify no production directory was modified.
- [x] Report the exact promotion command and current/target release identities.
- [ ] Leave the goal open until the production pointer is reconciled after explicit promotion approval.
