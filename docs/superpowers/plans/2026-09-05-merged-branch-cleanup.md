# 已合并分支清理实施计划

> 按任务逐项执行本计划，并使用复选框记录完成状态。

目标：在保护 `research-workspace` 和 `market-intel` 的 `main` 与 tag 的前提下，安全删除已经合并的功能分支。

架构：保留本地且确定性的 pre-push 校验。它负责保护 `main`、tag 和分支命名空间，不调用 GitHub。增加独立的认证清理命令，在执行 `git push --delete` 前查询已合并 PR。两个仓库采用相同的策略和测试。

技术栈：Bash hook、Python 3.12+、pytest、GitHub CLI（`gh`）、Git。

依据：用户对话中批准的分支清理策略。

## 全局约束

- 继续禁止删除 `main` 和 tag。
- 只允许删除 `feat/*`、`fix/*`、`hotfix/*`、`chore/*` 和 `release/*` 分支。
- 已合并 PR 的验证放在显式清理命令中，不放入普通 pre-push hook。
- 不绕过仓库质量门禁，也不修改生产发布。
- 两个仓库都使用独立 worktree 和 PR。

### 任务 1：工作区推送策略

文件：
- 修改：`scripts/run_pre_push_checks.py`
- 测试：`tests/test_run_pre_push_checks.py` 或现有的推送引用校验测试位置

- [ ] 增加失败测试，证明允许的功能分支删除可以通过，而 `main`、tag 和未批准的分支名称仍会被拒绝。
- [ ] 运行针对性测试，确认失败原因是当前删除规则。
- [ ] 只修改 `_destination_issue` 中处理删除的分支。
- [ ] 运行针对性测试、lint 和格式检查。

### 任务 2：工作区已合并 PR 清理命令

文件：
- 新建：`scripts/cleanup_merged_branches.py`
- 测试：`tests/test_cleanup_merged_branches.py`
- 修改：`README.md` 或相关工作流文档

- [ ] 通过注入命令运行器，测试分支名称校验、已合并 PR 选择、未合并 PR 拒绝和 dry-run 行为。
- [ ] 实现无额外依赖的 CLI，使用 `gh pr list`、`gh pr view`，只有确认 PR 已合并后才运行 `git push --delete`。
- [ ] 支持 `--branch`、`--remote`、`--dry-run` 和 `--yes`。删除操作必须显式提供 `--yes`。
- [ ] 记录命令用法和安全行为。

### 任务 3：market-intel 推送策略和清理命令

文件：
- 修改：`project_tools/pre_push_guard.py`
- 测试：`tests/test_pre_push_guard.py`
- 新建：`project_tools/cleanup_merged_branches.py`
- 测试：`tests/test_cleanup_merged_branches.py`
- 修改：相关 market-intel 工作流文档

- [ ] 增加相同的删除策略失败测试，并确认测试为红。
- [ ] 应用相同的确定性目标策略。
- [ ] 实现并记录显式的已合并 PR 清理命令，要求使用 `--yes` 确认。
- [ ] 运行 market-intel 的完整本地门禁。

### 任务 4：修复本地 hook 配置并完成审查

文件：
- 仅本地：`research-workspace` 仓库配置 `core.hooksPath`

- [ ] 代码改动合并后，将 main 检出中的过期 hook 路径重置为 `.githooks`。
- [ ] 运行两个仓库的完整验证命令。
- [ ] 每个 PR 合并前请求或执行只读审查。
- [ ] 合并两个 PR，更新 main 检出，并以 dry-run 模式验证清理命令。
