# 工作区维护

本页说明顶层工作区的日常维护动作：什么时候改顶层，怎样更新子模块版本，以及发布前应该跑哪些检查。

## 什么时候改顶层

适合放在顶层的改动：

- 跨仓库文件约定、工作流、发布检查清单或 doctor 规则。
- 子模块 gitlink，也就是锁定 `market-data-platform`、`alpha-research`、`portfolio-backtester`、`strategy-pipeline`、`quant-execution-engine` 的具体提交。
- 顶层直接追踪的 `src/research_contracts` 薄包，用于校验跨仓库 artifact contract 清单。
- 顶层 `docs/` 中的协作说明和版本组合记录。
- 只依赖公开 CLI 或文档化文件输出的轻量检查脚本。

不适合放在顶层的改动：

- 子项目内部架构、依赖、lint、type check 或业务参数。
- 市场数据本体、研究输出、provider 缓存、交易审计日志。
- 直接导入子模块内部 Python 包的顶层脚本。
- 自动绕过执行引擎门禁的模拟盘或实盘操作。

## 子模块版本锁定

本仓库通过 Git submodule 固定活跃子项目的提交版本。子项目仍在各自目录里独立开发、测试和发布；顶层仓库记录这几个提交可以一起使用的组合。

日常开发通常在子项目目录中完成：

```bash
cd alpha-research
git status
git add <files>
git commit -m "..."
git push
```

确认子项目版本后，再回到顶层仓库提交新的子模块指针：

```bash
cd ..
git status
git add alpha-research
git commit -m "Bump alpha-research"
git push
```

如果一次更新多个子项目，建议先分别完成子项目自己的测试，再回到顶层更新所有相关 gitlink，并在 [version-matrix.md](version-matrix.md) 记录验证结论。

## 顶层健康检查

顶层检查只验证工作区层面的边界：

```bash
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
uv run --with pytest python -m pytest tests -q
python scripts/run_quality_checks.py --profile hard
python scripts/run_quality_checks.py --profile basedpyright
python scripts/workspace_import_boundaries.py --check
uv run --with pytest python -m pytest tests/test_workspace_import_boundaries.py -q
```

发布前或更新子模块指针前建议使用严格模式：

```bash
python scripts/workspace_doctor.py --strict
python src/research_contracts/smoke_contracts.py --strict
python scripts/workspace_import_boundaries.py --check
uv run --with pytest python -m pytest tests/test_workspace_import_boundaries.py -q
```

## 委托子项目检查

如果已经安装了各子项目依赖，可以从顶层统一委托子项目自己的检查：

```bash
python scripts/run_submodule_checks.py --list-profiles
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile full --dry-run
python scripts/run_submodule_checks.py --profile release_typecheck --dry-run
```

配置文件是 [../scripts/submodule_checks.json](../scripts/submodule_checks.json)。顶层脚本只进入对应子项目目录并运行清单中声明的命令；`full` 默认使用 `ruff`、`ty check` 和 `pytest`，`release_typecheck` 统一运行 BasedPyright 建议项，`mypy_advisory` 仍是执行引擎的单独观察项。

执行引擎仓库自己的 `Makefile` 还提供 `make test`、`make typecheck`、`make basedpyright` 和 `make quality`。顶层委托检查以 [../scripts/submodule_checks.json](../scripts/submodule_checks.json) 为准，执行引擎本地维护时再使用 `Makefile`。

检查分为硬门禁、建议项和人工复核三类。GitHub Actions 在拿不到私有子模块 token 时运行顶层 `ci-smoke` 质量档位，只检查根仓库 Ruff、格式、`ty check` 和 secret scan；有 token 或本地完整工作区时继续运行 `hard` 档位。仓库级 ownership、secret scan、依赖审计 baseline 以及执行引擎迁移后的 mypy 建议项见 [quality-governance.md](quality-governance.md)。

## GitHub Actions 清点

| 仓库 | workflow | 阻塞检查 | 非阻塞或专项检查 |
| --- | --- | --- | --- |
| superproject | `.github/workflows/superproject.yml` | 有 `WORKSPACE_SUBMODULE_READ_TOKEN` 时运行 `hard`、完整 pytest、contract smoke；无 token 时运行 `ci-smoke`、smoke pytest 和子项目检查 dry-run。 | BasedPyright 以 `continue-on-error` 运行；CodeQL 和 Dependency Graph 由 GitHub 独立 workflow 运行。 |
| `market-data-platform` | `.github/workflows/ci.yml` | Ruff、Ruff format、`ty check`、pytest coverage、质量债 ratchet、维护性 baseline、兼容层和架构治理。 | BasedPyright、BasedPyright core basic 和 BasedPyright debt 以 `continue-on-error` 运行；`.github/workflows/package.yml` 负责构建和按需发布包。 |
| `alpha-research` | `.github/workflows/tests.yml` | Ruff、Ruff format、`ty check`、维护性 ratchet；配置 `HK_DATA_PLATFORM_READ_TOKEN` 后还会 checkout `market-data-platform` 并运行 pytest。 | BasedPyright 以 `continue-on-error` 运行。 |
| `portfolio-backtester` | `.github/workflows/tests.yml` | Ruff、Ruff format、`ty check`、维护性 ratchet；配置 `HK_DATA_PLATFORM_READ_TOKEN` 后还会 checkout `market-data-platform` 并运行 pytest。 | BasedPyright 以 `continue-on-error` 运行。 |
| `strategy-pipeline` | `.github/workflows/tests.yml` | lint、format、维护性 ratchet、platform contract、fast tests、`ty check`、DuckDB extra smoke、stats extra smoke。 | BasedPyright 通过 `typecheck-release` 作为 `continue-on-error` 步骤运行；`.github/workflows/security-audit.yml` 运行 lockfile 和 `pip-audit`；`.github/workflows/manual-tests.yml` 保留 slow 与 integration 手动测试。 |
| `quant-execution-engine` | `.github/workflows/tests.yml` | Ruff、Ruff format、`ty check`、pytest。 | BasedPyright 以 `continue-on-error` 运行；CodeQL 和 Dependency Graph 由 GitHub 独立 workflow 运行。 |

## 常见术语

| 术语 | 在本工作区中的意思 |
| --- | --- |
| submodule | Git 子模块；顶层仓库用它锁定各子项目的具体提交。 |
| contract | 文件约定；下游按这个约定读取上游输出。 |
| registry | 已发布数据资产索引，主要用于查找和审计。 |
| `targets.json` | 研究系统导出的目标持仓文件，执行引擎按它生成调仓计划。 |
| paper / live | 模拟盘 / 实盘。实盘必须通过执行引擎自己的安全门禁。 |
| lineage | 记录一个输出来自哪些输入、配置和运行过程的审计信息。 |
