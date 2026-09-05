# 贡献说明

本工作区是多个子模块的集成层。大多数功能改动应进入对应子仓库。顶层改动集中在跨仓库文件约定、子模块版本、工作区健康检查、发布清单和治理文档。

## 范围

- 数据平台改动进入 `market-data-platform`。
- L2 事件流、DeepLOB 和预测模型改动进入 `deep-learning-tick-data-prediction`。
- Alpha、因子和信号研究改动进入 `alpha-research`。
- 组合构造和研究回测改动进入 `portfolio-backtester`。
- 策略身份、生命周期、结论和证据导航进入 `strategy-research`。
- 策略特有纯计算和冻结合同进入 `strategy-app`。
- 外部调用、运行编排、发布控制和执行目标导出进入 `strategy-pipeline`。
- 交易执行改动进入 `quant-execution-engine`。
- 顶层文档和脚本只覆盖跨仓库交接、文件约定、发布、健康检查和治理事项。

改动子模块内容时，先阅读对应子模块的 `AGENTS.md`。不要回退无关的子模块改动或脏 gitlink。

## GitHub Actions

远端 CI 按仓库可见性管理：

- public 仓库默认启用 GitHub Actions，用于拉取请求的轻量自动检查。
- private 仓库默认关闭 GitHub Actions，避免持续占用私有仓库的 Actions 额度。
- private 仓库如需启用远端 CI，应记录原因、检查范围和资源成本，并由维护者明确批准。
- 本地 `pre-push` 和发布流程负责完整质量门禁。

当前可见性和状态见 [docs/quality-governance.md](docs/quality-governance.md)。

## 验证顺序

汇报验证结果时按以下顺序：

1. 数据平台。
2. 深度学习数据模型。
3. Alpha 研究。
4. 组合回测。
5. 策略研究。
6. 策略应用。
7. 策略编排。
8. 交易执行。
9. 顶层文档和 doctor。
10. 剩余限制。

未触及的仓库可以说明未运行定点测试。

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

`research-workspace` 顶层 pre-push 守卫允许 `feat/*`、`fix/*`、`hotfix/*`、`chore/*`、`release/*` 功能分支，用于拉取请求流程。`main` 和标签禁止删除。

`market-intel` 是工作区之外的独立外部仓，不参与本工作区版本锁定和检查。它的开发流程以自身文档为准。

### 标准流程

1. 从最新 `main` 建立独立 worktree 和功能分支。

   ```bash
   cd /home/richard/code/research-workspace
   git fetch github
   git worktree add /home/richard/code/.worktrees/research-workspace-my-feature \
     -b feat/my-feature github/main
   cd /home/richard/code/.worktrees/research-workspace-my-feature
   ```

2. 完成修改并运行与改动范围匹配的检查。

   顶层常用入口：

   ```bash
   python scripts/run_quality_checks.py --profile hard
   python scripts/workspace_doctor.py
   python src/research_contracts/smoke_contracts.py
   python scripts/run_workspace_tests.py
   ```

3. 提交并推送功能分支。

   ```bash
   git push -u github feat/my-feature
   ```

   推送会触发本地 pre-push 门禁。public 仓库的拉取请求还会按仓库配置触发 GitHub Actions。

4. 开拉取请求并合并到 `main`。

5. 合并后刷新主工作树和子模块。

   ```bash
   cd /home/richard/code/research-workspace
   git fetch github
   git merge --ff-only github/main
   git submodule update --init --recursive
   git status
   ```

6. 清理功能分支和 worktree。

   ```bash
   git push github --delete feat/my-feature
   git worktree remove /home/richard/code/.worktrees/research-workspace-my-feature
   git branch -d feat/my-feature
   git worktree prune
   ```

### 子模块流程

八个子模块都是独立 Git 仓库。修改子模块时，在对应子仓库自己的 worktree 中执行同样的分支、测试、PR 和清理流程，远端使用 `origin`。

跨仓库改动遵循先子仓库后顶层的顺序：

1. 在 owner 子仓完成实现和测试。
2. 合并 owner 子仓的 PR。
3. 更新依赖该 owner 的仓库 Git pin 和 lockfile，并完成其门禁。
4. 最后在顶层更新 gitlink、版本记录和跨仓契约。

不要只更新顶层 gitlink而留下子仓 `[tool.uv.sources]` 的依赖版本漂移。工作区架构扫描会报告 standalone pin 差异，集成测试还需要单独确认实际加载的是当前工作区组合。

## 常见拦截与处理

| 报错 | 含义 | 处理 |
| --- | --- | --- |
| `only refs/heads/main or refs/heads/{feat,fix,hotfix,chore,release}/* are allowed` | 分支名不在白名单 | 改用允许的功能分支前缀 |
| `repository is outside the managed workspace` | 守卫无法识别来源仓库 | 确认当前目录属于受管仓库或 linked worktree |
| `repository-clean: working tree is dirty` | 工作树有未提交改动 | 提交或丢弃改动后再推 |
| gitlink 一致性检查失败 | 子模块检出版本与顶层记录不一致 | 更新子模块检出或顶层 gitlink |
| 维护性基线或预算不符 | 当前代码测量值与治理记录不一致 | 重算基线并按负责人决策收紧或登记合理增长 |

## 提交前检查

避免提交以下内容：

- `.env`、`.env.*`、`.envrc`
- API 密钥、访问令牌和券商凭证
- `artifacts/`、`outputs/`、缓存和大型数据文件
- 本地绝对路径、内部主机名和私有账户信息

提交说明和拉取请求应写清修改内容、验证方式、兼容影响和剩余限制。
