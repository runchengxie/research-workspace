# Branch and Worktree Retirement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Audit remaining development worktrees and non-main branches, preserve useful changes, and retire only content proven obsolete or already merged.

**Architecture:** Treat `main` and production releases as canonical state. Review each detached worktree and remote branch by commit and PR status, extract useful changes into an accepted branch when needed, then remove only the confirmed disposable worktree/ref.

**Tech Stack:** Git worktrees, GitHub CLI, repository quality gates, Markdown audit records.

**Spec:** The user's request to merge or extract useful increments and retire expired or superseded branches/worktrees.

## Global Constraints

- Do not delete uncommitted work before inspecting and preserving it.
- Do not modify the market-intel development snapshot without explicit classification.
- Do not delete production release worktrees; they are rollback targets.
- Use fast-forward or reviewed PR merges; do not force-push shared branches.

### Task 1: Audit each remaining worktree and branch

**Files:**
- Create: `docs/branch-worktree-retirement-audit.md`

- [ ] Record path, repository, commit, branch, worktree cleanliness, PR status, and disposition for each candidate.
- [ ] Compare remote refs against `git ls-remote` so stale local tracking refs are not mistaken for live remote branches.
- [ ] Stop and preserve any candidate whose content or ownership is not yet understood.

### Task 2: Merge or extract useful increments

**Files:**
- Modify: repository files only when a reviewed increment is clearly safe.
- Test: repository-specific tests and quality gates.

- [ ] For each candidate with an open PR or useful commits, inspect the diff against current `main`.
- [ ] Merge only when checks and ownership are acceptable; otherwise record the reason and keep it.
- [ ] For orphaned files with no Git metadata, copy only explicitly selected useful files into a new reviewed branch and record provenance.

### Task 3: Retire confirmed obsolete state

**Files:**
- Modify: local Git worktree metadata and remote refs only after confirmation from Tasks 1–2.

- [ ] Remove empty or orphaned worktree directories only after verifying no recoverable commit exists.
- [ ] Delete remote branches only when merged, superseded, or explicitly archived in the audit.
- [ ] Prune local remote-tracking refs after remote deletion.

### Task 4: Verify final state

- [ ] Confirm the main checkout is clean and production `current` links are unchanged.
- [ ] Confirm no unintended development worktree remains.
- [ ] Confirm audit documentation records every retained or retired item.

