# 研究证据链契约

本页记录跨仓库研究证据链的薄契约。它只描述时点与 lineage，不接管各 owner 的业务计算。

## `research.clock.v1`

Owner：`research-workspace` 的 `research-contracts`。

用途：记录同一次研究运行的信息可见、信号、决策、最早下单、执行窗口和估值时点。交易日历解析、
价格选择、订单生成和成交算法继续由对应 owner 负责。

最小字段：

- `schema_version`
- `timezone`
- `information_cutoff_at`
- `signal_at`
- `decision_at`
- `valuation_at`
- `timing_policy_id`
- `trading_calendar_ref`

`execution_aware` 运行还必须包含：

- `earliest_order_at`
- `execution_window_start_at`
- `execution_window_end_at`

全部时间戳使用带时区的 ISO 8601。共享校验器只检查结构和因果顺序，不解析交易所日历。

## `research.backtest-run.v1`

Contract owner：`research-workspace` 的 `research-contracts`。
主要 producer：计划由 `strategy-pipeline` 在真实集成 PR 中落地。

该清单是一次研究的根 lineage，只引用 owner 产物，不复制数据表或组合账本。核心字段包括：

- `run_id`
- `strategy_ref`
- `research_purpose`
- `evidence_tier`
- `clock`
- `configuration_sha256`
- `producer_versions`
- `data_refs`
- `signal_refs`
- `portfolio_result_ref`
- 可选 `benchmark_ref`
- `evidence_refs`
- `created_at`

第一版 `evidence_tier` 只允许 `diagnostic` 与 `execution_aware`。声明为 `execution_aware` 时，嵌套的
`research.clock.v1` 必须具有完整执行窗口。

`ArtifactRef` 只包含 `artifact_id`、SHA-256 和可选相对路径。`ProducerVersion` 记录 repository、
commit 和可选 version。消费者应通过这些引用定位对应 owner 的稳定 artifact，不要从 run manifest
重新推导业务结果。

本契约种子 PR 不把 `research.backtest-run.v1` 加入 `artifact-contracts.yml`。当前 registry 校验要求
artifact 同时存在真实 owner entrypoint。等 `strategy-pipeline` producer 与 `portfolio-backtester`
canonical bundle 都合入后，由工作区集成 PR 一次性登记 producer、consumer 和 canonical file，避免
把计划能力误写成当前能力。
