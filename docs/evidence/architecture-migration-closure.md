# 架构迁移收尾检查清单

> 状态：所有暂存迁移切片已验证，等待消费者切换
> 核验日期：2026-09-06

## 目标架构

目标架构如下：

> `quant-platform` 提供可复用能力，`quant-research` 保存策略知识产权，
> `market-intel` 展示并投递结果，`research-workspace` 锁定兼容的版本组合。

在每个迁移切片完成独立发布并取得回滚证据前，当前仓库名称仍作为事实来源。
目标映射记录在 `docs/governance/repository-naming-map.md` 和
`docs/architecture-model.yml` 中。

批准的迁移顺序和回滚触发条件记录在
`docs/migrations/architecture-cutover-runbook.md` 中。

## 已验证门禁

- Public platform at `2ba7088`: Apache-2.0, portfolio/data/alpha/microstructure/orchestration/execution framework slices transferred; local full gate is `1146 passed, 3 skipped`, Ruff and format clean. Public GitHub Actions is green in run `34024056490`.
- Private research at `5265b68`: alpha, microstructure, strategy families, and private execution runtime are transferred; legacy `alpha-research`/`strategy-pipeline` dependencies have been removed in favor of the consolidated framework. All six private transfer jobs are green in CI run `34024857688`.
- Public alpha scope intentionally excludes DailyWatch20/Hotsector strategy-specific modules and ownership/result documents; those remain in private research. Public alpha contains 135 source files, 70 tests, and 31 docs.
- Public orchestration/execution foundations and private broker/runtime code are transferred and covered by their scoped suites.
- Public microstructure framework at `2ba7088` contains only generic event-stream/model/simulator machinery; its synthetic suite passes `45 tests`. Real-data coverage, labels, experiments, and results remain private.
- Private strategy-family source, tests, docs, research records, and runtime imports are transferred; import smoke, DailyWatch20 validation, and the strategy-family CI job are green in `34024857688`. Legacy standalone repository-root governance tests remain excluded where their assertions intentionally require the retired repository layout.
- Formal-shaped DailyWatch20 producer → publication contract → `market-intel`
  consumer handoff: passed for both approved artifacts.
- `market-intel` boundary and production-shaped handoff tests pass; synthetic
  DailyWatch20 fixture is pushed at `89a35d9`; CI run `34025080421` is green
  on Python 3.11–3.13.
- Workspace thin-layer doctor tests: `23 passed`; doctor reports `0 errors`.
- Architecture model tests: `7 passed`; architecture scan reports `0 errors`.
- Contract smoke: all checks passed with `0 errors`, `0 warnings`.
- Hard quality profile: all checks passed, including Ruff, format, ty, import
  boundaries, ownership boundaries, architecture, capability registry, trial
  ledger, and secret scan.
- `quant-platform` and `quant-research` GitHub repositories were created and
  pushed. Both public platform CI and private research CI completed
  successfully for the validated slice.

## AI 上下文策略

Agents default to the directly affected package and its local manifest. They
expand to producer, contract, and consumer only for public API changes,
artifact changes, downstream failures, or explicit cross-module work. The
machine-readable routing is provided by `scripts/context_manifest.py`.

## 回滚演练

在隔离的临时 release 根目录中完成了以下演练：

1. 校验失败时，`current` 仍指向旧版本。
2. 通过临时符号链接和原子替换晋级通过校验的候选版本。
3. 使用相同的原子机制恢复旧版本。

演练前后读取了真实生产指针，结果保持不变：

- `production/market-intel/current` → release `482cb31b...`
- `production/research-workspace/current` → release `9267bbae...`

演练没有修改生产指针、artifact、远端或 GitHub 仓库。

## 明确待办

- 工作区消费者切换到新远端。
- 仓库重命名、重定向和旧 submodule 移除决策。
- 最终迁移仓库的完整 release-type 门禁。

这些工作需要明确的发布或重命名决策，现有本地暂存证据不代表它们已经完成。
