# Production Release Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Manage research-workspace and market-intel production code through immutable release worktrees, a `current` pointer, automatic fetch notifications, and explicit human or agent promotion.

**Architecture:** Each production repository has `releases/<commit>` worktrees and a relative `current` symlink. Services only reference `current`. A fetch-only systemd timer reports new remote revisions; promotion creates and validates a release, then atomically switches `current` without deleting prior releases.

**Tech Stack:** Git worktree, Bash, systemd user units, uv, `flock`.

**Spec:** `docs/production-update.md`.

## Global Constraints

- Fetch never changes the running release.
- Promotion never runs while another promotion is active.
- Existing release directories are immutable and are not deleted automatically.
- The running `current` release must be clean and have a recorded revision manifest.
- Services must reference `current`, never an agent worktree.

---

### Task 1: Add release-aware promotion and fetch audit commands

**Files:**
- Create: `scripts/promote-production.sh`
- Create: `scripts/check-production-updates.sh`
- Modify: `docs/production-update.md`
- Modify: `AGENTS.md`

- [ ] Add `--dry-run` support to promotion for both repositories.
- [ ] Make promotion create `releases/<commit>`, validate it, and atomically replace `current`.
- [ ] Make promotion retain previous releases and print a two-repository manifest.
- [ ] Add fetch-only update detection with exit status suitable for systemd notifications.
- [ ] Document manual promotion, fetch-only checks, rollback, and release retention.

### Task 2: Add fetch-only systemd monitoring

**Files:**
- Create: `/home/richard/.config/systemd/user/research-production-update-check.service`
- Create: `/home/richard/.config/systemd/user/research-production-update-check.timer`

- [ ] Run the fetch-only check on a daily schedule.
- [ ] Keep the check non-mutating with respect to running production code.
- [ ] Write an update report to the user log and use failure status only for operational alerting.

### Task 3: Migrate existing production worktrees

**Files:**
- Modify: `/home/richard/code/production/research-workspace/`
- Modify: `/home/richard/code/production/market-intel/`
- Modify: affected systemd unit paths

- [ ] Preserve the current revisions as the first release directories.
- [ ] Create relative `current` symlinks.
- [ ] Point all operational units at `current`.
- [ ] Keep `.env.local` outside release code and load it explicitly where needed.

### Task 4: Verify release and rollback behavior

**Files:**
- Verify: production manifests, symlinks, systemd units, Git worktree registrations

- [ ] Confirm both current releases are clean and services resolve through `current`.
- [ ] Run dry-run update checks and promotion checks.
- [ ] Confirm rollback changes only the pointer and leaves prior releases intact.
- [ ] Confirm agent worktrees cannot be reached through service paths.

