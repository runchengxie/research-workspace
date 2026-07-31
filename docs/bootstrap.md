# 新机器初始化

本页给出 `research-workspace` 的最短可复现安装路径。子仓库的凭证、可选依赖和业务命令以各自文档为准。

## 环境要求

准备 Git、uv 和 Python 3.12。Python 3.12 是七个仓库当前共同支持的版本。顶层仓库与
`market-data-platform` 最低支持 3.11，四个研究仓库最低支持 3.12，
`quant-execution-engine` 支持 3.10 至 3.12。

```bash
python --version
uv --version
git --version
```

## 克隆与同步

```bash
git clone --recurse-submodules https://github.com/runchengxie/research-workspace.git
cd research-workspace
git submodule status
python scripts/workspace_doctor.py
```

已有本地仓库时运行：

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

普通 zip 或源代码快照没有完整 Git 子模块信息，只适合阅读文档。

## 安装本地 Git 门禁

新 clone 需要显式安装共享钩子。安装器只写入顶层和六个子仓库各自的本地 `core.hooksPath`：

```bash
python scripts/install_pre_push_hooks.py --dry-run
python scripts/install_pre_push_hooks.py
python scripts/install_pre_push_hooks.py --check
```

安装后，推送哪个仓库就运行哪个仓库的完整门禁。推送顶层仓库还会检查全部 Git 子模块指针（gitlink）和子模块工作树。`strategy-pipeline` 原有的 pre-commit 与 pre-push 钩子会继续运行。

安装器会链式保留仓库 `.githooks` 和默认 Git 钩子目录中的可执行钩子。若已有其他 `core.hooksPath`，安装会停止并提示先人工处理冲突。

## 安装子仓库依赖

每个子仓库维护独立环境：

```bash
cd market-data-platform
uv sync --extra dev

cd ../alpha-research
uv sync --extra dev

cd ../portfolio-backtester
uv sync --extra dev

cd ../research-apps
uv sync --extra dev

cd ../strategy-pipeline
uv sync --extra dev

cd ../quant-execution-engine
uv sync --group dev --extra cli

cd ..
```

需要 RQData、TuShare、DuckDB 或券商软件开发工具包（SDK）时，在对应子仓库安装相应可选依赖。

## 配置数据根目录

共享数据产物放在仓库外：

```bash
export DATA_PLATFORM_ROOT=/path/to/research-artifacts
```

常见目录：

```text
$DATA_PLATFORM_ROOT/
  assets/
  metadata/
    current_assets/
      a_share_current.json
    dataset_registry.csv
  reports/
  standardized/
```

顶层 `.env` 只保存 `DATA_PLATFORM_ROOT` 一类路径配置。数据服务商令牌、券商凭证和密码按子仓库规则保存。

## 顶层检查

```bash
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
uv run --project strategy-pipeline --extra dev \
  --with 'matplotlib>=3.8' --with 'tabulate>=0.9' \
  python -m pytest tests -q
python scripts/run_quality_checks.py --profile hard
```

发布前增加严格检查：

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

配置见 [../scripts/submodule_checks.json](../scripts/submodule_checks.json)。

`full` 先验证 lockfile，再运行各仓库当前登记的质量检查。`market-data-platform` 会分批
启动 pytest 进程，避免完整测试在单个进程中持续累积内存。`research-apps` 使用自己的
`scripts/dev/check.py` 权威门禁。`release_typecheck` 运行各仓库登记的发布类型检查。

## 自动化状态

当前顶层和六个子模块的 GitHub Actions 仓库权限均禁用。顶层
`.github/workflows/superproject.yml.disabled`、`research-apps` 的 CI 文件和 Strategy
兼容检查都只保存停用模板。`portfolio-backtester` 虽保留 `ci.yml`，权限关闭时也不会
触发远端检查。新机器验收应以本地 pre-push 和本页命令的实际输出为准。
