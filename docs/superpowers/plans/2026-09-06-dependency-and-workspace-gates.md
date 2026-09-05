# Dependency and Workspace Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the workspace test and governance gates, then make Dependabot updates mergeable only when their owner-repository checks pass.

**Architecture:** Keep the public top-level repository independent from private submodule runtime packages. Repair stale documentation and generated governance evidence in the root repository, align submodule gitlinks with the committed manifest, and treat disk capacity as an environment prerequisite. Dependabot updates will be evaluated per owner repository rather than merged in one batch.

**Tech Stack:** Python, `uv`, `pytest`, Git submodules, GitHub Actions, GitHub CLI.

**Spec:** Current workspace test failures and the open Dependabot PR inventory reported on 2026-09-06.

## Global Constraints

- Do not commit credentials or add private package dependencies to public CI.
- Do not merge a Dependabot PR while required checks are failing.
- Keep one local `main` branch per repository and remove only branches whose changes are merged or explicitly superseded.
- Use `python scripts/run_workspace_tests.py` for workspace integration tests.
- Keep production promotion separate from dependency PR merging.

### Task 1: Reproduce and classify current gates

**Files:** None.

- [ ] Run `python scripts/run_workspace_tests.py` and record each failure.
- [ ] Run `python scripts/workspace_doctor.py` and `python src/research_contracts/smoke_contracts.py`.
- [ ] Compare the committed submodule manifest with actual gitlinks.
- [ ] Record which failures are code, generated metadata, or environment capacity.

### Task 2: Repair root documentation and generated baseline

**Files:**
- Modify: the documentation files reported by `tests/test_documentation_entrypoints.py`.
- Modify: the committed maintainability baseline reported by the baseline test.
- Test: `tests/test_documentation_entrypoints.py`, `tests/test_maintainability_governance.py`.

- [ ] Add or update focused assertions only if the intended contract is missing.
- [ ] Remove forbidden punctuation/style fragments while preserving the documented meaning.
- [ ] Regenerate the maintainability baseline with the repository generator.
- [ ] Run the two focused tests and the workspace runner.

### Task 3: Align submodule manifest and gitlinks

**Files:**
- Modify: the root submodule manifest or gitlink metadata identified by the failing contract.
- Test: `tests/test_namespace_contracts.py` and the relevant workspace doctor checks.

- [ ] Identify all mismatched owner commits.
- [ ] Confirm each target commit exists on the owner repository main branch.
- [ ] Update the manifest or root gitlink using the repository’s normal synchronization flow.
- [ ] Run the namespace and submodule consistency checks.

### Task 4: Resolve environment capacity for the maintenance test

**Files:** Modify only if the existing test cannot use a valid temporary directory with sufficient free space.

- [ ] Check available space on `/tmp` and the configured temporary root.
- [ ] Prefer running the test with a larger temporary directory.
- [ ] Change the test or threshold only if the threshold is incorrectly hard-coded for the supported environment.
- [ ] Re-run `tests/test_production_maintenance.py`.

### Task 5: Process Dependabot PRs by repository

**Files:** Owner repository branches and workflow files only when a failing check has a reproducible code or configuration cause.

- [ ] Review open Dependabot PRs in `research-workspace`, `alpha-research`, `portfolio-backtester`, and public `strategy-pipeline`.
- [ ] Merge only PRs with successful required checks and compatible dependency changes.
- [ ] For failed CodeQL or contract checks, inspect the failure before changing code.
- [ ] Re-run checks after any fix, merge successful PRs, and delete merged branches.

### Task 6: Final synchronization and promotion audit

**Files:** None unless the root gitlink changes after owner merges.

- [ ] Fetch and prune all relevant remotes.
- [ ] Confirm root and each submodule have no uncommitted files, no stale local feature branches, and no open mergeable PRs left unintentionally.
- [ ] Update root gitlinks for any merged owner-repository changes.
- [ ] Run the workspace checks again.
- [ ] Promote production only after main and the release manifest agree.

