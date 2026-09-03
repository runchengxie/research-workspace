# 顶层文档入口

> status: active
> owner: workspace
> last_verified: 2026-09-02
> source_of_truth: yes
> superseded_by: n/a

本目录只记录跨仓库协作、文件约定、版本组合和发布治理。子仓库的内部实现、依赖、业务参数和完整命令以各自文档为准。

## 推荐阅读

| 目标 | 文档 |
| --- | --- |
| 第一次拉起工作区 | [bootstrap.md](bootstrap.md) |
| 理解端到端链路 | [platform-workflow.md](platform-workflow.md) |
| 查看全部已完成事项、剩余项目和优先级 | [roadmap.md](roadmap.md) |
| 查找策略思路、状态和代码归属 | [../strategy-research/README.md](../strategy-research/README.md) |
| 查看截面股票 ML 的长期研究问题与实验地图 | [cross-sectional ML research agenda](../strategy-research/research/cross_sectional_ml_research_agenda.md) |
| 整理研究资产、抽取通用能力和执行研究资产清理 | [research-lifecycle-and-workspace-hygiene.md](research-lifecycle-and-workspace-hygiene.md) |
| 查看策略边界 R0 至 R6 的实施记录 | [strategy-boundary-refactor-roadmap.md](strategy-boundary-refactor-roadmap.md) |
| 查看子模块边界重构项 | [submodule-boundary-refactor-checklist.md](submodule-boundary-refactor-checklist.md) |
| 查看说明文档归集和去重顺序 | [documentation-consolidation.md](documentation-consolidation.md) |
| 查看仓库职责和命名空间 | [../ARCHITECTURE.md](../ARCHITECTURE.md) |
| 查看贡献流程 | [../CONTRIBUTING.md](../CONTRIBUTING.md) |
| 查看跨仓库文件约定 | [contracts.md](contracts.md) |
| 查看 deep-learning 集成边界 | [deep-learning-integration.md](deep-learning-integration.md) |
| 维护子模块和运行检查 | [workspace-maintenance.md](workspace-maintenance.md) |
| 查看质量检查分类和 CI 策略 | [quality-governance.md](quality-governance.md) |
| 核对 Qlib、LEAN、vn.py 和 Backtrader 的当前状态 | [framework-support-matrix.md](framework-support-matrix.md) |
| 查看当前锁定组合 | [version-matrix.md](version-matrix.md) |
| 发布或更新组合 | [release-checklist.md](release-checklist.md) |
| 数据、研究与代码目录术语 | [data-lifecycle-terminology.md](data-lifecycle-terminology.md) |
| 旧数据路径迁移映射 | [data-path-migration-map.md](data-path-migration-map.md) |
| 登记数据路径重大变更 | [data-path-breaking-change-register.md](data-path-breaking-change-register.md) |
| 生成数据路径审计清单 | `python scripts/data_path_audit.py --data-root <数据根目录> --output <清单路径>` |
| 推进 A 股主线或恢复港股归档 | [data-transition-playbook.md](data-transition-playbook.md) |
| 查看港股恢复专用归档 | [archive/hk/README.md](archive/hk/README.md) |
| 术语表 | [glossary.md](glossary.md) |

## 参考资料

- 工作区路线图：[roadmap.md](roadmap.md)
- 文档归集与去重清单：[documentation-consolidation.md](documentation-consolidation.md)
- 外部框架采用评估：[framework-adoption-assessment.md](framework-adoption-assessment.md)
- 框架集成边界：[adr/0001-framework-integration-boundaries.md](adr/0001-framework-integration-boundaries.md)
- Python 命名空间决策：[adr/0002-owner-native-python-namespaces.md](adr/0002-owner-native-python-namespaces.md)
- 研究应用 owner 边界：[adr/0003-research-application-ownership.md](adr/0003-research-application-ownership.md)
- 架构决策总索引：[adr/README.md](adr/README.md)
- 废弃入口：[deprecations.md](deprecations.md)
- 维护性治理：[maintainability-governance.md](maintainability-governance.md)
- 治理文件索引：[governance-index.md](governance-index.md)
- 子模块 noqa 历史清债计划：[noqa-clearing-plan.md](noqa-clearing-plan.md)
- 文档生命周期：[documentation-lifecycle.md](documentation-lifecycle.md)
- 研究生命周期与工作区瘦身：[research-lifecycle-and-workspace-hygiene.md](research-lifecycle-and-workspace-hygiene.md)
- 架构拆分收口记录：[architecture-split-closure-checklist.md](architecture-split-closure-checklist.md)
- 外部策略项目接入：[strategy-satellites.md](strategy-satellites.md)
- 策略总览导航索引：[strategy-catalog.md](strategy-catalog.md)
- 策略边界重构完成记录：[strategy-boundary-refactor-roadmap.md](strategy-boundary-refactor-roadmap.md)
- 策略生命周期权威目录：[../strategy-research/catalog.json](../strategy-research/catalog.json)
- 截面股票机器学习研究议程：[cross-sectional ML research agenda](../strategy-research/research/cross_sectional_ml_research_agenda.md)
- A 股风格因子研究方法与功能：[style-factors.md](style-factors.md)
- A 股年度市场风格解读（2008 年至 2026 年）：[style-factor-market-regimes-2008-2026.md](../strategy-research/research/experiments/style_factors/style-factor-market-regimes-2008-2026.md)
- A 股低换手因子定义与暴露诊断（2008 年至 2026 年）：[low-turnover-factor-diagnostics-2008-2026.md](../strategy-research/research/experiments/style_factors/low-turnover-factor-diagnostics-2008-2026.md)
- 公募基金持仓因子研究总览（截至 2026-08-25）：[fund-portfolio-factors-overview-20260825.md](../strategy-research/research/experiments/style_factors/fund-portfolio-factors-overview-20260825.md)
- A 股风格因子全历史约束稳健性附录（2008 年至 2026 年）：[style-factor-constrained-robustness-2008-2026.md](../strategy-research/research/experiments/style_factors/style-factor-constrained-robustness-2008-2026.md)
- A 股风格因子约束稳健性历史快照（2015 年至 2026 年）：[style-factor-constrained-robustness-2015-2026.md](../strategy-research/research/experiments/style_factors/style-factor-constrained-robustness-2015-2026.md)
- A 股风格因子技术说明：[style-factor-technical-reference.md](style-factor-technical-reference.md)
- Owner-native 命名空间迁移记录：[namespace-migration.md](namespace-migration.md)
- 价值因子长周期风格轮动分析：[value-regime-18y.md](../strategy-research/research/experiments/style_factors/value-regime-18y.md)
- AFML 方法落地与跨仓库版本组合：[afml-methodology-rollout.md](afml-methodology-rollout.md)
- 策略证据门禁与生命周期必检清单：[strategy-evidence-gate.md](strategy-evidence-gate.md)
- 实验说明书格式与校验：[research-spec.md](research-spec.md)
- 研究判断治理与决策线索：[research-decision-governance.md](research-decision-governance.md)
- 统一考试表格式与生成：[benchmark-matrix.md](benchmark-matrix.md)
- 概念级机器学习探索路线图：[concept-level-ml-exploration.md](../strategy-research/research/experiments/style_factors/concept-level-ml-exploration.md)

