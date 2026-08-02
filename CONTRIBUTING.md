# 贡献说明

本工作区是多个子模块的集成层。大多数功能改动应进入对应子仓库。顶层改动集中在
跨仓库文件约定、子模块版本、工作区健康检查、发布清单和治理文档。

## 范围

- 数据平台改动进入 `market-data-platform`。
- Alpha、因子和信号研究改动进入 `alpha-research`。
- 组合构造和研究回测改动进入 `portfolio-backtester`。
- 策略编排、命令行（CLI） 兼容层和执行目标导出改动进入 `strategy-pipeline`。
- 交易执行改动进入 `quant-execution-engine`。
- 顶层文档和脚本只覆盖跨仓库交接、文件约定、发布、健康检查和治理事项。

改动子模块内容时，先阅读对应子模块的 `AGENTS.md`，并在最终汇报中包含子模块 `git status --short`。不要回退无关的子模块改动或脏 gitlink。

## 验证顺序

汇报验证结果时按以下顺序：

1. 数据平台。
2. Alpha 研究。
3. 组合回测。
4. 策略编排。
5. 交易执行。
6. 顶层文档和 doctor。
7. 剩余限制。

未触及的仓库说明无需 focused tests。

## 维护治理门禁

提交前检查改动是否涉及以下事项：

- 新增或扩展已废弃入口。
- 新增一次性脚本或迁移工具。
- 新增 Ruff 或 `ty` 排除项。
- 改动 `targets.json` 交接约定。
- 读取数据供应商或券商凭证。
- 需要迁移说明、回退路径、恢复证据或定点验证。

这些检查的权威入口是 [docs/deprecations.md](docs/deprecations.md)、[docs/script-lifecycle.yml](docs/script-lifecycle.yml)、[docs/quality-coverage-governance.yml](docs/quality-coverage-governance.yml) 和 [docs/maintainability-refactor-roadmap.yml](docs/maintainability-refactor-roadmap.yml)。

## 开发流程

`research-workspace` 顶层已放开 pre-push 守卫，允许推送 `feat/*`、`fix/*`、`hotfix/*`、`release/*` 前缀的功能分支，用以走拉取请求流程。主线 `main` 仍受保护（禁止删除，标签禁止删除）。

`market-intel` 是工作区之外的独立外部仓，不参与本工作区的版本锁定与检查，其 pre-push 守卫流程仅作类比参考，具体以 `market-intel` 自己的仓库约定为准。

### 关键事实

- 守卫放行的是功能分支前缀，不是任意分支名。推 `experiment`、`tmp` 这类无前缀分支仍会被拒绝。
- `research-workspace` 的 pre-push 钩子通过 `.githooks/pre-push` 继承到子模块推送。子模块是独立 Git 仓库，各自有钩子，请在子模块自己的 worktree 里改子模块代码。
- 合并进 `main` 的内容必须经过 pre-push 门禁，门禁在 push 时运行，不在 PR 创建时运行。

### 标准流程（顶层仓库）

下面以 `research-workspace` 为例，`market-intel` 把 `github` 换成 `origin` 即可。

1. 开 worktree 与功能分支。

   ```bash
   cd /home/richard/code/research-workspace
   git worktree add /home/richard/code/research-workspace-my-feature -b feat/my-feature
   cd /home/richard/code/research-workspace-my-feature
   ```

   分支名必须以 `feat/`、`fix/`、`hotfix/`、`release/` 之一开头，否则推送会被守卫拒绝。

2. 改代码并提交。涉及治理基线或 ratchet 预算的合法代码增量，可能触发 pre-push 门禁要求重算基线或上调预算。遇到这类拦截，先按报错在本地把 `docs/maintainability-baseline.json`（用 `scripts/maintainability_baseline.py` 重算）和 `docs/maintainability-refactor-roadmap.yml` 对齐，再提交，不要跳过钩子。

3. 从 worktree 直接推功能分支。

   ```bash
   git push github feat/my-feature
   ```

   这一步会触发完整 pre-push 门禁（质量检查、workspace-doctor、契约冒烟、根测试）。全部通过后分支出现在远端，可在 GitHub 开 PR。

   早期版本里从 worktree 直推会被守卫判为 `repository is outside the managed workspace` 而拒绝。该限制已在 `scripts/run_pre_push_checks.py` 的 `plan_gate` 中通过 `_is_same_git_repo` 识别 linked worktree 而解除，当前版本可直接推。

4. 开 PR 并合并回 `main`。合并后进主工作树拉取并更新子模块。

   ```bash
   cd /home/richard/code/research-workspace
   git fetch github
   git merge --ff-only github/main
   git submodule update --init --recursive
   git status   # 应干净，且子模块 gitlink 与记录一致
   ```

5. 清理功能分支与 worktree。

   ```bash
   git push github --delete feat/my-feature
   git worktree remove /home/richard/code/research-workspace-my-feature --force
   git branch -d feat/my-feature
   git worktree prune
   ```

### 子模块的等价流程

六个子模块（alpha-research、market-data-platform、portfolio-backtester、quant-execution-engine、research-apps、strategy-pipeline）各自是独立仓库。改子模块代码时，在子模块自己的 worktree 里走同样的五步，远程用各子模块的 `origin`。子模块进入 `main` 后，回到顶层仓库把 `docs/owner-native-namespace-release.json` 里对应的 `commit` 字段更新到新提交，再提交顶层，以满足 `test_owner_native_manifest_matches_gitlinks` 契约。

### 常见拦截与处理

| 报错 | 含义 | 处理 |
| --- | --- | --- |
| `only remote branch refs/heads/main is allowed` | 分支名不是白名单前缀 | 改成分支名以 `feat/`、`fix/`、`hotfix/`、`release/` 开头 |
| `repository is outside the managed workspace` | 守卫无法识别来源仓库 | 确认在 worktree 或主工作树内推送。当前版本 worktree 已支持，若仍出现检查 cwd 是否在该仓库内 |
| `test_owner_native_manifest_matches_gitlinks` 失败 | 子模块 gitlink 与 `owner-native-namespace-release.json` 不一致 | 把 manifest 里对应子模块的 `commit` 更新为实际提交 |
| `repository-clean: working tree is dirty` | 工作树有未提交改动 | 提交或丢弃改动后再推 |
| 门禁报基线或 ratchet 预算不符 | 代码增量合法但超阈值 | 用 `scripts/maintainability_baseline.py` 重算基线，并按 owner decision 调整 `maintainability-refactor-roadmap.yml` 预算 |
