# internal runtime 归档审计

## 审计结论

internal 当前 `pipeline` 和 `liveops` 目录仍保留一批历史实现与 owner 适配层。它们包括 panel 加载、评估、输出编排、运行时辅助、allocation、holdings、snapshot 和 targets 导出等模块。

审计确认：

- workspace production 使用公共 `strategy-pipeline` 和 owner-native API，不调用 internal runtime。
- targets、执行和审计入口由 `quant-execution-engine` 负责。
- 数据读取和 provider 能力由 `market-data-platform` 提供。
- 研究与策略相关 owner 已完成 active consumer 切换，internal runner 仅保留历史引用。
- 当前没有 workspace、定时任务或 owner 仓库把这些 internal runtime 模块作为 active 入口。

## 处理方式

`pipeline` 和 `liveops` 剩余代码标记为 `archive`。公共控制面和可复用 owner 能力保留在对应公共仓库，internal 中的实现仅用于历史复核和恢复参考，不再继续维护为 active runtime。

恢复时必须从 `retirement-freeze-20260905-r1` 创建独立恢复分支，重新核对各 owner API、版本矩阵、artifact contract 和 production smoke。恢复结果不能自动成为 workspace 或 production 的 active consumer。
