# 港股通季频 PIT 研究归档

> status: archived
> owner: strategy-research
> last_verified: 2026-08-16
> source_of_truth: no
> superseded_by: 数据与执行边界归 owner 仓，候选结论见 pipeline HK archive

本页是港股通季频 PIT 研究的权威索引入口。原始笔记与 config 仍冻结在
`strategy-pipeline/docs/archive/research/hk/`，本页只负责定位、说明生命周期与结论，
不复制或改写被 provenance 哈希绑定的内容。

## 投资假设与生命周期

季频港股通路线研究季度点（point-in-time）财务与组合构造，属于 `archived` 研究树，
没有进入生产发布，不能自动恢复为生产流程。复现以具体 run 的 `config.used.yml` 与
`summary.json` 为最高优先级，优先级高于研究笔记。

## 归档结论

| 路线 | 结论 |
| --- | --- |
| 季频主线 | `ranker h12_w16 + close + balanced execution` 保持主线 |
| 第一候选 | `reg_zscore h12_w16 + tr_close` |
| 结构探针 | `raw-scale dedup + groupcap3` 只作结构探针 |
| 覆盖敏感场景 | `provider_dense` 只在 coverage-sensitive 场景使用 |

## 已迁能力

- PIT 财务、coverage、health 与 current contract 生产由 `market-data-platform` 承载。
- 组合构造、成本与可交易性评估归 `portfolio-backtester`。
- 执行边界说明由 `targets.json` 导出语义承担，不证明 broker trading readiness。

## 文件归属

| 内容类型 | 位置 |
| --- | --- |
| 历史研究笔记 | pipeline `docs/archive/research/hk/notes/hk-quarterly-*.md` |
| 历史实验 config | pipeline `docs/archive/research/hk/configs/experiments/` |
| 冻结回执 | 以具体 run 目录的 `config.used.yml` 与 `summary.json` 为准 |

## 快速阅读

| 目的 | 先读 |
| --- | --- |
| 季频路线整体口径 | pipeline `notes/hk-quarterly-current-state-20260329.md` |
| 候选与结构探针解释 | pipeline `notes/hk-quarterly-benchmark-and-interpretation-20260405.md`、`notes/hk-quarterly-holdings-analysis-20260329.md` |
| PIT freshness / coverage warning | pipeline `notes/hk-quarterly-pit-provider-coverage-20260411.md` |

## 恢复边界

本归档不可自动恢复为生产流程。HK 资产的生产、PIT 与执行分别由 `market-data-platform` 与
`quant-execution-engine` 承载，季频候选的任何重新评估都从活跃策略说明开始。
