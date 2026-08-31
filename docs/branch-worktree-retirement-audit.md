# Branch and Worktree Retirement Audit

Date: 2026-08-31

## Result

The cleanup removed only state proven merged, superseded, empty, or orphaned with no code delta.
Production release worktrees remain intentionally available for rollback.

## Retired

- Closed and deleted the empty MDP follow-up PR #82 after rebasing showed its effective diff was
  already present on `market-data-platform/main`.
- Retired `/home/richard/code/.worktrees/mdp-context-official`; its useful official-context work was
  already represented on current MDP main, and the follow-up PR had an empty effective diff.
- Moved the broken Git-pointer directory `alpha-fundamental-a2` to the desktop trash after comparing
  tracked source files with current `alpha-research/main`; only an older `AGENTS.md` and generated
  caches differed.
- Removed the empty `etf-history-backfill` directory.
- Deleted merged remote branches from `market-data-platform`: `feat/context-core-tushare-macro`,
  `feat/context-official-energy`, `feat/l2-lazy-canonical`, `fix/fund-portfolio-duplicate-guard`,
  `fix/nbs-indicator-label`, `fix/nbs-stream-endpoint`, `fix/tushare-context-columns`, and
  `fix/tushare-future-release`.
- Deleted merged `alpha-research/feat/contextual-factors`.
- Pruned local remote-tracking refs for deleted branches and old merged production/documentation branches.
- Moved the one-off `/home/richard/transfer/etf-minute-fetcher` staging directory to the desktop
  trash; it was not a Git repository and contained only an ETF minute-data import handoff.

## Merged documentation

- Parent repository PR #283: capability registry and trial ledger design.
- `market-intel` PR #116: worktree-first layout documentation.

## Retained

- `alpha-research/fix/adopt-size-style-signal-owner` was extracted into the reusable
  size-style API and merged as PR #50; the parent gitlink is being synchronized separately.
- The rebased effective diffs for `alpha-research/feat/remove-style-replica-portfolio-owner` and
  `portfolio-backtester/feat/style-replica-portfolio-owner` were empty because their changes were
  already present on the respective main branches; both branches were retired.
- `portfolio-backtester/chore/sync-mdp-lazy-view` was also empty after comparison and was retired.

## Follow-up

The parent and market-intel main branches advanced after the production release was created. Production
must be refreshed through the existing manual promotion command after reviewing those main changes; no
automatic production switch was performed by this cleanup.
