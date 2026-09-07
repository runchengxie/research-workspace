# 分支和 Worktree 退役实施计划

> 面向智能体执行者：必须使用 `superpowers:executing-plans`，按任务逐项执行本计划。

目标：审计剩余开发 worktree 和非 main 分支，保留有用改动，只退役已经确认过时或已经合并的内容。

架构：将 `main` 和生产发布视为规范状态。根据提交和 PR 状态检查每个 detached worktree 与远端分支，必要时将有用改动提取到已接收分支，再只删除已经确认可以丢弃的 worktree 或引用。

技术栈：Git worktree、GitHub CLI、仓库质量门禁和 Markdown 审计记录。

规格：根据用户关于合并或提取有用增量，以及退役过期或已被替代分支和 worktree 的要求。

## 全局约束

- 检查并保留未提交改动前，不得删除它们。
- 没有明确分类前，不要修改 market-intel 开发快照。
- 不要删除生产发布 worktree，它们是回滚目标。
- 使用 fast-forward 或经过评审的 PR 合并，不要强推共享分支。

### 任务 1：审计每个剩余 worktree 和分支

文件：
- Create: `docs/branch-worktree-retirement-audit.md`

- [ ] 记录每个候选项的路径、仓库、提交、分支、worktree 清洁状态、PR 状态和处理决定。
- [ ] 将远端引用与 `git ls-remote` 比较，避免把过期的本地跟踪引用误认为仍然存在的远端分支。
- [ ] 对内容或归属尚未明确的候选项停止操作并保留。

### 任务 2：合并或提取有用增量

**Files:**
- Modify: repository files only when a reviewed increment is clearly safe.
- Test: repository-specific tests and quality gates.

- [ ] 对每个存在开放 PR 或有用提交的候选项，检查其相对于当前 `main` 的差异。
- [ ] 只有检查和归属都合适时才合并，否则记录原因并保留。
- [ ] 对没有 Git 元数据的孤立文件，只将明确选择的有用文件复制到新的评审分支，并记录来源。

### 任务 3：退役已确认过时的状态

**Files:**
- Modify: local Git worktree metadata and remote refs only after confirmation from Tasks 1–2.

- [ ] 确认不存在可恢复提交后，才删除空 worktree 或孤立 worktree 目录。
- [ ] 远端分支只有在已合并、已被替代或已在审计中明确归档时才删除。
- [ ] 删除远端分支后清理本地远端跟踪引用。

### 任务 4：验证最终状态

- [ ] 确认 main 检出目录干净，生产 `current` 链接没有变化。
- [ ] 确认没有遗留非预期的开发 worktree。
- [ ] 确认审计文档记录了每个保留或退役的项目。