阶段记录、冻结记录和历史证据从 [archive/README.md](archive/README.md) 进入。活跃文档只保留当前做法和归档链接。

文档写作约定见 [documentation-style.md](documentation-style.md)，本轮文档审计见
[documentation-audit-20260902.md](documentation-audit-20260902.md)。

## 子模块文档入口

八个子模块的内部实现、依赖、业务参数与完整命令各自成体系，以下为入口导航（路径相对本文件）：

| 子模块 | 文档入口 | 说明 |
| --- | --- | --- |
| `alpha-research` | [../alpha-research/docs/](../alpha-research/docs/) | 研究信号、回测算法与评估方法 |
| `market-data-platform` | [../market-data-platform/docs/](../market-data-platform/docs/) | 行情数据供给、契约与治理 |
| `deep-learning-tick-data-prediction` | [../deep-learning-tick-data-prediction/](../deep-learning-tick-data-prediction/) | L2 事件流审计、模型与预测产物 |
| `portfolio-backtester` | [../portfolio-backtester/docs/](../portfolio-backtester/docs/) | 组合回测、容量与执行模拟 |
| `quant-execution-engine` | [../quant-execution-engine/docs/](../quant-execution-engine/docs/) | 实盘执行引擎与指令路由 |
| `strategy-app` | [../strategy-app/docs/](../strategy-app/docs/) | 应用目录、迁移栈与质量门禁 |
| `strategy-pipeline` | [../strategy-pipeline/docs/](../strategy-pipeline/docs/) | 策略流水线、产出与发布 |
| `strategy-pipeline-internal` | [GitHub 私有仓库](https://github.com/runchengxie/strategy-pipeline-internal) | 私有研究编排、`strategy` CLI、运行目录和目标导出 |
| `strategy-research` | [../strategy-research/README.md](../strategy-research/README.md) | 策略目录、实验、证据与生命周期 |

如某子模块暂无 `docs/README` 索引，可直接浏览其 `docs/` 目录。

## 当前事实

- `market-intel` 是外部卫星仓，通过版本化文件接入，不参与 `print_version_matrix.py` 的版本锁定
- `src/research_contracts` 是顶层普通目录
- `alpha_research.style_factors`（alpha-research）负责风格因子计算内核，`portfolio_backtester.style_factors_backtest`（portfolio-backtester）负责分位回测内核，`strategy-research/style_factors`（可 `python -m style_factors`）负责表现层归因、报告与图表（ADR-0006 拆分后均非顶层目录）
- A 股日频、时间点（PIT）财务和历史行业资产已发布。`normalized_fundamentals` 与 `pit_fundamentals` 均为 v2 且 `exists: true`。准确覆盖范围以 `$DATA_PLATFORM_ROOT/metadata/current_assets/a_share_current.json` 为准
- A 股长窗口 producer 已完成一次 diagnostic run，但运行产物仍是本地 ignored outputs，尚未形成 canonical promotion evidence。E2 是生产准备审计，当前主线仍是推进真实策略研究，见 [roadmap E2](roadmap.md)
- 港股资产和历史研究输出按恢复专用归档管理

> 子模块组成、GitHub Actions 策略与分支规则见根目录 [README.md](../README.md) 和 [AGENTS.md](../AGENTS.md)。本段只记录跨仓库事实中根入口未涵盖的部分，避免重复维护。
