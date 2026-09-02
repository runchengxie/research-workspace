# 架构边界

本工作区把策略知识与运行时代码分开，通过公开 API 和文件产物连接数据、研究、回测、编排和执行：

```text
strategy-research
  维护策略身份、投资假设、生命周期和证据导航
        |
        v
market-data-platform
  发布数据资产
        |
        v
deep-learning-tick-data-prediction
  L2 事件流清洁审计、模型和预测产物
        |
        v
alpha-research
  生成特征、模型评估和信号产物
        |
        v
portfolio-backtester
  构造组合并评估成本、容量和风险
        |
        v
strategy-app
  把策略规格转成纯计算，组合各职责仓公开 API 并返回数据帧和报告
        |
        v
strategy-pipeline
  编排研究流程并导出 targets.json
        |
        v
quant-execution-engine
  解析 targets.json，执行预演、风控和受控交易
```

## Python 命名空间

各子仓库维护自己的主要 Python 命名空间：

- `market_data_platform.*` 归 `market-data-platform`
- `ticknet.*` 归 `deep-learning-tick-data-prediction`
- `alpha_research.*` 归 `alpha-research`
- `portfolio_backtester.*` 归 `portfolio-backtester`
- `style_factors.*` 表现层归 `strategy-research`
- `strategy_app.*` 归 `strategy-app`
- `strategy_pipeline.*` 归 `strategy-pipeline`
- `quant_execution_engine.*` 归 `quant-execution-engine`

风格因子计算内核位于 `alpha_research.style_factors`，分位回测内核位于 `portfolio_backtester.style_factors_backtest`，研究表现层位于 `strategy-research/style_factors`，可使用 `python -m style_factors` 调用。

工作区 2.0 已删除旧共享命名空间、旧命令行别名和环境变量回退。策略编排的权威命令为 `strategy` 和 `strategy-pipeline`。命名迁移记录见 [ADR-0002](docs/adr/0002-owner-native-python-namespaces.md)。

策略身份和生命周期由 `strategy-research` 维护。可执行应用由 `strategy-app` 维护。`strategy-pipeline` 负责数据提供方调用、操作控制、运行目录、原子发布和执行交接。详细边界见 [ADR-0006](docs/adr/0006-strategy-knowledge-and-runtime-boundaries.md)。

当前八个 submodule 为 `market-data-platform`、`deep-learning-tick-data-prediction`、`alpha-research`、`portfolio-backtester`、`strategy-research`、`strategy-app`、`strategy-pipeline`、`quant-execution-engine`。版本由 `.gitmodules` 和各自 gitlink 锁定。

## 代码和数据边界

- 活跃代码服务当前 A 股数据与研究主线，以及多市场共用的执行契约。
- 兼容入口需要登记负责人、替代路径、删除条件和验证证据。
- 带日期的交接、冻结、恢复演练和历史研究记录进入归档。
- 公开合成数据示例由外部演示仓库维护，不属于本工作区的子模块或发布门禁。
- 数据供应商适配器、券商适配器、凭证、本地数据和交易审计日志留在对应运行环境。

跨仓库协作使用稳定文件或公开 API。第三方框架对象不得进入跨仓库契约。

## 数据质量与 PIT 边界

- `market-data-platform` 负责不可变原始数据、数据语义契约、可复用质量检查、时间点与版本来源追踪、数据质量凭证和权威发布。
- `deep-learning-tick-data-prediction` 负责事件流、模型输入、标签与泄漏检查、交易所特定回放诊断和模型评估。模型仓不能静默覆盖数据平台给出的可用性状态。
- `alpha-research`、`portfolio-backtester` 与 `strategy-research` 在平台数据证据之上增加研究、组合与策略生命周期门禁，不重复定义原始数据清洗规则。
- `research_only` 与 `quarantine` 必须保持显式状态，跨仓交接时不能折叠成普通可用数据。

完整约定见 [跨仓库数据质量契约](docs/data-quality-contracts.md)。

## 外部框架

- Qlib 可以作为研究和差分回测后端。数据资产、时间点语义和跨仓库产物仍由本工作区维护。
- vn.py 可以作为执行传输、Gateway 和订单管理系统（OMS）适配层。审批、幂等、持久证据和对账归 `quant-execution-engine`。
- LEAN 只用于领域对象和参考场景对照，不进入当前 Python 主运行时。

适配器需要把输入和输出转换为本工作区的稳定类型或文件产物。

## 版本解析

工作区模式以顶层 gitlink 组合为版本事实。各子仓 `pyproject.toml` 的 `[tool.uv.sources]` 服务于独立安装模式，可以与 gitlink 暂时不同。

`scripts/workspace_architecture.py` 会把这些差异记录到版本图。当前差异属于可见警告。顶层集成测试必须进一步确认实际加载的是当前工作区组合，避免独立安装 pin 静默改变集成测试版本。

## 治理入口

- [Architecture as Code](docs/architecture-as-code.md)
- [工作区聚合路线图](docs/roadmap.md)
- [文档归集与去重清单](docs/documentation-consolidation.md)
- [框架集成边界](docs/adr/0001-framework-integration-boundaries.md)
- [命名空间边界](docs/adr/0002-owner-native-python-namespaces.md)
- [策略知识与运行时边界](docs/adr/0006-strategy-knowledge-and-runtime-boundaries.md)
- [跨仓库文件契约](docs/contracts.md)
- [跨仓库数据质量契约](docs/data-quality-contracts.md)
- [废弃入口](docs/deprecations.md)
- [脚本生命周期](docs/script-lifecycle.yml)
- [质量覆盖](docs/quality-coverage-governance.yml)
- [维护性重构路线图](docs/maintainability-refactor-roadmap.yml)
- [发布检查](docs/release-checklist.md)
