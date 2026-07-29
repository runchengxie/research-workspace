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
- 废弃入口：[deprecations.md](deprecations.md)
- 维护性治理：[maintainability-governance.md](maintainability-governance.md)
- 文档生命周期：[documentation-lifecycle.md](documentation-lifecycle.md)
- 架构边界发布清单：[architecture-split-closure-checklist.md](architecture-split-closure-checklist.md)
- 外部策略项目接入：[strategy-satellites.md](strategy-satellites.md)
- 策略总览导航索引（术语澄清 + 链接入口）：[strategy-catalog.md](strategy-catalog.md)
- A 股风格因子：[style-factors.md](style-factors.md)
- Owner-native 命名空间迁移记录：[namespace-migration.md](namespace-migration.md)
- 价值因子长周期轮动分析：[value-regime-18y.md](value-regime-18y.md)
- AFML 方法落地与跨仓库版本组合：[afml-methodology-rollout.md](afml-methodology-rollout.md)
- 概念级机器学习探索路线图：[concept-level-ml-exploration.md](concept-level-ml-exploration.md)
- 港股兼容面清单（已取代）：[hk-legacy-surface-inventory.md](hk-legacy-surface-inventory.md)
- 港股私有 legacy 归档（已取代）：[hk-private-archive.md](hk-private-archive.md)
- A 股生产就绪度与长窗口扩展（已取代）：[a-share-production-readiness.md](a-share-production-readiness.md)
- 外部框架适配器候选发布（已取代）：[framework-adapter-release.md](framework-adapter-release.md)

阶段记录、冻结记录和历史证据从 [archive/README.md](archive/README.md) 进入。活跃文档只保留当前做法和归档链接。

## 当前事实

- 活跃链路包含六个 Git 子模块
- `market-intel` 是外部卫星仓，通过版本化文件接入，不属于六个子模块，也不参与 `print_version_matrix.py` 的版本锁定
- `src/research_contracts` 是顶层普通目录
- `src/style_factors` 是顶层普通目录，负责风格因子计算、归因、回测与报告
- A 股 current 契约 是 `metadata/current_assets/a_share_current.json`
- A 股日频基线覆盖 2015-01-05 至 2026-07-16，时间点（PIT）财务和历史行业资产已发布
- `normalized_fundamentals` 尚未写入 current 契约，完整 PIT 策略证据仍待补齐
- `targets.json` 是研究到执行的标准交接文件
- 港股资产和历史研究输出按恢复专用归档管理
- 顶层和子模块 GitHub Actions workflow 当前停用，`research-apps` 的仓库 Actions 权限也禁用
- 顶层与六个子模块共七个仓库使用共享本地 pre-push 门禁，远端只维护 `main`
