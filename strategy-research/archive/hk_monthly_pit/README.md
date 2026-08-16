# 港股通月频 PIT 研究归档

> status: archived
> owner: strategy-research
> last_verified: 2026-08-16
> source_of_truth: no
> superseded_by: 数据与执行边界归 owner 仓，候选结论见 pipeline HK archive

本页是港股通月频 PIT 研究的权威索引入口。原始笔记与 config 仍冻结在
`strategy-pipeline/docs/archive/research/hk/`，本页只负责定位、说明生命周期与结论，
不复制或改写被 provenance 哈希绑定的内容。

## 投资假设与生命周期

月频港股通路线研究时间点（point-in-time）候选池与低换手持仓，属于 `archived` 研究树，
没有进入生产发布，不能自动恢复为生产流程。复现以具体 run 的 `config.used.yml` 与
`summary.json` 为最高优先级，优先级高于研究笔记。

## 归档结论

| 路线 | 结论 |
| --- | --- |
| 月频基准 | `M-PIT baseline` 留作研究锚点，`M-PIT + no_ret + bx20 / be10` 保留为默认 PIT 候选 |
| ranker 主候选 | `trial_008 + k15_bx25_be12` 是 ranker 主候选 |
| 实现对照 | provider rebalance-only 只作实现对照或前瞻候选 |

## 已迁能力

- PIT coverage、health、current contract、asset release 与 intraday asset 生产由
  `market-data-platform` 承载，pipeline 只读消费。
- 执行边界说明由 `targets.json` 导出语义承担，不证明 broker trading readiness。
- 港股通候选与组合评估如需继续，统一从 `catalog.json` 进入对应策略族说明。

## 文件归属

| 内容类型 | 位置 |
| --- | --- |
| 历史研究笔记 | pipeline `docs/archive/research/hk/notes/hk-monthly-*.md` |
| 历史实验 config | pipeline `docs/archive/research/hk/configs/experiments/` |
| 冻结回执 | 以具体 run 目录的 `config.used.yml` 与 `summary.json` 为准 |

## 快速阅读

| 目的 | 先读 |
| --- | --- |
| 月频路线整体口径 | pipeline `notes/hk-monthly-current-state-20260330.md` |
| 候选收敛到 no-ret / ranker | pipeline `notes/hk-monthly-pit-no-ret-tuning-follow-up-20260405.md`、`notes/hk-monthly-ranker-ab-and-next-sweep-20260413.md` |
| 行业与 benchmark 解释 | pipeline `notes/hk-monthly-industry-treatment-20260404.md`、`notes/hk-monthly-benchmark-ladder-and-attribution-20260405.md` |

## 恢复边界

本归档不可自动恢复为生产流程。HK 资产的生产、PIT 与执行分别由 `market-data-platform` 与
`quant-execution-engine` 承载，月频候选的任何重新评估都从活跃策略说明开始。
