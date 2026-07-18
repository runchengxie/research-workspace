# 工作区维护

本页说明顶层仓库的日常维护、子模块更新和验证要求。

## 顶层负责什么

适合放在顶层的内容：

- 跨仓库文件约定和发布治理
- 子模块 gitlink
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

再回到顶层更新 gitlink：

```bash
cd ..
git status
git add alpha-research
git commit -m "chore: update alpha-research"
git push
```

一次更新多个子仓库时，应先分别验证，再统一更新顶层 gitlink 和 [version-matrix.md](version-matrix.md)。

## 顶层验证

| 目标 | 命令 |
| --- | --- |
| 工作区状态 | `python scripts/workspace_doctor.py` |
| 契约冒烟 | `python src/research_contracts/smoke_contracts.py` |
| 顶层测试 | `uv run --project strategy-pipeline --extra dev --with 'matplotlib>=3.8' --with 'tabulate>=0.9' python -m pytest tests -q` |
| 硬质量门禁 | `python scripts/run_quality_checks.py --profile hard` |
| BasedPyright 诊断 | `python scripts/run_quality_checks.py --profile basedpyright` |
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
- `full` 先验证 lockfile，再运行各仓库登记的 Ruff、格式、`ty`、维护性门禁和测试。
  `market-data-platform` 的 pytest 按文件分批执行，`research-apps` 委托给仓库自己的
  `scripts/dev/check.py` 权威门禁
- `release_typecheck` 运行 BasedPyright 诊断

## 本地 pre-push 门禁

顶层仓库提供共享 hook，并把安装状态写入顶层和六个子仓库各自的本地 Git 配置。先检查计划，再安装并验证：

```bash
python scripts/install_pre_push_hooks.py --dry-run
python scripts/install_pre_push_hooks.py
python scripts/install_pre_push_hooks.py --check
```

共享 pre-push hook 根据当前推送仓库选择门禁：

- 推送顶层仓库时运行硬质量检查、workspace doctor、严格契约冒烟和顶层测试，并检查全部 gitlink 与子模块工作树
- 推送子仓库时只运行 `scripts/submodule_checks.json` 中该仓库的 `full` profile
- `strategy-pipeline` 和 `research-apps` 先运行仓库原有 pre-push hook，成功后再运行共享完整门禁
- 当前推送仓库必须保持工作树干净，任一检查失败都会阻止推送
- 远端分支只允许创建或更新 `main`，且推送对象必须解析到当前 `HEAD`
- tag 仅在解析到当前 `HEAD` 时放行，删除远端 `main`、删除 tag 和其他 ref 会被阻止

共享 dispatcher 会保留并调用仓库 `.githooks` 和默认 Git hooks 目录中已有的可执行 hook。安装器发现其他 `core.hooksPath` 时会拒绝覆盖，并要求先人工处理冲突。没有原生 hook 的仓库不会增加 pre-commit 检查。

检查命令计划且不执行任何门禁：

```bash
python scripts/run_pre_push_checks.py --repository "$PWD" --dry-run
```

紧急情况下可以使用 Git 原生的 `git push --no-verify` 绕过 hook。共享门禁没有自定义环境变量绕过方式。工作区移动后需要重新运行安装命令，因为各仓库的 `core.hooksPath` 指向共享 hook 的绝对路径。Git linked worktree 会共享这项本地配置。并行开发应使用独立 clone，避免另一个 worktree 改写同一 hooksPath。

## GitHub Actions 状态

当前没有启用顶层 GitHub Actions workflow。顶层只保留
`.github/workflows/superproject.yml.disabled` 作为停用模板。顶层和六个
子仓库的 GitHub Actions 权限均禁用。`portfolio-backtester` 保留 `ci.yml` 定义，
`research-apps` 与 Strategy 只保留停用模板，但这些文件当前都不会触发远端检查。
权威检查在本地 pre-push 执行，文档和 PR 不应把本地质量命令描述成已经由远端 CI 自动
执行。恢复自动化时，需要显式开启对应仓库权限，并同步更新本页、质量治理文档和测试。

## 更新文档时

- README 只保留入口级信息
- `docs/README.md` 只做导航
- 当前命令以脚本和配置文件为准
- 阈值、提交编号和阶段证据放在治理文件或 evidence 中
- 历史交接材料放入 `docs/archive/`
- 修改子模块检查配置时同步更新测试

## 发布记录

需要可审计的版本组合时，运行：

```bash
python scripts/print_version_matrix.py
```

将实际验证结果写入 [version-matrix.md](version-matrix.md)。不要手工复制当前子模块状态作为长期静态表。
