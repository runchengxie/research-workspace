# AGENTS.md

本文件说明顶层工作区的协作规则。子仓库内部改动仍以各自的 `AGENTS.md` 为准。

## 工作区职责

顶层仓库负责以下内容：

- 锁定六个子模块的提交版本
- 维护跨仓库文件约定和 `src/research_contracts`
- 维护工作区 doctor、质量检查和子仓库委托脚本
- 维护风格因子计算内核（`alpha_research.style_factors`，alpha-research owner）、分位回测内核（`portfolio_backtester.style_factors_backtest`，portfolio-backtester owner）与表现层（`strategy-research/style_factors`，可 `python -m style_factors`）的交接与说明
- 记录版本组合、发布检查和归档入口
- 维护 `strategy-research` 中的策略身份、生命周期和证据导航
- 说明数据、研究、回测、编排和执行之间的交接方式

子仓库内部实现、依赖、业务参数和完整测试配置留在对应仓库。

`strategy-research` 是顶层仓库的 tracked 目录，不是子模块。它有独立的
`pyproject.toml` 与 `tests/`，pre-push 会额外运行其 `research-layer-tests` 与
`research-layer-quality` 门禁（见 `scripts/run_pre_push_checks.py`）。

## 仓库边界

| 仓库 | 主要职责 |
| --- | --- |
| `market-data-platform` | 数据资产生产、检查、发布和读取 |
| `alpha-research` | 特征、模型、研究评估和信号产物 |
| `portfolio-backtester` | 组合构造、回测、成本、容量、暴露和报告 |
| `strategy-app` | 策略特有的纯计算、冻结合同与研究应用，不承担生产发布 |
| `strategy-pipeline` | 运行编排、外部调用、命令行（CLI）、发布控制和 `targets.json` 导出 |
| `quant-execution-engine` | 预演、风控、券商执行、对账和审计 |

