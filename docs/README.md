# 顶层文档入口

> status: active
> owner: workspace
> audience: human and agent
> last_verified: 2026-09-06
> source_of_truth: yes
> superseded_by: n/a

本目录只记录跨仓库协作、文件约定、版本组合和发布治理。子仓库内部实现、依赖、业务参数和完整命令以各自文档为准。

## 按任务阅读

| 任务 | 入口 |
| --- | --- |
| 第一次拉起工作区 | [操作文档](operations/README.md) |
| 理解模块职责和边界 | [架构文档](architecture/README.md) |
| 核对跨仓文件和产物 | [契约文档](contracts/README.md) |
| 运行检查、发布和维护 | [治理与操作](governance/README.md)、[操作文档](operations/README.md) |
| 了解当前研究交接 | [研究入口](research/README.md) |
| 查找稳定术语和框架状态 | [参考资料](reference/README.md) |
| 查看路线图和当前优先级 | [工作区路线图](roadmap.md) |
| 查看策略身份、实验和生命周期 | [strategy-research README](../strategy-research/README.md) |

## 子模块入口

| 子模块 | 文档入口 | 主要职责 |
| --- | --- | --- |
| `market-data-platform` | [README](../market-data-platform/README.md) | 数据资产生产、检查、发布和读取 |
| `deep-learning-tick-data-prediction` | [README](../deep-learning-tick-data-prediction/README.md) | L2 事件流、模型和预测产物 |
| `alpha-research` | [docs/README](../alpha-research/docs/README.md) | 特征、模型、信号和 alpha 证据 |
| `portfolio-backtester` | [docs/README](../portfolio-backtester/docs/README.md) | 组合回测、成本、容量和风险 |
| `strategy-research` | [README](../strategy-research/README.md) | 策略身份、实验、证据和生命周期 |
| `strategy-app` | [docs/README](../strategy-app/docs/README.md) | 策略专用计算和研究应用 |
| `strategy-pipeline` | [docs/README](../strategy-pipeline/docs/README.md) | 编排、产物发布和交接 |
| `quant-execution-engine` | [docs/README](../quant-execution-engine/docs/README.md) | 执行、风控、对账和审计 |

## 顶层权威页面

- 入口兼容链接：[../ARCHITECTURE.md](../ARCHITECTURE.md)、[../CONTRIBUTING.md](../CONTRIBUTING.md)
- [架构边界](../ARCHITECTURE.md)
- [贡献流程](../CONTRIBUTING.md)
- [跨仓库文件契约](contracts/README.md)
- [质量治理](governance/README.md)
- [版本矩阵](governance/README.md)
- [工作区维护](operations/README.md)
- [术语表](reference/README.md)
- [文档写作与维护](documentation-style.md)
- [文档生命周期](governance/README.md)
- 指标归属：[metric-ownership.md](metric-ownership.md)

阶段记录、冻结记录和历史证据从 [archive/README.md](archive/README.md) 进入。活跃文档不复制历史材料。

港股材料仅通过[恢复专用归档](archive/hk/README.md)访问。

AI 编码工具默认读取根 README、本页、一个相关分类 README 和目标页面。除非任务明确要求，否则跳过 `archive/`、`evidence/` 和 `superpowers/`。
