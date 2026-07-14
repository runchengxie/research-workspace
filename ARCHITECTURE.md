# 架构边界

本工作区协调数据平台、alpha 研究、组合回测、策略编排和交易执行之间的文件交接：

```text
market-data-platform
  生产并发布数据资产
        |
        v
alpha-research
  因子、模型、稳健性和信号产物
        |
        v
portfolio-backtester
  组合构造、回测、容量和报告
        |
        v
strategy-pipeline
  编排研究流程、保留 CLI 兼容层，并导出 targets.json
        |
        v
quant-execution-engine
  解析 targets.json，执行 dry-run、风控门禁和受控券商执行
```

`alpha-research` 承载 alpha 研究模块（`alpha_research.*`），`portfolio-backtester` 承载
组合回测模块（`portfolio_backtester.*`），`strategy-pipeline` 承载编排模块
（`strategy_pipeline.*`）。三个 distribution 已各自独占 owner-native namespace，不再通过共享
`cstree` namespace 或 `pkgutil.extend_path` 拼装运行时。`strategy-pipeline` 在 1.x 中单独保留
`cstree` Python facade 与 CLI alias 作为限期兼容面；权威命令是 `strategy`，兼容面按
[ADR-0002](docs/adr/0002-owner-native-python-namespaces.md) 计划在 workspace 2.0 删除。

## 代码边界

- 活跃代码：当前 A 股数据、研究、执行流程，以及多市场共享文件约定。
- 兼容代码：保留中的港股 deprecated surface。删除前需要完成 consumer audit、replacement docs、rollback notes、restore evidence 和 focused tests。
- 归档和来源说明：带日期的交接记录、冻结记录、恢复演练证据和历史研究背景。
- 演示仓库 staging：`demo/` 下的 clean-room synthetic public demo 模板，独立于活跃工作区，不作为子模块或发布门禁。
- 私有运行环境：provider adapter、broker adapter、凭证、本地数据根目录和执行审计日志。这些内容不进入公开演示仓库。

## 治理入口

- 框架集成决策：[docs/adr/0001-framework-integration-boundaries.md](docs/adr/0001-framework-integration-boundaries.md)
- 框架采用评估：[docs/framework-adoption-assessment.md](docs/framework-adoption-assessment.md)
- 框架迁移账本：[docs/framework-integration-ledger.yml](docs/framework-integration-ledger.yml)
- 废弃入口：[docs/deprecations.md](docs/deprecations.md)
- 港股公开拆分：[docs/hk-public-split-manifest.yml](docs/hk-public-split-manifest.yml)
- 脚本生命周期：[docs/script-lifecycle.yml](docs/script-lifecycle.yml)
- 质量覆盖和排除项：[docs/quality-coverage-governance.yml](docs/quality-coverage-governance.yml)
- 重构路线图：[docs/maintainability-refactor-roadmap.yml](docs/maintainability-refactor-roadmap.yml)
- 当前文件约定：[docs/contracts.md](docs/contracts.md)
- 拆分收敛清单：[docs/architecture-split-closure-checklist.md](docs/architecture-split-closure-checklist.md)

## 外部框架边界

- Qlib 只作为可选研究和差分回测后端，不拥有数据资产、PIT 语义或跨仓库 artifact。
- vn.py 只作为可选执行 transport、Gateway 和 OMS bridge；执行审批、幂等、持久证据和对账继续由 `quant-execution-engine` 拥有。
- LEAN 只作为领域对象和 golden-reference 参照，不进入当前 Python 主运行时。
- 第三方框架对象不得跨 repository contract。适配器必须把输入和输出转换为本工作区的稳定类型或文件产物。
