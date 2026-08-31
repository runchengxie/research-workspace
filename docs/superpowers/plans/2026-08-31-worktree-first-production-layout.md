# Worktree-First Production Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a conventional, reliable layout in which the primary checkout contains the complete `main` codebase, agent work happens in isolated worktrees, and scheduled jobs run from an explicitly versioned production checkout.

**Architecture:** `/home/richard/code/research-workspace` remains the canonical `main` checkout and is never used as an agent scratch area. `/home/richard/code/.worktrees/` contains disposable or review worktrees. `/home/richard/code/production/` contains detached, clean deployment checkouts updated only by an explicit promotion command.

**Tech Stack:** Git worktree, Git submodules, Bash, systemd user services, Python/uv.

**Spec:** `docs/market-intel-owner-boundary.md` and repository `AGENTS.md` worktree-first rules.

## Global Constraints

- Never represent a Git submodule with a symbolic link.
- Never delete uncommitted files without first identifying and preserving them.
- Scheduled services must use production paths, not agent worktrees.
- Production promotion must record the parent and submodule revisions before and after update.
- A production checkout must remain clean and detached at an explicitly selected commit.

---

### Task 1: Restore the canonical primary checkout

**Files:**
- Modify: `/home/richard/code/research-workspace/` Git worktree state
- Verify: parent and all submodule worktrees

- [ ] Remove only the two known compatibility symlinks after confirming service paths have a production target.
- [ ] Populate the primary checkout from `github/main` and initialize its submodules normally.
- [ ] Verify the primary checkout is a complete, clean checkout and no submodule path is a symlink.

### Task 2: Define agent worktree placement

**Files:**
- Modify: `AGENTS.md`
- Modify: each maintained submodule `AGENTS.md`
- Verify: `.gitignore` and `git worktree list`

- [ ] State that the primary checkout is a complete stable baseline, not an empty control directory.
- [ ] State that new agent worktrees belong under `/home/richard/code/.worktrees/` and must be created with `git worktree add`.
- [ ] State that untracked outputs belong under ignored artifact/data locations or outside Git, never in a disposable worktree without a retention policy.

### Task 3: Add explicit production promotion workflow

**Files:**
- Create: `scripts/promote-production.sh`
- Create: `docs/production-update.md`
- Modify: `AGENTS.md`

- [ ] Implement a dry-run-capable promotion command that fetches `main`, checks a clean production checkout, updates the parent and submodules, and prints the resulting revision manifest.
- [ ] Document that `git push` updates the remote only; production changes only after promotion.
- [ ] Document preflight, promotion, rollback, and post-promotion verification commands.

### Task 4: Point scheduled execution at production

**Files:**
- Modify: affected systemd user unit files and environment files
- Verify: `systemctl --user daemon-reload` and unit command paths

- [ ] Replace stale development paths with explicit production paths where a service is intended to be operational.
- [ ] Leave research-only services explicitly classified rather than silently switching them.
- [ ] Reload user units and verify the key daily/weekly entry points resolve to production.

### Task 5: Verify and record the final state

**Files:**
- Verify: parent, submodules, production checkout, service definitions

- [ ] Confirm primary `main` and production revision manifest.
- [ ] Confirm all production worktrees are clean and detached.
- [ ] Run the relevant repository doctor/contract tests and a dry-run production promotion.
- [ ] Record any intentionally retained dirty research data outside the code promotion path.

