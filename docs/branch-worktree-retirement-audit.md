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

## Merged documentation

- Parent repository PR #283: capability registry and trial ledger design.
- `market-intel` PR #116: worktree-first layout documentation.

## Retained

- `market-intel` local branch `feat/worktree-first-layout` still contains two uncommitted snapshot
  artifacts. Its remote branch was deleted after PR #116 merged, but the local checkout is retained
  until those data files are explicitly archived, committed, or discarded.
- `alpha-research/feat/remove-style-replica-portfolio-owner` and
  `alpha-research/fix/adopt-size-style-signal-owner` remain remote without an associated PR; they
  require owner review before retirement.
- `portfolio-backtester/chore/sync-mdp-lazy-view` and
  `portfolio-backtester/feat/style-replica-portfolio-owner` remain remote without an associated PR;
  they require diff review before retirement.

## Follow-up

The parent and market-intel main branches advanced after the production release was created. Production
must be refreshed through the existing manual promotion command after reviewing those main changes; no
automatic production switch was performed by this cleanup.

