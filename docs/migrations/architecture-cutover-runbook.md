# Architecture cutover runbook

> status: target remotes initialized; consumer cutover still pending
> scope: local staging → approved GitHub repositories

This runbook is the final operational handoff for the repository consolidation.
The local staging repositories and compatibility gates are already validated;
the commands below require an explicit decision to create, rename, push, or
change remote repositories.

## Target layout

| Target | Visibility | Contents | Source mapping |
| --- | --- | --- | --- |
| `quant-platform` | public | reusable data interfaces, alpha/research primitives, portfolio/backtest, orchestration, public execution interfaces, contracts and CI | `market-data-platform`, `alpha-research`, `portfolio-backtester`, generic `strategy-pipeline`, public parts of `quant-execution-engine`, generic microstructure code |
| `quant-research` | private | strategy registry, strategy-specific logic, proprietary features/labels, experiments, model selection, evidence and private configuration | `strategy-research`, `strategy-app`, private parts of alpha/microstructure/pipeline |
| `market-intel` | private application | market context, report assembly, dashboards, delivery, freshness and recovery | existing independent repository; consumes versioned artifacts only |
| `research-workspace` | integration-only | version manifest, compatibility checks, contract smoke tests, architecture/CI metadata and rollback pointers | existing superproject; legacy submodules remain until cutover gates pass |

## Preconditions

Do not begin the remote cutover until all of these are true:

- public staging tests and Ruff pass (`31 passed`);
- private staging tests pass (`26 passed`, adapter `3 passed`);
- formal DailyWatch20 publication is accepted by `market-intel`;
- `market-intel` boundary and consumer gates pass (`2` boundary tests,
  `112` broader consumer tests);
- workspace doctor reports zero errors;
- architecture scanner reports zero errors;
- production `current` pointers and artifact rollback have been rehearsed;
- license, visibility, GitHub Actions, CODEOWNERS, and repository-owner
  decisions have been explicitly approved.

The technical preconditions are satisfied. The target `quant-platform` public
and `quant-research` private repositories have now been created and pushed.
The current workspace and legacy consumers have not yet been switched to use
them as authoritative sources.

## Ordered cutover

1. Keep the created `quant-platform` public repository protected by its green
   CI and verify branch protection, ownership, and public-content review.
2. Keep the created `quant-research` private repository access-controlled and
   configure its private CI, secrets, and collaborators.
3. Merge the validated `market-intel` boundary change to its approved remote
   branch. Keep the artifact consumer verifier enabled.
4. Update `research-workspace`'s version manifest to the exact public,
   private, and `market-intel` commits. Do not update gitlinks until the
   corresponding remote commits are reachable and independently verified.
5. Run the workspace doctor, contract smoke, workspace tests, hard quality
   profile, and submodule smoke checks against the new commit combination.
6. Update documentation and compatibility aliases. Rename legacy repositories
   one at a time only after their replacement is green.
7. Retain old repositories and release pointers through the rollback window;
   remove legacy submodules only after every consumer and production manifest
   has switched successfully.

## Per-step rollback

| Failure | Rollback |
| --- | --- |
| Public audit finds private content | stop before publishing; discard public staging publication and keep the old public source authoritative |
| Private repository dependency or test failure | keep old strategy repositories and private production pins; do not advance workspace manifest |
| `market-intel` contract failure | keep previous consumer commit and previous artifact release active; do not advance `current` |
| Workspace compatibility failure | restore the previous version manifest/gitlinks and rerun smoke checks |
| Production promotion failure | leave `current` unchanged; atomically restore the previous release directory |
| Rename or redirect failure | keep the old repository name and compatibility pointer; retry only after CI and URL checks pass |

## Completion evidence

The cutover is complete only when the following are recorded in the workspace
release manifest:

- remote repository URLs and visibility;
- exact commits for all four layers;
- CI results for public and private repositories;
- consumer verification receipt and artifact hashes;
- old-name compatibility/redirect status;
- rollback release identifiers and the date the rollback window closes.

Until the workspace and all consumers are switched, the architecture remains
in a transition state and the legacy submodules remain the authoritative
rollback source. The new repositories are published targets, not yet the
production source of truth.
