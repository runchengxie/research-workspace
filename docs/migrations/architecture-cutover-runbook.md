# 架构切换运行手册

> 状态：目标 gitlink 已在本地切换，远程推送和生产 T0 尚未开始
> 范围：本地暂存仓库 → 已批准的 GitHub 仓库

本文是仓库整合的最终操作交接文档。
本地暂存仓库和兼容性门禁已经完成验证。下面的命令涉及创建、重命名、推送或修改远程仓库，必须先取得明确决定。

## 目标布局

| Target | Visibility | Contents | Source mapping |
| --- | --- | --- | --- |
| `quant-platform` | public | reusable data interfaces, alpha/research primitives, portfolio/backtest, orchestration, public execution interfaces, contracts and CI | `market-data-platform`, `alpha-research`, `portfolio-backtester`, generic `strategy-pipeline`, public parts of `quant-execution-engine`, generic microstructure code |
| `quant-research` | private | strategy registry, strategy-specific logic, proprietary features/labels, experiments, model selection, evidence and private configuration | `strategy-research`, `strategy-app`, private parts of alpha/microstructure/pipeline |
| `market-intel` | private application | market context, report assembly, dashboards, delivery, freshness and recovery | existing independent repository; consumes versioned artifacts only |
| `research-workspace` | integration-only | version manifest, compatibility checks, contract smoke tests, architecture/CI metadata and rollback pointers | existing superproject; legacy submodules remain until cutover gates pass |

## 前置条件

Do not begin the remote cutover until all of these are true:

- public staging tests and Ruff pass; public CI is green;
- private DailyWatch20 parity suite passes locally (`122 passed`);
- formal DailyWatch20 publication is accepted by `market-intel`;
- `market-intel` boundary and consumer gates pass (`2` boundary tests,
  `112` broader consumer tests);
- workspace doctor reports zero errors;
- architecture scanner reports zero errors;
- production `current` pointers and artifact rollback have been rehearsed;
- license, visibility, GitHub Actions, CODEOWNERS, and repository-owner
  decisions have been explicitly approved.

技术前置条件已经满足。目标 `quant-platform` 公共仓库、`quant-research` 私有仓库和 `market-intel` 仓库均已创建、推送并独立验证。workspace 分支现在记录这些仓库的 gitlink，同时保留所有旧 submodule 以便回滚。在本 workspace 版本推送并获批前，生产 T0 不会开始。

## 切换顺序

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

## 分阶段回滚

| Failure | Rollback |
| --- | --- |
| Public audit finds private content | stop before publishing; discard public staging publication and keep the old public source authoritative |
| Private repository dependency or test failure | keep old strategy repositories and private production pins; do not advance workspace manifest |
| `market-intel` contract failure | keep previous consumer commit and previous artifact release active; do not advance `current` |
| Workspace compatibility failure | restore the previous version manifest/gitlinks and rerun smoke checks |
| Production promotion failure | leave `current` unchanged; atomically restore the previous release directory |
| Rename or redirect failure | keep the old repository name and compatibility pointer; retry only after CI and URL checks pass |

## 完成证据

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

## 回滚窗口策略

The migration uses a defined 14-calendar-day rollback window beginning at
the first production cutover (`T0`). This is a safety window, not permission to
retire legacy repositories early.

During the window:

- every old repository, legacy gitlink, previous production release, and
  previous artifact manifest remains reachable and unchanged;
- the active and previous target manifests are recorded with exact commits;
- daily consumer, freshness, publication, and delivery smoke checks are
  recorded;
- any contract mismatch, missing artifact, unexplained output drift, failed
  recovery, or unavailable rollback source immediately reopens the old release;
- no repository is deleted, archived, renamed, or made inaccessible.

The window closes only after 14 calendar days with no rollback trigger, two
successful scheduled production cycles, a successful rollback rehearsal from
the recorded manifest, and explicit confirmation that licensing, CI access,
consumer validation, and production ownership are complete. The close record
must name the previous release, target release, window start/end timestamps,
checks performed, and the person approving closure.
