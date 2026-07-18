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
| 查看当前锁定组合 | [version-matrix.md](version-matrix.md) |
| 发布或更新组合 | [release-checklist.md](release-checklist.md) |
| 推进 A 股主线或恢复港股归档 | [data-transition-playbook.md](data-transition-playbook.md) |
| 查看港股恢复专用归档 | [archive/hk/README.md](archive/hk/README.md) |

## 参考资料

- 框架集成边界：[adr/0001-framework-integration-boundaries.md](adr/0001-framework-integration-boundaries.md)
- Python 命名空间决策：[adr/0002-owner-native-python-namespaces.md](adr/0002-owner-native-python-namespaces.md)
- 废弃入口：[deprecations.md](deprecations.md)
- 维护性治理：[maintainability-governance.md](maintainability-governance.md)
- 文档生命周期：[documentation-lifecycle.md](documentation-lifecycle.md)
- 架构边界发布清单：[architecture-split-closure-checklist.md](architecture-split-closure-checklist.md)
- 外部策略项目接入：[strategy-satellites.md](strategy-satellites.md)
- A 股风格因子：[style-factors.md](style-factors.md)

阶段记录、冻结记录和历史证据从 [archive/README.md](archive/README.md) 进入。活跃文档只保留当前做法和归档链接。

## 当前事实

- 活跃链路包含六个 Git 子模块
- `src/research_contracts` 是顶层普通目录
- A 股 current contract 是 `metadata/current_assets/a_share_current.json`
- A 股日频基线覆盖 2015-01-05 至 2026-07-16，PIT 财务和历史行业资产已发布
- `normalized_fundamentals` 尚未写入 current contract，完整 PIT 策略证据仍待补齐
- `targets.json` 是研究到执行的标准交接文件
- 港股资产和历史研究输出按恢复专用归档管理
- 顶层和子模块 GitHub Actions workflow 当前停用，`research-apps` 的仓库 Actions 权限也禁用
- 七个仓库使用共享本地 pre-push 门禁，远端只维护 `main`
