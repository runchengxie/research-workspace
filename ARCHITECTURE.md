# 架构边界

本工作区通过文件产物连接数据、研究、回测、编排和执行：

```text
market-data-platform
  发布数据资产
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
research-apps
  组合 owner API 并返回研究 frames 和报告
        |
        v
strategy-pipeline
  编排研究流程并导出 targets.json
        |
        v
quant-execution-engine
  解析 targets.json，执行预演、风控和受控交易
```

每个子仓库维护自己的 Python 命名空间：

- `alpha_research.*` 归 `alpha-research`
- `portfolio_backtester.*` 归 `portfolio-backtester`
- `research_apps.*` 归 `research-apps`
- `strategy_pipeline.*` 归 `strategy-pipeline`

工作区 2.0 已删除旧共享命名空间、命令行（CLI）别名和环境变量回退。策略编排的权威命令为 `strategy` 和 `strategy-pipeline`。命名迁移记录见 [ADR-0002](docs/adr/0002-owner-native-python-namespaces.md)。
研究应用由独立 `research-apps` 仓库发行，`strategy-pipeline` 继续拥有数据提供方调用、
操作员控制、原子发布和执行交接。边界见
[ADR-0004](docs/adr/0004-standalone-research-apps-repository.md)。

## 代码和数据边界

- 活跃代码服务当前 A 股数据与研究主线，以及多市场共用的执行契约。
- 兼容入口必须登记负责人、替代路径、删除条件和验证证据。
- 带日期的交接、冻结、恢复演练和历史研究记录进入归档。
- 公开合成数据示例由外部演示仓库维护，不属于本工作区的子模块或发布门禁。
- 数据供应商适配器、券商适配器、凭证、本地数据和交易审计日志留在对应私有运行环境。

跨仓库协作使用稳定文件或公开应用程序接口（API）。第三方框架对象不得进入跨仓库契约。

## 外部框架

- Qlib 可作为研究和差分回测后端。数据资产、时间点（PIT）语义和跨仓库产物仍由本工作区维护。
- vn.py 可作为执行传输、Gateway 和 订单管理系统（OMS）适配层。审批、幂等、持久证据和对账归 `quant-execution-engine`。
- LEAN 只用于领域对象和参考场景对照，不进入当前 Python 主运行时。

适配器需要把输入和输出转换为本工作区的稳定类型或文件产物。

## 治理入口

- [框架集成边界](docs/adr/0001-framework-integration-boundaries.md)
- [命名空间边界](docs/adr/0002-owner-native-python-namespaces.md)
- [跨仓库文件契约](docs/contracts.md)
- [废弃入口](docs/deprecations.md)
- [脚本生命周期](docs/script-lifecycle.yml)
- [质量覆盖](docs/quality-coverage-governance.yml)
- [维护性重构路线图](docs/maintainability-refactor-roadmap.yml)
- [发布检查](docs/release-checklist.md)
