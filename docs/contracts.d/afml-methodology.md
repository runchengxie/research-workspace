# AFML 方法产物契约

本页是 `docs/contracts.md` 的 owner-native 扩展，由 artifact contract validator 一并读取。

| Artifact | Contract | Owner | Canonical file | 用途 |
| --- | --- | --- | --- | --- |
| `label_events.parquet` | `alpha_research.label_events` | `alpha-research` | `label_events.parquet` | 统一标签、purging、embargo 和 overlap 事件窗口 |
| `sample_weights.parquet` | `alpha_research.sample_weights` | `alpha-research` | `sample_weights.parquet` | uniqueness、time decay 和 return-attribution 训练权重 |
| `sample_weights.receipt.json` | `alpha_research.sample_weights receipt` | `alpha-research` | `sample_weights.receipt.json` | 样本权重配置、有效样本量和事件 hash |
| `research_features.parquet` | `market_data_platform.research_features.v1` | `market-data-platform` | `research_features.parquet` | 已发布的低频流动性和 activity-bar 派生特征 |
| `sizing_receipt.json` | `portfolio_backtester.sizing_receipt.v1` | `portfolio-backtester` | `sizing_receipt.json` | OOS 校准、波动率缩放、权重上限和离散化证据 |
| `strategy_risk_report.json` | `portfolio_backtester.strategy_risk.v1` | `portfolio-backtester` | `strategy_risk_report.json` | PSR、收益集中度、策略失败概率和成本韧性 |
| `hrp_receipt.json` | `portfolio_backtester.hrp_receipt.v1` | `portfolio-backtester` | `hrp_receipt.json` | 模型或 sleeve HRP 配置、顺序和权重摘要 |
| `research_protocol_report.json` | `strategy_pipeline.research_protocol.v1` | `strategy-pipeline` | `research_protocol_report.json` | exploratory/candidate/release 证据完整性门禁 |
| `execution_policy_receipt.json` | `quant_execution_engine.execution_policy_decision.v1` | `quant-execution-engine` | `execution_policy_receipt.json` | 动态目标、平均限价、手数和参与率决策 |
| `handoff_audit_report.json` | `quant_execution_engine.handoff_audit.v1` | `quant-execution-engine` | `handoff_audit_report.json` | targets、lineage 和可选证据 hash 审计 |

## 边界

- `label_events.parquet` 是标签和事件跨度的唯一跨模块事实来源。
- `sample_weights.parquet` 只能由训练窗口内可用的 label outcome 信息计算，并只用于训练。
- `research_features.parquet` 中的盘口或订单流特征必须有真实、授权的逐笔源数据。
- `sizing_receipt.json` 和 `strategy_risk_report.json` 属于研究证据，不是执行指令。
- `research_protocol_report.json` 只决定候选是否允许交接，不改变 `targets.json`。
- `execution_policy_receipt.json` 关联目标 artifact hash，但不反向修改研究模型。
- `handoff_audit_report.json` 验证完整性，不解释 Sharpe、IC、DSR 或 PBO。
