# 工作区维护

本页说明顶层仓库的日常维护、子模块更新和验证要求。

## 顶层负责什么

适合放在顶层的内容：

- 跨仓库文件约定和发布治理
- Git 子模块指针（gitlink）
- `src/research_contracts`
- 工作区 doctor、质量检查和委托脚本
- 版本矩阵、发布清单和归档入口

子仓库内部架构、依赖、业务参数、数据生产逻辑和券商实现留在对应仓库。

## 更新子模块

先在子仓库完成修改、测试和提交：

```bash
cd alpha-research
git status
git add <files>
git commit -m "..."
git push
```

再回到顶层更新子模块指针：

```bash
cd ..
git status
git add alpha-research
git commit -m "chore: update alpha-research"
git push
```

一次更新多个子仓库时，应先分别验证，再统一更新顶层子模块指针和 [version-matrix.md](version-matrix.md)。

## 顶层验证

| 目标 | 命令 |
| --- | --- |
| 工作区状态 | `python scripts/workspace_doctor.py` |
| 契约冒烟 | `python src/research_contracts/smoke_contracts.py` |
| 顶层测试 | `python scripts/run_workspace_tests.py` |
| 硬质量门禁 | `python scripts/run_quality_checks.py --profile hard` |
| 跨仓库导入边界 | `python scripts/workspace_import_boundaries.py --check` |

发布前增加：

```bash
python scripts/workspace_doctor.py --strict
python src/research_contracts/smoke_contracts.py --strict
```

## 委托子仓库检查

```bash
python scripts/run_submodule_checks.py --list-profiles
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile full --dry-run
python scripts/run_submodule_checks.py --profile release_typecheck --dry-run
```

委托配置见 [../scripts/submodule_checks.json](../scripts/submodule_checks.json)。

- `smoke` 检查公开入口是否可达
- `full` 先验证 lockfile，再运行各仓库登记的 Ruff、格式、`ty`、维护性门禁和测试
- `market-data-platform` 的 pytest 按文件分批执行
- `strategy-app` 委托给仓库自己的 `scripts/dev/check.py`
- `strategy-pipeline` 委托给仓库自己的 `scripts/dev/run_tests.sh full`
- `release_typecheck` 运行各仓库登记的发布类型检查

`--fail-fast` 会持续执行成功项，并在遇到第一条错误结果后停止。

## 本地 pre-push 门禁

顶层仓库提供共享钩子，并把安装状态写入顶层和八个子仓库各自的本地 Git 配置。先检查计划，再安装并验证：

```bash
python scripts/install_pre_push_hooks.py --dry-run
python scripts/install_pre_push_hooks.py
python scripts/install_pre_push_hooks.py --check
```

共享 pre-push 钩子根据当前推送仓库选择门禁：

- 推送顶层仓库时运行硬质量检查、workspace doctor、严格契约冒烟、策略证据检查、顶层测试和研究层检查，并检查全部子模块指针与工作树
- 推送子仓库时运行 `scripts/submodule_checks.json` 中该仓库的 `full` profile
- `strategy-pipeline` 和 `strategy-app` 会先运行仓库原有 pre-push 钩子，再运行共享完整门禁
- 当前推送仓库必须保持工作树干净，任一检查失败都会阻止推送
- 远端分支允许 `main` 和 `feat/*`、`fix/*`、`hotfix/*`、`chore/*`、`release/*`
- 推送对象必须解析到当前 `HEAD`
- tag 只能指向当前 `HEAD`
- 删除远端 `main`、功能分支和 tag 会被拒绝

共享 dispatcher 会保留并调用仓库 `.githooks` 和默认 Git 钩子目录中已有的可执行钩子。安装器发现其他 `core.hooksPath` 时会拒绝覆盖，并要求先人工处理冲突。没有原生钩子的仓库不会增加 pre-commit 检查。

检查命令计划且不执行任何门禁：

```bash
python scripts/run_pre_push_checks.py --repository "$PWD" --dry-run
```

紧急情况下可以使用 Git 原生的 `git push --no-verify` 绕过钩子。共享门禁没有自定义环境变量绕过方式。工作区移动后需要重新运行安装命令，因为各仓库的 `core.hooksPath` 指向共享钩子的绝对路径。Git linked worktree 会共享这项本地配置，因此不要在独立 worktree 内重复安装或改写 hook。

## GitHub Actions 策略

远端 CI 按仓库可见性管理：

- public 仓库默认启用 GitHub Actions，用于拉取请求的轻量自动检查
- private 仓库默认关闭 GitHub Actions，避免持续占用私有仓库的 Actions 额度
- private 仓库如需启用远端 CI，应记录原因、检查范围和资源成本，并由维护者明确批准
- 本地 `pre-push` 和发布流程负责完整质量门禁

本顶层仓库是 public 仓库，`.github/workflows/contracts.yml` 当前运行无需 private 子模块的公开契约和根仓轻量回归测试。

子模块当前默认状态：

| 子模块 | 可见性 | 远端 CI |
| --- | --- | --- |
| `market-data-platform` | private | 关闭 |
| `deep-learning-tick-data-prediction` | public | 启用 |
| `alpha-research` | private | 关闭 |
| `portfolio-backtester` | public | 启用 |
| `strategy-research` | private | 关闭 |
| `strategy-app` | private | 关闭 |
| `strategy-pipeline` | private | 关闭 |
| `quant-execution-engine` | public | 启用 |

完整分工见 [quality-governance.md](quality-governance.md)。远端 CI 通过只代表公开检查范围通过，不能替代完整工作区门禁。

## 更新文档时

- README 只保留入口级信息
- `docs/README.md` 只做导航
- 当前命令以脚本和配置文件为准
- 阈值、提交编号和阶段证据放在治理文件或 evidence 中
- 历史交接材料放入 `docs/archive/`
- 修改子模块检查配置时同步更新测试
- 修改 CI 状态时同步更新 `AGENTS.md`、质量治理文档和事实测试

## 发布记录

需要可审计的版本组合时，运行：

```bash
python scripts/print_version_matrix.py
```

将实际验证结果写入 [version-matrix.md](version-matrix.md)。不要手工复制当前子模块状态作为长期静态表。
