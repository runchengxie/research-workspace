# Cross-Sectional ML Research Governance Design

> status: active
> owner: workspace、strategy-research
> last_verified: 2026-09-02
> source_of_truth: yes
> superseded_by: n/a

## 目标

本设计解决两个互相关联的问题：

1. 把截面股票机器学习的研究问题从单一短周期收益预测扩展为可证伪的研究议程，系统比较预测周期、预测目标与排序目标。
2. 在研究数量持续增加时，保持策略研究与通用量化基础设施解耦，让失败实验可以归档或删除，可复用能力可以沉淀到职责仓。

本次只增加研究与治理文档，不新增仓库，不修改运行时代码，不改变任何策略生命周期。

## 设计原则

### 研究问题与实现分离

`strategy-research` 维护研究问题、假设、实验矩阵、失败条件、证据和决策。通用实现继续由现有 owner 负责：

- 数据与 PIT 语义：`market-data-platform`
- 特征、标签、模型、排序学习和统计评价：`alpha-research`
- 组合、成本、容量和暴露：`portfolio-backtester`
- 策略特有成熟计算：`strategy-app`
- 编排与发布：`strategy-pipeline`

### 投资期限不等于模型预测期限

长期投资 thesis 可以持续多年，但监督学习目标可以是一年期基本面状态、季度状态或较短收益。研究必须显式区分 holding horizon、prediction horizon、label horizon 与 rebalance frequency。

### 模型的选股偏好本身是研究对象

除了 Sharpe、IC 和收益，还要研究不同目标下模型选出了什么类型的公司，例如 size、turnover、attention、earnings surprise、growth、profitability、margin persistence、cash-flow quality 和 valuation 暴露。

### 实验可以退出，通用能力留下

研究实验应保持薄。两个及以上研究策略需要的能力应优先抽到职责仓。实验被证伪后保留结论、证据和必要复现入口，重复实现与临时脚本不应永久占据活跃代码面。

## 研究议程结构

正式研究议程放在 `strategy-research/research/cross_sectional_ml_research_agenda.md`，至少覆盖：

1. prediction horizon：5d、20d、60d、1y 与 fundamental-state target 的比较。
2. return target 与 fundamental target：直接收益预测和未来盈利能力、利润率、成长、现金流状态预测的比较。
3. stable compounder omission：短周期 return model 是否系统性低估缺乏短期 catalyst 的稳定优质公司。
4. attention / catalyst mechanism：注意力、成交、业绩 surprise、revision 与热点是否主要解释短周期模型选择。
5. learning objective：pointwise、pairwise、listwise 的目标对齐和噪声权衡。
6. model phenotype：不同模型与 horizon 的 top-k 股票在基本面、交易和风格维度上的画像。
7. valuation bridge：未来基本面预测是否需要与当前估值结合后才产生股票收益信息。
8. A 股假设：small-cap、low-turnover、growth 的历史结果要与壳价值、流动性、行业、制度和可交易性竞争解释区分。

## 排序学习术语

标准主分类使用 pointwise、pairwise、listwise，不增加 `rank-wise` 第四类。

- pointwise：每只股票独立预测收益、基本面状态或横截面 rank。
- pairwise：学习同一形成期内股票 A 是否应该排在股票 B 前面。
- listwise：把同一形成期整个股票截面作为排序对象，可重点优化 top-k，例如 NDCG@20 或 NDCG@100。

研究不得先验假定 listwise 优于 pairwise。股票完整排序含有大量低经济价值的相对次序，实验应重点关注最终组合实际使用的 top-k 区域。

## 治理设计

工作区新增 `docs/research-lifecycle-and-workspace-hygiene.md`，定义：

- active research、living infrastructure、historical knowledge 三类资产。
- capability extraction rule：通用能力从实验目录迁移到 owner 仓的触发条件。
- archive/reject/promote 规则。
- research GC：定期盘点停滞实验、重复实现、失效文档、过期配置和已抽取能力留下的壳代码。
- evidence retention：归档研究保留假设、关键配置、数据/代码版本、核心结果、失败原因和证据引用，不要求永久保留大型运行产物。
- repo split trigger：只有领域边界、依赖和维护节奏真正独立时才新增仓库，不以文件数量作为拆仓依据。

## Research GC 原则

Research GC 默认每季度进行一次，也允许在研究族完成重大阶段后触发。GC 是评审流程，不是自动删除脚本。

每次盘点至少检查：

- 长期无活动且没有下一步决策的实验。
- 已被证伪但仍位于 active 导航的实验。
- 两处及以上重复实现的特征、标签、模型 wrapper、CV、ranking 或 portfolio 逻辑。
- 已抽取到 owner 仓后仍保留的实验内实现。
- 已 superseded 的配置、文档和入口。
- 无法追溯数据、PIT 或证据来源的研究资产。

处置结果必须是 retain、extract、archive、supersede 或 delete 之一，并记录理由。

## 不新增仓库

当前 owner 边界已经由 ADR-0006 明确，继续拆仓会增加 gitlink、版本锁和组合验证成本。本次只强化 ownership、extraction 与 archive 规则。

未来只有同时满足以下条件时才考虑新仓库：

1. 有稳定且独立的领域 owner。
2. 有独立发布或依赖节奏。
3. 与现有 owner 的公开契约已经稳定。
4. 拆分能删除依赖或重复，而不只是移动文件。
5. workspace 组合验证成本的增加有明确收益。

## 文档落点

- `strategy-research/research/cross_sectional_ml_research_agenda.md`：研究问题与实验地图。
- `research-workspace/docs/research-lifecycle-and-workspace-hygiene.md`：跨仓库研究生命周期与瘦身规则。
- `research-workspace/docs/README.md`：新增两个入口导航，其中研究议程链接到 `strategy-research`。

不修改 `catalog.json`，因为研究议程不是一条独立策略。

## 验证

本次为文档治理改动，验证重点是：

- 新路径存在且互相链接正确。
- 不与 ADR-0006、文档生命周期和研究判断治理冲突。
- 不把新的研究议程误登记成生产策略。
- 不新增运行时代码或依赖。
