## Why

工作区的活跃主线已经转向 A 股，但中国香港市场的恢复敏感实现、兼容入口和历史研究材料仍分布在活跃仓库中，继续扩大默认维护面。与此同时，A 股 `daily_clean` 已具备基础 streaming build 和内存 guard，但发布前校验仍缺少行情逻辑、市场规则、manifest 对账和可诊断的批量扫描报告。

## What Changes

- 建立中国香港市场 legacy 私有归档候选的导出、审计和验收流程，记录 source tag、路径清单、checksum、restore drill、replacement docs、rollback notes 和消费者审计结果。
- 将中国香港市场 surface 明确分为 `shared_active`、`frozen_compatibility`、`archived_provenance` 和 `retire_after_audit`；只有满足 deletion gate 且经过单独 follow-up change 的实现才允许从活跃仓库迁出或删除。
- 保留 `marketdata migration freeze-hk` / `hydrate-hk`、freeze marker、标准 `targets.json` 多市场解析、交易执行风控和 LongPort broker runtime；LongPort 不归入中国香港市场 legacy 归档。
- 为 A 股 `daily_clean` 增加结构化质量报告和可配置严重级别，覆盖结构完整性、行情逻辑、涨跌停与停牌一致性、manifest lineage 和交易日历覆盖检查。
- 抽取可复用的 memory-aware Parquet batch scanner，使用列投影和 batch iteration 控制峰值内存，并记录 available memory、RSS、batch rows、估算字节数和 flush / abort 原因。
- 将增强后的 A 股质量报告接入 current refresh 与发布检查：质量门禁未通过时不得更新 canonical `metadata/current_assets/a_share_current.json` 指向的 alias。

## Capabilities

### New Capabilities

- `hk-legacy-private-archive`: 定义中国香港市场 legacy 私有归档候选、消费者审计、restore 证据、迁出门禁和活跃仓库保留边界。
- `memory-aware-parquet-scanning`: 定义可复用的 Parquet batch scanner、动态内存策略和诊断 telemetry。
- `a-share-daily-clean-quality-gate`: 定义 A 股 `daily_clean` 发布前的结构化质量检查、报告格式和阻塞规则。

### Modified Capabilities

无。当前工作区尚未建立 OpenSpec capability baseline。

## Impact

- `research-workspace`：新增归档 gate 脚本、顶层 doctor / checklist 对接、归档证据文档和 focused tests。
- `market-data-platform`：调整 A 股 `daily_clean` validation、CLI、current refresh、共享扫描与内存策略模块、文档和测试；中国香港市场代码只在满足 gate 后由单独 follow-up change 迁出。
- `cross-sectional-trees`：补充中国香港市场 legacy consumer audit 和迁移说明；`cstree alloc-hk` 在审计完成前继续作为 deprecated compatibility command 保留。
- `quant-execution-engine`：不迁出 broker runtime 或标准多市场执行 contract；仅在顶层归档清单中继续明确其 `shared_active` / `private_runtime` 边界。
- 运行依赖：优先复用仓库已有 `pyarrow` 能力；私有归档 repo 的创建、访问控制和 paused-maintenance 设置属于实施阶段的运维动作。
