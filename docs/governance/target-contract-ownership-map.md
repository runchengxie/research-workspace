# 目标契约维护方映射

> 状态：迁移目标
> 核验日期：2026-09-06
> 权威来源：目标状态治理图

这张映射表将策略 IP、产物生产方和产物消费方分开。对应迁移门禁通过前，当前仓库名称仍然是权威记录。

| Contract or responsibility | Current owner | Target owner | Consumer | Boundary rule |
| --- | --- | --- | --- | --- |
| Strategy identity, thesis, lifecycle and evidence navigation | `strategy-research` | `quant-research/registry` | research users and governance | Private; never inferred from runtime code location |
| DailyWatch20 strategy-specific calculation | `strategy-app` | `quant-research/strategies/daily_watch20` | orchestration layer | Private; keeps the transitional `strategy_app.daily_watch20` namespace initially |
| `watchlist_20.csv` and `selection_receipt.json` | `strategy-pipeline` + `strategy-app` | `quant-research/strategies/daily_watch20` produces the private projection; `quant-platform/publication` supplies generic bundle mechanics | `market-intel` | Strategy-specific selection and receipt remain private; only the versioned file bundle crosses the application boundary |
| Generic publication manifest and file hashing | `research_contracts` in the workspace | `quant-platform/research_contracts` | `quant-research`, `market-intel`, other approved consumers | Public mechanism only; no strategy selection, provider, credential, or real data |
| DailyWatch20 rendering and delivery | `market-intel` | `market-intel` | end users | Independent application; no import from `quant-research` |
| Version combination and compatibility smoke tests | `research-workspace` | `research-workspace` thin layer | release process | Records compatible commits and rollback pointers; does not own strategy logic |

## 影响

`quant-research` 维护私有策略逻辑和策略专属投影。公共平台提供通用清单构建、相对路径校验、哈希和原子打包机制，不决定选择哪些股票。`market-intel` 只消费带版本的文件包。这样可以保留现有生产方与消费方契约，也不会通过公共编排包暴露策略边界。

## 验证证据

The independent `market-intel` worktree branch `feat/architecture-boundary` contains commit
`312efa2`, which adds `tests/test_research_artifact_boundary.py`. The test passes and enforces that
the consumer has no `quant_research` import and documents versioned-artifact consumption.
