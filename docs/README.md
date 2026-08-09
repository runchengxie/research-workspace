# 顶层文档入口

> status: active
> owner: workspace
> last_verified: 2026-07-19
> source_of_truth: yes
> superseded_by: n/a

本目录只记录跨仓库协作、文件约定、版本组合和发布治理。子仓库的内部实现、依赖、业务参数和完整命令以各自文档为准。

## 推荐阅读

| 目标 | 文档 |
| --- | --- |
| 第一次拉起工作区 | [bootstrap.md](bootstrap.md) |
| 理解端到端链路 | [platform-workflow.md](platform-workflow.md) |
| 查找策略思路、状态和代码归属 | [../strategy-research/README.md](../strategy-research/README.md) |
| 查看仓库职责和命名空间 | [../ARCHITECTURE.md](../ARCHITECTURE.md) |
| 查看贡献流程 | [../CONTRIBUTING.md](../CONTRIBUTING.md) |
| 查看跨仓库文件约定 | [contracts.md](contracts.md) |
| 维护子模块和运行检查 | [workspace-maintenance.md](workspace-maintenance.md) |
| 查看质量检查分类 | [quality-governance.md](quality-governance.md) |
| 核对 Qlib、LEAN、vn.py 和 Backtrader 的当前状态 | [framework-support-matrix.md](framework-support-matrix.md) |
| 查看当前锁定组合 | [version-matrix.md](version-matrix.md) |
| 发布或更新组合 | [release-checklist.md](release-checklist.md) |
| 推进 A 股主线或恢复港股归档 | [data-transition-playbook.md](data-transition-playbook.md) |
| 查看港股恢复专用归档 | [archive/hk/README.md](archive/hk/README.md) |
| 术语表 | [glossary.md](glossary.md) |

## 参考资料

- 外部框架采用评估：[framework-adoption-assessment.md](framework-adoption-assessment.md)
- 框架集成边界：[adr/0001-framework-integration-boundaries.md](adr/0001-framework-integration-boundaries.md)
- Python 命名空间决策：[adr/0002-owner-native-python-namespaces.md](adr/0002-owner-native-python-namespaces.md)
- 研究应用 owner 边界：[adr/0003-research-application-ownership.md](adr/0003-research-application-ownership.md)
- 架构决策总索引：[adr/README.md](adr/README.md)
- 废弃入口：[deprecations.md](deprecations.md)
- 维护性治理：[maintainability-governance.md](maintainability-governance.md)
- 治理文件索引：[governance-index.md](governance-index.md)
- 代码体量复查与拆分建议：[code-size-review.md](code-size-review.md)
- 子模块巨型文件拆分方案：[submodule-refactor-plan.md](submodule-refactor-plan.md)
- 子模块 noqa 清债计划：[noqa-clearing-plan.md](noqa-clearing-plan.md)
- 文档生命周期：[documentation-lifecycle.md](documentation-lifecycle.md)
- 架构边界发布清单：[architecture-split-closure-checklist.md](architecture-split-closure-checklist.md)
- 外部策略项目接入：[strategy-satellites.md](strategy-satellites.md)
- 策略总览导航索引：[strategy-catalog.md](strategy-catalog.md)
- 策略生命周期权威目录：[../strategy-research/catalog.json](../strategy-research/catalog.json)
- A 股风格因子研究方法与功能：[style-factors.md](style-factors.md)
- A 股年度市场风格解读（2008 年至 2026 年）：[style-factor-market-regimes-2008-2026.md](../strategy-research/experiments/style_factors/style-factor-market-regimes-2008-2026.md)
- A 股低换手因子定义与暴露诊断（2008 年至 2026 年）：[low-turnover-factor-diagnostics-2008-2026.md](../strategy-research/experiments/style_factors/low-turnover-factor-diagnostics-2008-2026.md)
- A 股风格因子全历史约束稳健性附录（2008 年至 2026 年）：[style-factor-constrained-robustness-2008-2026.md](../strategy-research/experiments/style_factors/style-factor-constrained-robustness-2008-2026.md)
- A 股风格因子约束稳健性历史快照（2015 年至 2026 年）：[style-factor-constrained-robustness-2015-2026.md](../strategy-research/experiments/style_factors/style-factor-constrained-robustness-2015-2026.md)
- A 股风格因子技术说明：[style-factor-technical-reference.md](style-factor-technical-reference.md)
- Owner-native 命名空间迁移记录：[namespace-migration.md](namespace-migration.md)
- 价值因子长周期风格轮动分析：[value-regime-18y.md](../strategy-research/experiments/style_factors/value-regime-18y.md)
- AFML 方法落地与跨仓库版本组合：[afml-methodology-rollout.md](afml-methodology-rollout.md)
- 概念级机器学习探索路线图：[concept-level-ml-exploration.md](../strategy-research/experiments/style_factors/concept-level-ml-exploration.md)

阶段记录、冻结记录和历史证据从 [archive/README.md](archive/README.md) 进入。活跃文档只保留当前做法和归档链接。

## 子模块文档入口

六个子模块的内部实现、依赖、业务参数与完整命令各自成体系，以下为入口导航（路径相对本文件）：

| 子模块 | 文档入口 | 说明 |
| --- | --- | --- |
| `alpha-research` | [../alpha-research/docs/](../alpha-research/docs/) | 研究信号、回测算法与评估方法 |
| `market-data-platform` | [../market-data-platform/docs/](../market-data-platform/docs/) | 行情数据供给、契约与治理 |
| `portfolio-backtester` | [../portfolio-backtester/docs/](../portfolio-backtester/docs/) | 组合回测、容量与执行模拟 |
| `quant-execution-engine` | [../quant-execution-engine/docs/](../quant-execution-engine/docs/) | 实盘执行引擎与指令路由 |
| `strategy-app` | [../strategy-app/docs/](../strategy-app/docs/) | 应用目录、迁移栈与质量门禁 |
| `strategy-pipeline` | [../strategy-pipeline/docs/](../strategy-pipeline/docs/) | 策略流水线、产出与发布 |

> 子模块文档以各仓 `docs/` 为准。如某子模块暂无 `docs/README` 索引，可直接浏览其 `docs/` 目录。

## 当前事实

- `market-intel` 是外部卫星仓，通过版本化文件接入，不参与 `print_version_matrix.py` 的版本锁定
- `src/research_contracts` 是顶层普通目录
- `src/style_factors` 是顶层普通目录，负责风格因子计算、归因、回测与报告
- A 股 current 契约是 `metadata/current_assets/a_share_current.json`
- A 股日频基线覆盖 2015-01-05 至 2026-07-16，该日期是 current 契约的数据范围快照日，时间点（PIT）财务和历史行业资产已发布
- `normalized_fundamentals` 尚未写入 current 契约，完整 PIT 策略证据仍待补齐
- `targets.json` 是研究到执行的标准交接文件
- 港股资产和历史研究输出按恢复专用归档管理

> 子模块组成、GitHub Actions 停用状态与分支策略见根目录 [README.md](../README.md)。本段只记录跨仓库事实中根 README 未涵盖的部分，避免两处各说各话。
