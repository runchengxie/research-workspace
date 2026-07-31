# ADR-0003：研究应用归属与仓库布局解耦

- 状态：superseded by ADR-0004
- 日期：2026-07-18
- 决策范围：研究侧四个 owner 包、`research_apps` 与 `strategy-pipeline`

## 背景

研究侧仍未决定最终采用多仓、私有 monorepo 或公开镜像组合。仓库可见性不应继续阻塞领域归属修正。

`strategy-pipeline` 已同时承载数据快照读取、alpha 模型生命周期、组合回放、策略实验、外部模型运行与发布控制。该混合边界使 owner port 只停留在调用外形，代码归属和依赖方向仍不稳定。

本页保存独立仓库建立前的决策背景。`research-apps` 已于 2026-07-19 成为独立子模块，当前做法见 [ADR-0004](0004-standalone-research-apps-repository.md)。

## 决策

1. `market_data_platform.research_views` 拥有时间点（PIT）数据视图、当前资产解析、候选池快照与来源血缘（lineage）。
2. `alpha_research` 拥有特征、标签、模型生命周期、滚动样本外（OOS）信号、统计推断与信号覆盖层。
3. `portfolio_backtester` 拥有组合构造、换手、成本、可交易性和研究会计状态机。
4. `research_apps` 拥有 DailyWatch20、hotsector 等策略专用合同、预注册实验、证据解释与决策组合。
5. `strategy_pipeline` 仅保留命令行（CLI）、配置合成、运行目录、外部调用 runner、操作员控制、原子发布、release gate 与 `targets.json` 交接。
6. 仓库布局延后决定。`research_apps` 先作为独立 Python 包存在于当前私有子仓库（distribution）中，不得反向 import `strategy_pipeline`，以后可原样抽取为公开或私有仓库。
7. 旧 `strategy_pipeline.*` 路径在迁移窗口内只允许保留保留身份的门面（facade）。不得新增领域实现。

## 不变量

- 第三方框架对象不得进入 owner public result 或跨仓产物（artifact）。
- 历史回执（receipt）、campaign spec digest 与产物（artifact）schema 必须保持可读。
- 原子发布、不可覆盖写入、操作员时间窗和执行交接安全门禁不得因研究代码迁移而下沉。
- 组合会计状态机不得通过 portfolio 包反向 import 流水线伪装成迁移。
- owner 版本、lockfile、最新组合测试和 workspace pin 未完成前，所有迁移拉取请求（PR）保持 draft。

## 合并栈

1. `market-data-platform#10`
2. `alpha-research#11`
3. `portfolio-backtester#13`
4. 更新 owner 版本和 lockfile，运行最新组合验证
5. `strategy-pipeline#26`
6. 更新本仓子模块 pin 并运行 full workspace profile

## 后果

短期内会增加门面与跨仓迁移测试。完成后，仓库布局可独立调整，owner 应用程序接口（API）和 `research_apps` import surface 不需要再次改名。未完成的 mixed module 必须登记在机器可读账本中，不以 README 声明代替退出证据。
