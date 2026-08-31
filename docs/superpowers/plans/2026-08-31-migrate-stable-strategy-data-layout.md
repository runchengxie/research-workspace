# Stable Strategy Data Layout Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the three stable strategy data namespaces into canonical `published/` locations while preserving their existing paths as reversible compatibility aliases.

**Architecture:** The canonical directories become the physical owners of the data. Existing `strategy_outputs/...` and `strategy_inputs/...` paths remain symlinks during the observation period, so current production readers and writers continue to work without a breaking change. A migration receipt records the source, target, hashes, aliases, and rollback procedure; no production release is changed in this task.

**Tech Stack:** Git, POSIX symlinks, JSON receipts, Markdown contracts, existing Python data-path audit.

**Spec:** `docs/data-path-breaking-change-register.md` and `docs/data-lifecycle-terminology.md`

## Global Constraints

- Keep `market-intel` and `strategy-pipeline` production code unchanged in this migration.
- Do not delete the old paths; retain them as compatibility aliases.
- Do not change any `latest` target or production release alias.
- Record pre/post file inventories and SHA-256 digests in a receipt outside Git.
- A later code-default cutover requires a complete shadow cycle, dry-run, contract checks, and two observation cycles.

### Task 1: Extend the migration contract

**Files:**
- Modify: `docs/data-path-breaking-change-register.md`
- Modify: `docs/data-path-migration-map.md`

- [x] Add the canonical target paths and explicitly describe the old paths as compatibility aliases.
- [x] Document rollback as replacing the alias with the recorded original directory only after stopping producers.
- [x] Add the observation gates and state that this task does not promote production code.

### Task 2: Verify the migration receipt

**Files:**
- Create outside Git: `/home/richard/data/market-data-platform/metadata/lifecycle/migrations/stable-strategy-layout-20260831.json`

- [x] Record source and target paths, source/target file counts, byte totals, per-tree file-list SHA-256, current alias targets, and `deletion_authorized: false`.
- [x] Re-run the read-only data-path audit after the migration and record its output path.

### Task 3: Validate compatibility

**Files:**
- Test: existing `tests/test_data_path_audit.py`

- [x] Run the data-path audit tests.
- [x] Resolve each old alias and verify it reaches the same `latest` and receipt files as the canonical target.
- [x] Verify the parent repository is clean and the production release directories remain untouched.

### Task 4: Commit and submit for review

- [ ] Commit the documentation changes on `feat/migrate-stable-strategy-data-layout`.
- [ ] Push the branch and open a PR; do not merge or promote production in this task.
