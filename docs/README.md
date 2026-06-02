# 顶层文档入口

这里收录 superproject 层级的说明，只覆盖跨仓库协作、contract、版本锁定和发布检查。子项目内部的依赖、业务命令、架构规则和测试要求仍以各自 README / docs 为准。

当前工作区的活跃方向是 A 股数据、策略研究和执行交接。港股真实资产和研究输出按冷存储 /
恢复边界保留；公开展示使用外部 paused-maintenance 的 synthetic / public-safe demo 仓库，
独立于本工作区 submodule、依赖和必跑 CI 目标，不承接真实 provider、broker 或 restore
实现代码。

## 推荐阅读顺序

| 场景 | 阅读 |
| --- | --- |
| 第一次拉起工作区 | [bootstrap.md](bootstrap.md) |
| 先理解整体链路 | [platform-workflow.md](platform-workflow.md) |
| 了解顶层架构边界 | [../ARCHITECTURE.md](../ARCHITECTURE.md) |
| 了解协作和变更规则 | [../CONTRIBUTING.md](../CONTRIBUTING.md) |
| 推进 A 股主线或恢复港股归档 | [data-transition-playbook.md](data-transition-playbook.md) |
| 查看中国香港市场归档入口 | [archive/hk/README.md](archive/hk/README.md) |
| 查看港股 legacy 保留、归档和 sunset 边界 | [hk-legacy-surface-inventory.md](hk-legacy-surface-inventory.md) |
| 查看港股私有 legacy 归档候选和只读门禁 | [hk-private-archive.md](hk-private-archive.md) |
| 查看港股私有归档 manifest | [hk-private-archive-manifest.yml](hk-private-archive-manifest.yml) |
| 查看港股 public split manifest | [hk-public-split-manifest.yml](hk-public-split-manifest.yml) |
| 导出外部暂停维护的港股公开 demo | [hk-public-demo-export.md](hk-public-demo-export.md) |
| 查看 A 股 readiness 分层与验收命令 | [data-transition-playbook.md](data-transition-playbook.md#a-股-readiness-分层) |
| 查看 A 股生产 readiness 与长窗口扩展计划 | [a-share-production-readiness.md](a-share-production-readiness.md) |
| 确认上下游文件约定 | [contracts.md](contracts.md) |
| 查看维护债治理入口 | [maintainability-governance.md](maintainability-governance.md) |
| 查看 deprecated 入口删除条件 | [deprecations.md](deprecations.md) |
| 维护子模块指针或顶层检查 | [workspace-maintenance.md](workspace-maintenance.md) |
| 查看 hard、advisory 和 manual 质量 gate | [quality-governance.md](quality-governance.md) |
| 查看当前版本组合 | [version-matrix.md](version-matrix.md) |
| 发布或更新组合前检查 | [release-checklist.md](release-checklist.md) |

## 文档分层

- 活跃文档：初始化、当前跨仓库工作流、A 股 readiness、contract、release checklist。
- 参考文档：长期稳定的文件约定、质量治理、维护流程和 public demo 导出。
- 归档文档：[archive/README.md](archive/README.md) 下的交接记录、冻结记录和历史证据。

## 文档边界

- 顶层文档写数据平台、策略研究、交易执行之间的交接方式。
- 子项目内部实现、业务参数和完整命令说明放在子项目自己的文档里。
- 大型市场数据、研究 run、交易审计日志和 provider cache 不进入顶层仓库。
