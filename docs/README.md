# 顶层文档入口

这里收录 superproject 层级的说明，只覆盖跨仓库协作、contract、版本锁定和发布检查。子项目内部的依赖、业务命令、架构规则和测试要求仍以各自 README / docs 为准。

## 推荐阅读顺序

| 场景 | 阅读 |
| --- | --- |
| 第一次拉起工作区 | [bootstrap.md](bootstrap.md) |
| 先理解整体链路 | [platform-workflow.md](platform-workflow.md) |
| 判断先归档港股还是推进 A 股数据 | [data-transition-playbook.md](data-transition-playbook.md) |
| 确认上下游文件约定 | [contracts.md](contracts.md) |
| 维护子模块指针或顶层检查 | [workspace-maintenance.md](workspace-maintenance.md) |
| 查看当前版本组合 | [version-matrix.md](version-matrix.md) |
| 发布或更新组合前检查 | [release-checklist.md](release-checklist.md) |

## 文档边界

- 顶层文档写数据平台、策略研究、交易执行之间的交接方式。
- 子项目内部实现、业务参数和完整命令说明放在子项目自己的文档里。
- 大型市场数据、研究 run、交易审计日志和 provider cache 不进入顶层仓库。
