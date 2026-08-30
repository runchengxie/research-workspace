# 跨仓库数据质量契约

本工作区把市场数据的可用性判断拆成三个层次，避免每个研究仓库各自解释同一批原始文件。

## 平台层

`market-data-platform` 负责：

- 原始数据不可变保存、provider/schema/version provenance；
- `market_data_platform.dataset_contract.v1` 数据语义契约，包括时间、单位、null/sentinel、事件排序、PIT 和数据集级质量策略；
- `market_data_platform.dq_receipt.v1` 质量回执，包括输入、检查项、lineage、运行时间、状态和 `production` / `research_only` / `quarantine` 准入结论；
- L2 结构扫描、exchange sequence 质量统计、opening-ledger 可复用核算和低拷贝 keep/tag/exclude pilot；
- 分钟与基本面的既有 manifest、validation、immutable version、PIT 和发布门禁。

质量 gate 只读 raw 数据，不负责偷偷修值、删除分区或移动 current/latest alias。数据集特殊语义通过 contract 的 `quality_rules` 显式声明，默认 severity 和 effective severity 都必须保留在 receipt 中。

## 模型层

`deep-learning-tick-data-prediction` 消费平台质量证据，同时继续负责模型相关的数据约束：

- eventstream/model input contract；
- label、leakage、训练兼容性和模型评估；
- exchange-specific snapshot/event lag 与实验性对账；
- L2 replay 中的排序降级证据。

当原始订单保留 exchange channel/sequence 时，simulator 只在同毫秒、单 channel、sequence 完整的事件桶内用 sequence 重排。多 channel 同毫秒保留 source order，并记录 `cross_channel_total_order=false`。缺 sequence 时记录 timestamp fallback，不能把供应商文件宣称成交易所全局总序。

## 研究层

`alpha-research`、`portfolio-backtester` 和 `strategy-research` 不重新发明 raw-data 质量规则。研究侧应把平台 receipt 的 eligibility 与版本/provenance 作为输入证据，再叠加自己的：

- PIT/样本切分与 leakage 检查；
- 特征、模型与 alpha evidence；
- 成本、容量、风险与组合门禁；
- 策略生命周期与 promotion 证据。

`research_only` 数据允许用于明确标记的诊断和数据契约研究，不应静默进入 production candidate、final OOS 或执行目标生成。`quarantine` 数据默认不进入研究主线。

## 新增数据处理

推荐流程：

```text
Provider / raw partition
        ↓
immutable raw + provenance
        ↓
platform profile / validation
        ↓
DQ receipt + eligibility
        ↓
canonical / validated asset
        ↓
model-specific checks
        ↓
alpha / portfolio research
```

分钟 operational 数据继续按交易日增量补齐和原子 promotion。核心 fundamentals observed-vintage 由平台按日归档完整 immutable snapshot，形成日频 revision observation ladder；该频率仍不能证明两次归档之间发生并消失的日内修订，首个观测日前历史仍属于 reconstructed PIT。

## Superproject pinning

涉及跨仓数据契约的变更应先在 owner 仓库形成独立 PR，再由 `research-workspace` PR 更新对应 gitlink。Superproject 只锁定经过审查的子仓 commit，不复制 owner 实现。
