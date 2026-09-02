# 文档总入口

本目录记录跨仓库协作、架构边界、数据契约、研究治理、发布流程和工作区维护。子项目的
内部实现、依赖、参数和完整命令以各自仓库文档为准。

## 按使用场景阅读

| 需求 | 入口 |
| --- | --- |
| 第一次初始化工作区 | [bootstrap.md](bootstrap.md) |
| 理解数据到执行的完整流程 | [platform-workflow.md](platform-workflow.md) |
| 查看工作区当前路线图 | [roadmap.md](roadmap.md) |
| 查找仓库职责和命名空间 | [架构说明](../ARCHITECTURE.md) |
| 查看跨仓库文件契约 | [contracts.md](contracts.md) |
| 查看数据质量和 PIT 约定 | [data-quality-contracts.md](data-quality-contracts.md) |
| 理解数据生命周期术语 | [data-lifecycle-terminology.md](data-lifecycle-terminology.md) |
| 查看数据路径迁移 | [data-path-migration-map.md](data-path-migration-map.md) |
| 执行数据过渡或恢复 | [data-transition-playbook.md](data-transition-playbook.md) |
| 查看策略身份和生命周期 | [strategy-research/README.md](../strategy-research/README.md) |
| 查看研究证据门禁 | [strategy-evidence-gate.md](strategy-evidence-gate.md) |
| 查看外部框架支持范围 | [framework-support-matrix.md](framework-support-matrix.md) |
| 查看版本组合 | [version-matrix.md](version-matrix.md) |
| 执行发布前检查 | [release-checklist.md](release-checklist.md) |
| 维护工作区和本地门禁 | [workspace-maintenance.md](workspace-maintenance.md) |
| 阅读文档写作约定 | [documentation-style.md](documentation-style.md) |
| 查找历史记录和证据 | [archive/README.md](archive/README.md) |

## 子项目文档

| 子项目 | 入口 | 主要内容 |
| --- | --- | --- |
| `market-data-platform` | [docs](../market-data-platform/docs/) | 行情数据供给、契约和治理 |
| `deep-learning-tick-data-prediction` | [README](../deep-learning-tick-data-prediction/README.md) | L2 事件流审计、模型和预测产物 |
| `alpha-research` | [docs](../alpha-research/docs/) | 特征、模型和研究评估 |
| `portfolio-backtester` | [docs](../portfolio-backtester/docs/) | 组合回测、成本、容量和风险 |
| `strategy-app` | [docs](../strategy-app/docs/) | 策略应用、研究计算和迁移边界 |
| `strategy-pipeline` | [docs](../strategy-pipeline/docs/) | 策略编排、配置和运行产物 |
| `strategy-research` | [README](../strategy-research/README.md) | 策略目录、实验、证据和生命周期 |
| `quant-execution-engine` | [docs](../quant-execution-engine/docs/) | 预演、风控、执行和审计 |

## 文档分工

- 根 README 负责工作区定位、快速开始和最短入口。
- `ARCHITECTURE.md` 负责完整职责边界。
- `AGENTS.md` 负责协作规则、文件边界和验证要求。
- 本页负责导航，不维护动态资产数量、版本号或运行结果。
- 当前事实优先来自代码、测试、manifest、catalog、contract 和运行 receipt。
- `docs/archive/`、`docs/evidence/`、ADR、计划和研究结果保存历史背景，不作为当前状态入口。

## 主题索引

### 架构与职责

- [architecture-as-code.md](architecture-as-code.md)
- [architecture-split-closure-checklist.md](architecture-split-closure-checklist.md)
- [adr/README.md](adr/README.md)
- [submodule-boundary-refactor-checklist.md](submodule-boundary-refactor-checklist.md)
- [strategy-boundary-refactor-roadmap.md](strategy-boundary-refactor-roadmap.md)

### 数据、契约与迁移

- [artifact-contracts.yml](artifact-contracts.yml)
- [contracts.md](contracts.md)
- [data-quality-contracts.md](data-quality-contracts.md)
- [data-path-breaking-change-register.md](data-path-breaking-change-register.md)
- [data-path-migration-map.md](data-path-migration-map.md)
- [data-transition-playbook.md](data-transition-playbook.md)

### 研究与证据

- [research-spec.md](research-spec.md)
- [research-decision-governance.md](research-decision-governance.md)
- [strategy-evidence-gate.md](strategy-evidence-gate.md)
- [benchmark-matrix.md](benchmark-matrix.md)
- [style-factors.md](style-factors.md)
- [style-factor-technical-reference.md](style-factor-technical-reference.md)

### 维护、质量与发布

- [workspace-maintenance.md](workspace-maintenance.md)
- [quality-governance.md](quality-governance.md)
- [maintainability-governance.md](maintainability-governance.md)
- [documentation-audit-20260902.md](documentation-audit-20260902.md)
- [framework-support-matrix.md](framework-support-matrix.md)
- [version-matrix.md](version-matrix.md)
- [release-checklist.md](release-checklist.md)
- [production-update.md](production-update.md)

### 历史与规划

- [documentation-consolidation.md](documentation-consolidation.md)
- [documentation-lifecycle.md](documentation-lifecycle.md)
- [deprecations.md](deprecations.md)
- [archive/README.md](archive/README.md)
- [superpowers/plans/](superpowers/plans/)
- [superpowers/specs/](superpowers/specs/)
