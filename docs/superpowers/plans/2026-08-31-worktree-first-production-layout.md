# Worktree 优先的生产布局实施计划

> 面向智能体执行者：必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项执行本计划。步骤使用复选框（`- [ ]`）跟踪。

目标：建立规范可靠的布局，使主检出目录包含完整的 `main` 代码库，agent 在隔离 worktree 中工作，定时任务从明确版本化的生产检出目录运行。

架构：`/home/richard/code/research-workspace` 继续作为规范的 `main` 检出目录，不用作 agent 临时目录。`/home/richard/code/.worktrees/` 存放可丢弃或待评审的 worktree。`/home/richard/code/production/` 存放 detached 且干净的部署检出，只通过明确的晋升命令更新。

技术栈：Git worktree、Git 子模块、Bash、systemd 用户服务和 Python/uv。

规格：`docs/market-intel-owner-boundary.md` 和仓库 `AGENTS.md` 中的 worktree 优先规则。

## 全局约束

- 不得用符号链接表示 Git 子模块。
- 识别并保留未提交文件前，不得删除它们。
- 定时服务必须使用生产路径，不能使用 agent worktree。
- 生产晋升必须记录更新前后的父仓库和子模块版本。
- 生产检出必须保持干净，并 detached 在明确选择的提交上。

---

### 任务 1：恢复规范主检出目录

文件：
- Modify: `/home/richard/code/research-workspace/` Git worktree state
- Verify: parent and all submodule worktrees

- [ ] 确认服务路径已有生产目标后，只删除两个已知兼容符号链接。
- [ ] 从 `github/main` 填充主检出目录，并按正常方式初始化子模块。
- [ ] 确认主检出目录完整且干净，所有子模块路径都不是符号链接。

### 任务 2：定义 agent worktree 位置

**Files:**
- Modify: `AGENTS.md`
- Modify: each maintained submodule `AGENTS.md`
- Verify: `.gitignore` and `git worktree list`

- [ ] 说明主检出目录是完整稳定的基线，不是空的控制目录。
- [ ] 说明新的 agent worktree 必须位于 `/home/richard/code/.worktrees/` 下，并使用 `git worktree add` 创建。
- [ ] 说明未跟踪输出应放在被忽略的资产或数据位置，或放在 Git 之外，不能在没有保留策略的可丢弃 worktree 中保存。

### 任务 3：增加明确的生产晋升流程

**Files:**
- Create: `scripts/promote-production.sh`
- Create: `docs/production-update.md`
- Modify: `AGENTS.md`

- [ ] 实现支持 dry-run 的晋升命令，fetch `main`，检查干净的生产检出，更新父仓库和子模块，并打印最终版本清单。
- [ ] 记录 `git push` 只更新远端，生产只有在晋升后才会变化。
- [ ] 记录预检、晋升、回滚和晋升后验证命令。

### 任务 4：让定时执行指向生产目录

**Files:**
- Modify: affected systemd user unit files and environment files
- Verify: `systemctl --user daemon-reload` and unit command paths

- [ ] 对计划投入运行的服务，将过期开发路径替换为明确的生产路径。
- [ ] 对仅供研究的服务进行明确分类，不要静默切换。
- [ ] 重新加载用户单元，确认关键的每日和每周入口解析到生产路径。

### 任务 5：验证并记录最终状态

**Files:**
- Verify: parent, submodules, production checkout, service definitions

- [ ] 确认主仓库 `main` 和生产版本清单。
- [ ] 确认所有生产 worktree 干净且 detached。
- [ ] 运行相关仓库 doctor、契约测试和 dry-run 生产晋升。
- [ ] 记录有意保留在代码晋升路径之外的脏研究数据。
