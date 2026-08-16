# A 股早期探索归档

> status: archived
> owner: strategy-research
> last_verified: 2026-08-16
> source_of_truth: no
> superseded_by: 各策略族 catalog 条目与 pipeline archive 中的冻结 config/probe

本页是 A 股早期策略探索的权威索引入口。原始文件仍冻结在
`strategy-pipeline/docs/archive/research/a_share/`，本页只负责定位、说明生命周期与结论，
不复制或改写被 provenance 哈希绑定的内容。

## 投资假设与生命周期

早期探索覆盖 2026 年上半年的 A 股策略开发过程，包含候选池口径、风险网格、行业映射、
事件叠加与容量探针。这些内容处于 `exploration` 生命周期，没有进入生产发布，不能自动恢复为生产流程。

## 归档结论

| 主题 | 结论 | 证据入口 |
| --- | --- | --- |
| 候选池口径 | 周频 top100 equal-weight 与 top80 sqrt-liquidity 候选在 MVP 选择后被中性 top800 base 继承取代 | pipeline `configs/README.md` |
| 风险网格 | live10 formal risk-grid configs 是研究 provenance，不是稳定实验入口 | pipeline `configs/` |
| 容量与执行 | 容量增强与执行容量探针只作诊断，不构成交易 readiness 结论 | pipeline `probes/README.md` |
| 行业映射 | SW2021 与 CNINFO 行业抓取是一次性数据探针，行业映射已由 `market-data-platform` 承担 | pipeline `probes/` |

## 已迁能力

- 可执行 OOS Top-K 逻辑已迁 `portfolio-backtester`（`a_share_executable_oos_topk`）。
- 因子 IC、模型和特征研究归 `alpha-research` 权威。
- 行业、股票池和 PIT 资产生产归 `market-data-platform`。

## 文件归属

| 内容类型 | 位置 |
| --- | --- |
| 历史 pipeline YAML 与精确运行配置 | 保留 pipeline `configs/`，本页索引 |
| 一次性探索脚本 | pipeline `probes/`（`.py.txt` 冻结快照），或 `strategy-research/experiments/archive/` |
| 策略假设与失败原因 | 后续按策略族迁入对应 catalog 条目 |

## 恢复边界

本归档不可自动恢复为生产流程。需要重新评估 A 股候选时，先从
[catalog.json](../../catalog.json) 进入对应策略族的活跃说明与证据。
