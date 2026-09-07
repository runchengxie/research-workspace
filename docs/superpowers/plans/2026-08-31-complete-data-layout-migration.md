# 完整数据布局迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

目标：完成混合研究和管道资产目录的第二轮安全分类，同时不破坏现有报告和生产方。

架构：将物理数据移动到规范生命周期根目录，旧路径改为符号链接。现有代码和 cron 默认值继续保持兼容，直到单独的跨仓库改动通过影子运行和观察周期证明规范路径读取有效。

技术栈：POSIX 文件系统、符号链接、JSON 迁移凭证、Markdown 契约、现有 `data_path_audit.py` 和 Git PR 流程。

规格：`docs/data-lifecycle-terminology.md`、`docs/data-path-migration-map.md` 和 `docs/data-path-breaking-change-register.md`

## 全局约束

- 本次迁移不得删除研究数据或运行数据。
- 通过兼容符号链接保持旧路径可读写。
- 不要修改生产发布目录或当前别名。
- 影子读取、dry-run、契约检查和两个观察周期全部通过前，不得声称已经完成生产切换。

### 任务 1：审计并分类混合根目录

- [x] 检查 `watchlist20/research`、`strategy-pipeline/artifacts` 和 `market-data-platform/research` 的消费者、大小、文件数量和符号链接。
- [x] 移动目录前确认没有活动进程占用这些目录。
- [x] 将研究输出归类为 `experiments/strategies/watchlist20`，将管道命名空间归类为 `assets`、`cache`、`metadata`、`reports`、`runs` 和 `snapshots`。

### 任务 2：使用兼容别名移动实体

- [x] 将 `strategy_outputs/watchlist20/research` 移动到 `experiments/strategies/watchlist20`，并将旧路径重新创建为符号链接。
- [x] 将每个 `strategy-pipeline/artifacts/*` 命名空间移动到对应项目数据根目录，并将每个旧路径重新创建为符号链接。
- [x] 保留 `market-data-platform/research` 兼容符号链接，因为其物理内容已经迁移。

### 任务 3：记录并验证迁移

- [x] 写入 `/home/richard/data/market-data-platform/metadata/lifecycle/migrations/research-and-pipeline-artifacts-layout-20260831.json`，记录清单哈希和回滚说明。
- [x] 重新生成 `/home/richard/data/market-data-platform/metadata/lifecycle/path-audit-20260831.json`。
- [x] 验证旧路径和规范路径、`latest` 目标、凭证以及生产发布目录的清洁状态。

### 任务 4：记录剩余破坏性变更门禁

- [x] 更新父级迁移图和破坏性变更登记表，记录规范位置和别名状态。
- [x] 记录源代码默认值和 cron 配置仍需要单独选择启用规范路径改动。
- [ ] 后续代码 PR 完成后，在删除别名前运行一次完整影子周期、报告 dry-run、契约检查和两个观察周期。

### 任务 5：评审并合并文档

- [ ] 运行 `pytest tests/test_data_path_audit.py -q` 和 `git diff --check`。
- [ ] 提交文档，推送功能分支，并将 PR 合并到 `main`。
