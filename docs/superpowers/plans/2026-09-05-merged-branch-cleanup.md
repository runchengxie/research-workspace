# Merged Branch Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow safe deletion of merged feature branches while continuing to protect `main` and tags in the `research-workspace` and `market-intel` repositories.

**Architecture:** Keep pre-push validation local and deterministic: it protects `main`, tags, and branch namespaces but does not call GitHub. Add a separate authenticated cleanup command that queries merged PRs before invoking `git push --delete`. Apply equivalent policy and tests in both repositories.

**Tech Stack:** Bash hooks, Python 3.12+, pytest, GitHub CLI (`gh`), Git.

**Spec:** The approved branch-cleanup policy from the user conversation.

## Global Constraints

- Continue forbidding deletion of `main` and tags.
- Allow deletion only for `feat/*`, `fix/*`, `hotfix/*`, `chore/*`, and `release/*`.
- Merged-PR verification belongs in the explicit cleanup command, not the ordinary pre-push hook.
- Do not bypass repository quality gates or change production releases.
- Use independent worktrees and PRs for both repositories.

### Task 1: Workspace push policy

**Files:**
- Modify: `scripts/run_pre_push_checks.py`
- Test: `tests/test_run_pre_push_checks.py` or the existing push-ref validation test location

- [ ] Add failing tests proving allowed feature-branch deletion succeeds while `main`, tags, and unapproved branch names remain rejected.
- [ ] Run the focused tests and confirm failure is caused by the current deletion rule.
- [ ] Change only the deletion branch in `_destination_issue`.
- [ ] Run focused tests, lint, and format.

### Task 2: Workspace merged-PR cleanup command

**Files:**
- Create: `scripts/cleanup_merged_branches.py`
- Test: `tests/test_cleanup_merged_branches.py`
- Modify: `README.md` or the relevant workflow documentation

- [ ] Add tests for branch-name validation, merged PR selection, unmerged PR refusal, and dry-run behavior using injected command runners.
- [ ] Implement a no-dependency CLI using `gh pr list`/`gh pr view` and `git push --delete` only after a merged PR is confirmed.
- [ ] Support `--branch`, `--remote`, `--dry-run`, and `--yes`; require explicit `--yes` for deletion.
- [ ] Document the command and its safety behavior.

### Task 3: Market-intel push policy and cleanup command

**Files:**
- Modify: `project_tools/pre_push_guard.py`
- Test: `tests/test_pre_push_guard.py`
- Create: `project_tools/cleanup_merged_branches.py`
- Test: `tests/test_cleanup_merged_branches.py`
- Modify: relevant market-intel workflow documentation

- [ ] Add the same failing deletion-policy tests and verify red.
- [ ] Apply the same deterministic destination policy.
- [ ] Implement and document the explicit merged-PR cleanup command with `--yes` confirmation.
- [ ] Run market-intel’s full local gate.

### Task 4: Local hook configuration repair and review

**Files:**
- Local-only: `research-workspace` repository config `core.hooksPath`

- [ ] Reset the main checkout’s stale hooks path to `.githooks` after code changes are merged.
- [ ] Run both repositories’ complete verification commands.
- [ ] Request/read-only review before merging each PR.
- [ ] Merge both PRs, update main checkouts, and verify the cleanup command in dry-run mode.
