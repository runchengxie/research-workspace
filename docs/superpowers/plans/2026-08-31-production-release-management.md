# 生产发布管理实施计划

> 面向智能体执行者：必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项执行本计划。步骤使用复选框（`- [ ]`）跟踪。

目标：通过不可变发布 worktree、`current` 指针、自动 fetch 通知和明确的人或 agent 晋升流程，管理 research-workspace 和 market-intel 生产代码。

架构：每个生产仓库都有 `releases/<commit>` worktree 和相对路径 `current` 符号链接。服务只引用 `current`。只执行 fetch 的 systemd 定时器报告远端新版本，晋升流程创建并验证发布版本，再原子切换 `current`，不删除旧发布。

技术栈：Git worktree、Bash、systemd 用户单元、uv 和 `flock`。

规格：`docs/production-update.md`。

## 全局约束

- fetch 不改变正在运行的发布版本。
- 已有晋升运行时，不得同时启动另一个晋升。
- 现有发布目录不可变，不自动删除。
- 正在运行的 `current` 发布必须干净，并有记录版本的清单。
- 服务必须引用 `current`，不能引用 agent worktree。

---

### 任务 1：增加面向发布的晋升和 fetch 审计命令

文件：
- Create: `scripts/promote-production.sh`
- Create: `scripts/check-production-updates.sh`
- Modify: `docs/production-update.md`
- Modify: `AGENTS.md`

- [ ] 为两个仓库的晋升流程增加 `--dry-run` 支持。
- [ ] 让晋升流程创建并校验 `releases/<commit>`，再原子替换 `current`。
- [ ] 让晋升流程保留旧发布，并打印双仓库清单。
- [ ] 增加只执行 fetch 的更新检测，并返回适合 systemd 通知的退出状态。
- [ ] 记录手动晋升、只执行 fetch 的检查、回滚和发布保留规则。

### 任务 2：增加只执行 fetch 的 systemd 监控

**Files:**
- Create: `/home/richard/.config/systemd/user/research-production-update-check.service`
- Create: `/home/richard/.config/systemd/user/research-production-update-check.timer`

- [ ] 按每日计划运行只执行 fetch 的检查。
- [ ] 确保检查不会修改正在运行的生产代码。
- [ ] 将更新报告写入用户日志，只将失败状态用于运维告警。

### 任务 3：迁移现有生产 worktree

**Files:**
- Modify: `/home/richard/code/production/research-workspace/`
- Modify: `/home/richard/code/production/market-intel/`
- Modify: affected systemd unit paths

- [ ] 将当前版本保留为第一批发布目录。
- [ ] 创建相对路径的 `current` 符号链接。
- [ ] 让所有运维单元指向 `current`。
- [ ] 将 `.env.local` 保留在发布代码之外，并在需要时显式加载。

### 任务 4：验证发布和回滚行为

**Files:**
- Verify: production manifests, symlinks, systemd units, Git worktree registrations

- [ ] 确认两个当前发布都干净，服务通过 `current` 解析。
- [ ] 运行 dry-run 更新检查和晋升检查。
- [ ] 确认回滚只改变指针，并保留旧发布。
- [ ] 确认服务路径无法访问 agent worktree。