各子项目已注册的命令行入口（`strategy`、`strategy-pipeline`、`qexec`、`stockq`、`marketdata`）见
[README 子项目命令行（CLI）](README.md#子项目命令行cli)。

顶层不保存大型数据、研究运行产物、数据提供方缓存、券商凭证或交易审计日志。

## 常用检查

```bash
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
uv run --project strategy-pipeline --extra dev \
  --with 'matplotlib>=3.8' --with 'tabulate>=0.9' \
  python -m pytest tests -q
python scripts/run_quality_checks.py --profile hard
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile full --dry-run
python scripts/run_submodule_checks.py --profile release_typecheck --dry-run
```

`run_submodule_checks.py` 只执行 `scripts/submodule_checks.json` 中登记的命令。不要在顶层复制子仓库内部检查逻辑。

当前顶层和六个子模块的 GitHub Actions 仓库权限均禁用。`portfolio-backtester` 虽保留
workflow 定义，也不会触发远端检查。文档中不得把停用模板或本地命令描述为正在运行的远端 CI。

## 文件约定

A 股权威 current 契约：

```text
metadata/current_assets/a_share_current.json
```

研究到执行的权威交接文件：

```text
targets.json
```

修改跨仓库产物格式时，应同步更新生产方、消费方、顶层契约文档和对应测试。

策略投资假设、生命周期、评审结论和证据入口只在 `strategy-research` 维护。生产状态是目录中的显式元数据，不由代码位于 `strategy-app` 或 `strategy-pipeline` 推断。通用数据、alpha、统计、组合或执行能力不得放入 `strategy-app`。

## 文档规则

- 根目录 `README.md` 只保留定位、快速开始、核心边界和文档入口
- `docs/README.md` 只做导航
- 顶层 `docs/` 只记录跨仓库协作、契约、版本和发布治理
- 子仓库实现细节放在子仓库文档
- 阶段记录和历史证据放入 `docs/archive/` 或 `docs/evidence/`
- 以上写作规范同样适用于 `docs/research/` 等研究笔记文档，不限于根目录与治理文档
- 中文正文使用中文标点
- 保留必要的命令、路径、配置键和 API 名称
- 避免中英混杂的长句、翻译腔和先否定再转折的表达
- 尽量不用双引号、加粗、分号和破折号
- 文档中的命令、文件名和默认值必须能从代码或测试中核对
- 外部框架能力以 `docs/framework-support-matrix.md` 为准，历史拉取请求和跳过的测试不能写成当前支持

文档润色不得顺手修改公开接口、路径、资产键或历史产物名称。

## 测试与验证

- 文档改动至少运行链接检查、入口文档风格检查和相关事实测试
- 修改 `scripts/submodule_checks.json` 时同步更新 `tests/test_run_submodule_checks.py`
- 修改子模块列表时同步更新 `.gitmodules`、doctor、版本矩阵和测试
- 修改 Python 命名空间边界时运行 `tests/test_namespace_contracts.py` 和 `tests/test_workspace_import_boundaries.py`
- 修改 `targets.json` 或 current 契约 时运行对应契约测试

## Git 工作流

本工作区可能由多个 agent 并行开发。每个改动都必须使用独立 worktree 与功能分支，
避免多个 agent 在同一检出目录竞争同一组文件。

远端命名：本顶层 superproject 的远端名为 `github`（不是 `origin`），推送与拉取用
`git push -u github ...` / `git fetch github`。六个子模块的远端名为 `origin`，请按
各自 `AGENTS.md` 的示例操作，不要混用。

`main` 是受保护常驻分支，改动一律走 worktree + PR 流程，不直接在主检出目录提交。
功能分支（`feat/*`、`fix/*`、`hotfix/*`、`release/*`）只用于拉取请求流程、临时存在。
每个改动遵循以下顺序：

1. 从 `github/main` 新建 worktree 与功能分支：

   ```bash
   git fetch github
   git worktree add <path> -b feat/<主题> github/main
   ```

2. 在独立 worktree 内完成改动，运行与改动范围匹配的检查。
3. 提交并推送功能分支：

   ```bash
   git push -u github feat/<主题>
   ```

4. 用 `gh pr create` 开拉取请求，合并到 `main`。
5. 合并完成后删除功能分支并移除 worktree：

   ```bash
   git push github --delete feat/<主题>
   git branch -d feat/<主题>
   git worktree remove <path>
   ```

跨仓库改动遵循先子模块后顶层的顺序：先在对应子仓库（远端 `origin`）完成检查、提交、
推送并合并 `main`，再回到顶层（远端 `github`）更新 gitlink 和版本记录，最后把顶层
改动按同一 worktree + PR 流程合并。

同一仓库的多个 worktree 共享主工作树的 `core.hooksPath` 配置。不要在独立 worktree
内重装或改写 hook。新的并行任务必须新建 worktree，不要直接在主检出目录的
`main` 上提交改动。

提交前检查暂存区，避免加入以下内容：

- `.env`、`.env.*`、`.envrc`
- API 密钥、访问令牌和券商凭证
- `artifacts/`、`outputs/`、缓存和大型数据文件
- 本地绝对路径、内部主机名和私有账户信息

## 汇报顺序

跨仓库工作按数据平台、alpha 研究、组合回测、策略编排、交易执行、顶层工作区的顺序汇报。完成状态应附真实命令结果或明确说明尚未运行的检查。

## Worktree-first 与 production 目录规范

- `/home/richard/code/research-workspace` 是完整的 `main` 主工作树，作为稳定基线和人工检查入口，不是空目录。
- 并行开发、实验和 agent 任务必须在 `/home/richard/code/.worktrees/` 下创建独立 worktree 和功能分支。
- `/home/richard/code/production/research-workspace` 是定时任务使用的干净、detached production worktree，不直接编辑。
- `git push` 只更新远端，不会更新 production。代码合入 `main` 后，必须显式运行 `scripts/promote-production.sh`。
- production 更新前必须通过 clean-check，更新后必须记录父仓库与 submodule revision manifest；失败时保留原 production 版本。
- 未追踪产物、数据快照和日志不得放入可删除的 agent worktree。应放在仓库外的数据目录、被忽略的 artifacts/outputs 目录，或有明确保留策略的归档目录。
- 不得用符号链接替代 Git submodule；服务配置应指向明确的 production 路径。

production 发布流程见 [`docs/production-update.md`](docs/production-update.md)。
