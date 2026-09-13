# 遗留变更台账

更新时间：2026-09-13

本台账用于避免开发 worktree、stash 和开放 PR 变成不可追踪的隐性技术债务。未进入
`main` 的内容不代表可以进入 production；只有通过对应仓库门禁并完成 PR 合并后，才
允许更新 production release。

## 当前遗留项

### research-workspace 主工作树

- 路径：`/home/richard/code/research-workspace`
- 分支：`chore/record-consumer-compatibility-approval`
- 状态：`checkpoint`
- 未提交：`quant-research` gitlink，以及 `docs/superpowers/plans/2026-09-07-quant-workspace-convergence.md`
- 后续：先保存迁移计划，再单独审查 gitlink。旧 submodule 删除必须等待回滚窗口和 owner 验收。

### daily-feishu10 backtest worktree

- 路径：`/home/richard/code/.worktrees/research-workspace-daily-feishu10-backtest`
- 分支：`feat/daily-feishu10-backtest-plan`
- 状态：`research-only`
- 特征：领先 `github/main` 18 个提交；7 个 submodule 有指针或 index 状态变化，包含 staged 删除。
- 后续：保存各 submodule SHA 和 patch，再拆分回测证据、文档和代码；staged 删除暂不提交。

### public-platform-decoupling worktree

- 路径：`/home/richard/code/quant/quant-intel-deploy/.worktrees/public-platform-decoupling`
- 分支：`chore/public-platform-decoupling`
- 状态：`candidate`
- 特征：包含部署路径、环境变量、调度默认值、refresh 行为和兼容路径变更。
- 后续：拆成文档、路径边界、运行行为三个 PR。运行行为需 shadow、失败恢复和回滚验证。

### research-workspace 依赖更新

- PR：#667、#668、#669、#670
- 状态：`blocked`
- 阻塞：旧 PR 的 lockfile 与当前约束不一致；consolidated replacement 分支的本地 hook 要求所有 submodule 配置共享 `core.hooksPath`，当前检查未通过。
- 后续：统一修复 hook 安装/检查流程，再用一个 PR 更新四个约束和 `uv.lock`。不得使用 `--no-verify`。

### quant-research 开放研究 PR

- PR：#134、#128、#120、#108、#99、#98、#97
- 状态：`research-only`
- 后续：补充研究假设、数据版本、复现命令和 production eligibility；冲突或被替代的 PR 关闭时保留替代关系。

### 剩余 stash

- quant-intel-deploy：大型调度、依赖和路径变更，状态 `checkpoint`，禁止整体应用。
- quant-intel-platform：旧迁移状态的大型 stash，状态 `checkpoint`，先拆文档和代码。
- 已确认与正式提交 patch-id 相同的 market-data-platform、quant-research stash 已删除。

## 生命周期规则

1. 新发现的 dirty worktree 在 7 天内必须变成 checkpoint、Draft PR 或关闭记录。
2. checkpoint 每 30 天复查；60 天没有变化则决定归档或删除。
3. stash 不作为长期保存形式；有价值内容转为命名分支或 patch 归档。
4. 研究内容、生产调度和 submodule gitlink 分开提交、分开 review。
5. 只有 main 中已合并且通过发布门禁的不可变 commit 才能进入 production。
