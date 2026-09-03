# 策略总览导航

> status: reference
> owner: workspace
> last_verified: 2026-08-09
> source_of_truth: no
> superseded_by: ../strategy-research/README.md

策略身份、投资假设、生命周期和证据导航的权威入口是 [strategy-research/README.md](../strategy-research/README.md)，机器可读目录是 [strategy-research/catalog.json](../strategy-research/catalog.json)。本页只解释术语和跨仓库导航。

## 三个容易混淆的对象

- 策略是可复核的投资假设、候选范围、信号、组合、调仓和风险规则，归 `strategy-research`。
- 策略应用是策略特有的可执行纯计算和冻结合同，归 `strategy-app`。
- 策略流水线是运行、外部调用、发布和执行交接控制面，归 `strategy-pipeline`。

`StrategySpec` 只是信号到组合的技术合同。`strategy run --config ...` 只是可配置工作流。二者都不单独算作策略。

## 当前排查结论

工作区内的策略身份已经集中登记，R0 至 R6 的可执行代码归位已经完成。当前仍需补齐的是策略证据和接口维护：

- DailyWatch20 与热点板块的策略特有纯计算以 `strategy-app` 为目标 owner。
- StyleReplica、D11-H5、红利与成长 ETF 动量、次日开盘到最高价也属于策略目录范围，不应因代码在顶层或 pipeline 而漏记。
- Guan 周度多因子主要在外部仓库，仍通过本目录登记身份和接入边界。
- F-lite、slow-volume、旧仓再资格、Numeric v2、低换手与 DeepSeek 是策略族内变体，不重复登记为独立生产策略。
- Qlib pilot、风格因子研究和基本面 shadow 是方法、输入或实验，不把存在脚本误判成独立策略。

## 代码与证据导航

| 目的 | 入口 |
| --- | --- |
| 查看有哪些策略、生命周期和迁移债务 | [strategy-research/catalog.json](../strategy-research/catalog.json) |
| 阅读策略思路与边界 | [strategy-research/README.md](../strategy-research/README.md) |
| 查看策略应用入口、比较组与冻结规格 | [strategy-app/docs/application-catalog.md](../strategy-app/docs/application-catalog.md) |
| 查看策略应用历史研究证据 | [strategy-app/docs/research/README.md](../strategy-app/docs/research/README.md) |
| 查看外部候选、选择与因子卫星 | [strategy-satellites.md](strategy-satellites.md) |
| 查看信号产物合同 | [alpha-research/docs/reference/signal-artifacts.md](../alpha-research/docs/reference/signal-artifacts.md) |
| 查看组合与回测职责 | [portfolio-backtester/README.md](../portfolio-backtester/README.md) |
| 查看运行与发布控制面 | [strategy-pipeline-internal/docs/strategy-catalog.md](https://github.com/runchengxie/strategy-pipeline-internal/blob/main/docs/strategy-catalog.md) |
| 查看工作区剩余项目和优先级 | [roadmap.md](roadmap.md) |
| 查看策略边界拆分完成记录 | [strategy-boundary-refactor-roadmap.md](strategy-boundary-refactor-roadmap.md) |

## 维护规则

- 新策略或生命周期变化先更新 `strategy-research`，再改运行代码。
- 新变体更新所属策略族说明和 `strategy-app` 应用目录。
- 新外部接入更新 [strategy-satellites.md](strategy-satellites.md)。
- 历史 ADR、回执 schema 和版本快照保留当时名称，不为追求文本一致性改写。
