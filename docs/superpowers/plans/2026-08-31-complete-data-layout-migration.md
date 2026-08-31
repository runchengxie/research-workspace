# Complete Data Layout Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the safe second-round classification of mixed research and pipeline artifact directories without breaking existing reports or producers.

**Architecture:** Physical data is moved to canonical lifecycle roots and legacy paths become symlinks. Existing code and cron defaults remain compatible until a separate cross-repository change proves canonical reads through shadow execution and observation cycles.

**Tech Stack:** POSIX filesystem, symlinks, JSON migration receipts, Markdown contracts, existing `data_path_audit.py`, Git PR workflow.

**Spec:** `docs/data-lifecycle-terminology.md`, `docs/data-path-migration-map.md`, and `docs/data-path-breaking-change-register.md`

## Global Constraints

- Never delete research or run data in this migration.
- Keep old paths readable and writable through compatibility symlinks.
- Do not modify production release directories or current aliases.
- Do not claim a production cutover until shadow read, dry-run, contract checks, and two observation cycles pass.

### Task 1: Audit and classify mixed roots

- [x] Inspect consumers, sizes, file counts, and symlinks for `watchlist20/research`, `strategy-pipeline/artifacts`, and `market-data-platform/research`.
- [x] Confirm no active process holds the directories before moving them.
- [x] Classify research output as `experiments/strategies/watchlist20` and pipeline namespaces as `assets`, `cache`, `metadata`, `reports`, `runs`, and `snapshots`.

### Task 2: Move entities with compatibility aliases

- [x] Move `strategy_outputs/watchlist20/research` to `experiments/strategies/watchlist20` and recreate the old path as a symlink.
- [x] Move each `strategy-pipeline/artifacts/*` namespace to the corresponding project data-root directory and recreate each old path as a symlink.
- [x] Keep `market-data-platform/research` compatibility symlinks because its physical contents were already migrated.

### Task 3: Record and verify migration

- [x] Write `/home/richard/data/market-data-platform/metadata/lifecycle/migrations/research-and-pipeline-artifacts-layout-20260831.json` with inventory hashes and rollback instructions.
- [x] Regenerate `/home/richard/data/market-data-platform/metadata/lifecycle/path-audit-20260831.json`.
- [x] Verify old and canonical paths, `latest` targets, receipts, and production release cleanliness.

### Task 4: Document remaining breaking-change gates

- [x] Update the parent migration map and breaking-change register with canonical locations and alias status.
- [x] Record that source defaults and cron configuration still require a separate opt-in canonical-path change.
- [ ] After a future code PR, run one complete shadow cycle, a report dry-run, contract checks, and two observation cycles before removing aliases.

### Task 5: Review and merge documentation

- [ ] Run `pytest tests/test_data_path_audit.py -q` and `git diff --check`.
- [ ] Commit the documentation, push a feature branch, and merge its PR into `main`.
