# Selective Execution Boundary Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port only the still-valid execution import-boundary and StyleReplica ownership ratchets from the stale `feat/research-portfolio-execution-boundaries` branch onto current `main`.

**Architecture:** Keep the migration as workspace-level governance: YAML rules declare forbidden cross-owner dependencies, tests prove the scanner detects those dependencies, and the ownership rule records the remaining StyleReplica portfolio migration debt. Do not port stale evidence deletions, research implementation deletions, or old submodule pins.

**Tech Stack:** Python, pytest, YAML, Git submodules.

**Spec:** `docs/adr/0007-style-replica-ownership.md` and the reviewed delta from `github/feat/research-portfolio-execution-boundaries`.

**Global Constraints**

- Preserve all current `main` evidence, runbooks, plans, source files, and submodule pins.
- Add only zero-budget import boundaries that reflect the current owner architecture.
- Keep the existing boundary and ownership test contracts green.
- Use a feature branch and PR; do not commit directly to `main`.

---

### Task 1: Add execution import-boundary ratchets

**Files:**
- Modify: `scripts/import_boundary_rules.yml`
- Modify: `tests/test_workspace_import_boundaries.py`

- [ ] Add rules forbidding alpha → execution, portfolio → execution, execution → alpha/portfolio, and strategy-app → execution imports.
- [ ] Extend the expected rule identifiers in the current-workspace test.
- [ ] Add a fixture test proving portfolio and execution cross-imports produce the expected two boundary violations.
- [ ] Run `uv run pytest tests/test_workspace_import_boundaries.py -q`.

### Task 2: Verify completed StyleReplica ownership migration

**Files:**
- Modify: `scripts/ownership_boundary_rules.yml`
- Modify: `tests/test_workspace_ownership_boundaries.py`

- [ ] Confirm current `alpha-research` no longer contains `src/alpha_research/style_replica/portfolio.py`.
- [ ] Do not add the stale debt rule from the source branch; preserve the current ownership rules and audit assertions.
- [ ] Run `uv run pytest tests/test_workspace_ownership_boundaries.py -q`.

### Task 3: Update the ADR without changing historical artifacts

**Files:**
- Modify: `docs/adr/0007-style-replica-ownership.md`

- [ ] Add the execution-engine ownership boundary to the decision and判定规则 sections.
- [ ] Document that portfolio simulation may remain research-only and must not import qexec runtime.
- [ ] Keep the ADR status and existing compatibility guidance intact.
- [ ] Run the workspace documentation and boundary tests.

### Task 4: Verify and publish

- [ ] Run `uv run pytest tests/test_workspace_import_boundaries.py tests/test_workspace_ownership_boundaries.py -q`.
- [ ] Run `python scripts/workspace_doctor.py`.
- [ ] Review the diff to confirm no evidence, runbook, experiment, or submodule pin deletions are included.
- [ ] Commit, push, create a PR to `main`, merge if clean, then remove the feature worktree and local branch.
