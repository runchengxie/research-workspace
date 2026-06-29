# 顶层文档入口

> status: active
> owner: workspace
> last_verified: 2026-06-10
> source_of_truth: yes
> superseded_by: n/a

这里收录顶层工作区说明，只覆盖跨仓库协作、文件约定、版本锁定和发布检查。子项目内部的依赖、业务命令、架构规则和测试要求仍以各自 README 和 docs 为准。

当前工作区的活跃方向是 A 股数据、策略研究和执行交接。港股真实资产、研究输出和历史代码
按冷存储和恢复专用归档保留。工作区不再维护
公开演示路线或独立港股研究线。

## 推荐阅读顺序

| 场景 | 阅读 |
| --- | --- |
| 第一次拉起工作区 | [bootstrap.md](bootstrap.md) |
| 先理解整体链路 | [platform-workflow.md](platform-workflow.md) |
| 了解顶层架构边界 | [../ARCHITECTURE.md](../ARCHITECTURE.md) |
| 了解协作和变更规则 | [../CONTRIBUTING.md](../CONTRIBUTING.md) |
| 推进 A 股主线或恢复港股归档 | [data-transition-playbook.md](data-transition-playbook.md) |
| 查看中国香港市场归档入口 | [archive/hk/README.md](archive/hk/README.md) |
| 查看港股私有归档清单 | [hk-private-archive-manifest.yml](hk-private-archive-manifest.yml) |
| 查看港股公开拆分清单 | [hk-public-split-manifest.yml](hk-public-split-manifest.yml) |
| 查看 A 股就绪度分层与验收命令 | [data-transition-playbook.md](data-transition-playbook.md#a-股-readiness-分层) |
| 运行 A 股 Barra 风格 proxy 和策略归因 | [style-factors.md](style-factors.md) |
| 确认上下游文件约定 | [contracts.md](contracts.md) |
| 查看跨仓库研究完整性和防过拟合边界 | [platform-workflow.md](platform-workflow.md#研究完整性和防过拟合边界) |
| 查看维护债治理入口 | [maintainability-governance.md](maintainability-governance.md) |
| 查看文档生命周期和归档规则 | [documentation-lifecycle.md](documentation-lifecycle.md) |
| 了解策略卫星项目和接入方式 | [strategy-satellites.md](strategy-satellites.md) |
| 查看废弃入口删除条件 | [deprecations.md](deprecations.md) |
| 维护子模块指针或运行顶层检查 | [workspace-maintenance.md](workspace-maintenance.md) |
| 查看质量门禁、建议项和人工复核项 | [quality-governance.md](quality-governance.md) |
| 查看阶段4拆分收敛清单 | [architecture-split-closure-checklist.md](architecture-split-closure-checklist.md) |
| 查看当前版本组合 | [version-matrix.md](version-matrix.md) |
| 发布或更新组合前检查 | [release-checklist.md](release-checklist.md) |
| 了解顶层本地契约薄包 | [contracts.md](contracts.md#跨模块-artifact-contract) |

## 文档分层

- 活跃文档：初始化、当前跨仓库工作流、A 股就绪度、文件约定、发布检查清单。
- 参考文档：长期稳定的文件约定、质量治理和维护流程。
- 归档文档：[archive/README.md](archive/README.md) 下的交接记录、冻结记录和历史证据。
- 生命周期规则：[documentation-lifecycle.md](documentation-lifecycle.md) 定义 `active`、`reference`、`archived` 和 `superseded` 的状态字段。
- 兼容入口：`hk-legacy-surface-inventory.md`、`hk-private-archive.md`、
  `a-share-production-readiness.md` 保留给旧链接，当前入口分别见
  [archive/hk/README.md](archive/hk/README.md) 和
  [data-transition-playbook.md](data-transition-playbook.md)。

## 文档边界

- 顶层文档写数据平台、策略研究、交易执行之间的交接方式。
- 子项目内部实现、业务参数和完整命令说明放在子项目自己的文档里。
- `src/research_contracts` 是顶层本地薄包，用于加载和校验跨仓库 artifact contract 清单，不登记为 Git 子模块。
- 大型市场数据、研究 run、交易审计日志和 provider 缓存不进入顶层仓库。
