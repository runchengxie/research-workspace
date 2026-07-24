# AFML 方法产物契约

本页是 `docs/contracts.md` 的 owner-native 扩展，由 artifact 契约 validator 一并读取。

| Artifact | 契约 | Owner | Canonical file | 用途 |
| --- | --- | --- | --- | --- |
| `label_events.parquet` | `alpha_research.label_events` | `alpha-research` | `label_events.parquet` | 统一标签、purging、embargo 和 overlap 事件窗口 |
| `sample_weights.parquet` | `alpha_research.sample_weights` | `alpha-research` | `sample_weights.parquet` | uniqueness、time decay 和 return-attribution 训练权重 |
| `sample_weights.receipt.json` | `alpha_research.sample_weights receipt` | `alpha-research` | `sample_weights.receipt.json` | 样本权重配置、分组、有效样本量和事件 hash |
| `research_features.parquet` | `market_data_platform.research_features.v1` | `market-data-platform` | `research_features.parquet` | 已发布的低频流动性和 activity-bar 派生特征 |
| `sizing_receipt.json` | `portfolio_backtester.sizing_receipt.v1` | `portfolio-backtester` | `sizing_receipt.json` | 最终组合权重方法、约束、来源文件和权重 hash |
| `strategy_risk_report.json` | `portfolio_backtester.strategy_risk.v1` | `portfolio-backtester` | `strategy_risk_report.json` | PSR、收益集中度、策略失败概率和成本韧性 |
| `hrp_receipt.json` | `portfolio_backtester.hrp_receipt.v1` | `portfolio-backtester` | `hrp_receipt.json`、`hrp_weights.csv` | 模型或 sleeve HRP 配置、顺序、输入和权重 hash |
| `afml_evidence_fragment.json` | `strategy_pipeline.afml_evidence_fragment.v1` | `strategy-pipeline` | `afml_evidence_fragment.json` | run 侧机器生成的 evidence 路径和 SHA-256 fragment |
| `research_protocol_report.json` | `strategy_pipeline.research_protocol.v1` | `strategy-pipeline` | `research_protocol_report.json` | exploratory/candidate/release 文件存在性、hash 和证据完整性门禁 |
| `execution_policy_receipt.json` | `quant_execution_engine.execution_policy_decision.v1` | `quant-execution-engine` | `execution_policy_receipt.json` | 动态目标、平均限价、手数和参与率决策 |
| `handoff_audit_report.json` | `quant_execution_engine.handoff_audit.v1` | `quant-execution-engine` | `handoff_audit_report.json` | targets、lineage 和可选证据 hash 审计 |

## 边界

- `label_events.parquet` 是标签和事件跨度的唯一跨模块事实来源。
- `sample_weights.parquet` 只能由训练窗口内可用的 label outcome 信息计算，并只用于训练。不同 symbol 的并发度独立计算。
- `research_features.parquet` 中的盘口或订单流特征必须有真实、授权的逐笔源数据。
- `portfolio-backtester` 拥有 sizing、strategy-risk 和 HRP 的算法语义。`strategy-pipeline` 可以从 run 产物生成其 sidecar。
- `sizing_receipt.json` 和 `strategy_risk_report.json` 属于研究证据，不是执行指令。
- `afml_evidence_fragment.json` 只合并路径、状态和 SHA-256，不替代正式 protocol report。
- `research_protocol_report.json` 只决定候选是否允许交接，不改变 `targets.json`。
- `execution_policy_receipt.json` 关联目标 artifact hash，但不反向修改研究模型。
- `handoff_audit_report.json` 验证完整性，不解释 Sharpe、信息系数（IC）、DSR 或 回测过拟合概率（PBO）。
