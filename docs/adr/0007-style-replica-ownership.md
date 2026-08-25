# ADR-0007：StyleReplica 策略规则与通用计算分层

- 状态：accepted
- 日期：2026-08-25
- 关联：ADR-0006、roadmap B2

## 背景

`alpha_research.style_replica` 当前同时包含因子与信号计算、A80/B20 策略参数，以及目标持仓构造。历史上这样便于单仓研究，但它把三类生命周期不同的职责绑在一起：可复用的研究计算、StyleReplica 专属决策政策、通用组合构造。

顶层边界要求特征、模型与信号归 `alpha-research`，策略专属纯计算归 `strategy-app`，组合构造归 `portfolio-backtester`。继续让一个 alpha 包同时决定主题配额、持仓槽位、缓冲退出、每日替换和最终权重，会让策略参数修改与通用研究 API 修改互相耦合。

## 决策

StyleReplica 按以下职责切分：

1. `alpha-research` 拥有因子、score、signal、研究标签与信号产物。它可以接收策略层传入的参数，但不新增最终持仓权重、缓冲退出、每日替换或组合重叠政策。
2. `strategy-app` 拥有 StyleReplica 的策略身份与冻结政策，包括 A80/B20、主题配额、策略专属行业约束、模型版本和实验合同。策略政策以显式配置传给 owner API。
3. `portfolio-backtester` 拥有从已评分候选到目标持仓的通用组合机制，包括槽位分配、buffer、replacement、overlap、weight、position validation 与回放。
4. `strategy-pipeline` 只负责调用上述公开 API、解析运行参数、写运行目录与发布产物。它不得直接读取数据平台资产内部文件名。
5. `market-data-platform` 通过 published/current contract 和只读 research view 提供 StyleReplica 所需市场数据。调用方不得依赖 `daily_clean.parquet`、`daily_basic.parquet` 等历史物理布局。

## 兼容与迁移

现有 `alpha_research.style_replica` 公共入口暂不机械搬迁。迁移按行为边界分批进行：

1. 先冻结 public API 和当前结果 fixture，防止重切时改变研究结果。
2. 将 A80/B20、主题配额等策略身份参数抽为 `strategy-app` 的版本化 policy，并由调用方显式注入。
3. 将 buffer、replacement、overlap 和最终权重构造迁到 `portfolio-backtester` 的公开 API。
4. alpha 侧保留兼容入口时只能做薄适配，并登记删除条件。新功能直接落到目标 owner，不继续扩大旧混合模块。
5. 每批迁移分别运行 alpha、portfolio、strategy-app 与 pipeline 的相关回归，并在子仓合并后更新 superproject gitlink。

## 判定规则

以下变化可以直接判断 owner：

- 新因子、新 score、新信号诊断进入 `alpha-research`。
- A80/B20 身份、主题配额、策略版本或冻结研究政策进入 `strategy-app`。
- 持仓数量约束、换仓 buffer、每日替换限制、重叠处理、最终权重进入 `portfolio-backtester`。
- CLI、运行目录、发布和 `targets.json` 交接进入 `strategy-pipeline`。
- 数据资产解析、PIT 读取、published asset 路径进入 `market-data-platform`。

如果一个函数同时需要策略身份参数和组合算法，应把策略参数作为输入传给组合 owner，避免在组合仓硬编码具体策略名称。

## 后果

- StyleReplica 不再作为 alpha 仓的特殊全栈策略继续增长。
- 策略参数与组合算法可以独立演化和测试。
- 迁移可以渐进进行，现有研究证据不因大规模机械搬文件而失去可复现性。
- B2 的完成标准增加一项：旧 `alpha_research.style_replica` 中不再新增策略政策或最终持仓构造，现有混合职责按 ratchet 只减不增。
