# 新机器初始化

本页说明如何在新机器上拉起 `research-workspace`，并检查活跃子项目是否处在顶层仓库记录的版本。各子项目的完整依赖、凭证和业务命令仍以各自 README 和 docs 为准。

## 克隆仓库

```bash
git clone --recurse-submodules https://github.com/runchengxie/research-workspace.git
cd research-workspace
```

如果已经克隆了顶层仓库：

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

普通 zip 或 source snapshot 没有 Git 子模块提交信息，也通常没有子模块内容；它适合阅读顶层文档，
不能作为完整测试、版本矩阵或文档链接检查的运行目录。

确认子模块指针和本地状态：

```bash
git submodule status
python scripts/workspace_doctor.py
```

发布前或更新子模块指针前建议使用严格模式：

```bash
python scripts/workspace_doctor.py --strict
```

## 安装依赖

推荐在每个子项目目录中独立安装依赖。顶层仓库只做工作区检查，不提供共享 Python 包或共享虚拟环境。`alpha-research` 和 `portfolio-backtester` 当前仍依赖同一个 workspace 下的 `cstree` namespace 组合运行；完整研究命令仍从 `cross-sectional-trees` 的 `cstree` CLI 进入。

```bash
cd market-data-platform
uv sync --extra dev

cd ../alpha-research
uv sync --extra dev

cd ../portfolio-backtester
uv sync --extra dev

cd ../cross-sectional-trees
uv sync --extra dev --extra rqdata

cd ../quant-execution-engine
uv sync --group dev --extra cli

cd ..
```

中国香港市场 provider 生产面已从活跃 `market-data-platform` 主线归档。日常运行不再使用
`marketdata rqdata hk-*` 或旧 `rqdata-hk-*` 命令；需要历史复现时，先通过
`marketdata migration hydrate-hk` 从 restore-only archive 恢复。工作区已停止追踪
`rqdata-hk-depth-snapshots` 子模块，也不承诺 `rqdata_tick_data.*` 旧 Python import 路径。

如果只需要只读文档和顶层检查脚本，顶层不需要额外安装依赖；`scripts/` 和 `tests/` 只使用 Python 标准库。

## 环境变量

共享数据根目录应放在仓库外部，并通过环境变量传给各模块：

```bash
export DATA_PLATFORM_ROOT=/path/to/research-artifacts
```

也可以复制顶层示例文件，给本机 `workspace_doctor.py` 和跨仓库检查提供默认路径：

```bash
cp .env.example .env
```

顶层 `.env` 只允许记录 `DATA_PLATFORM_ROOT` 这类工作区路径配置；provider token、券商凭证、
密码和其他 secret 仍必须放在对应子项目约定的私有位置，不能放进顶层 `.env`。

常见共享路径：

```text
$DATA_PLATFORM_ROOT/
  assets/
  metadata/
    current_assets/
      a_share_current.json
    frozen_markets/
      hk.json
    dataset_registry.csv
  reports/
```

`metadata/frozen_markets/hk.json` 表示港股资产已经整体移入独立冷存储。需要港股历史复现或明确跟踪时，先用 `marketdata migration hydrate-hk` 恢复。

不要把以下内容提交到顶层 Git：

- `.env`、`.env.*`、`.envrc`、本地凭证文件；`.env.example` 是唯一可提交的示例文件。
- `artifacts/`、`outputs/`、`data/`、`cache/` 等大型产物或缓存。
- 券商实盘凭证。实盘凭证应遵循 `quant-execution-engine` 自身文档，放在用户私有位置。

## 轻量检查

顶层只提供轻量检查。子项目测试仍在对应子项目中运行：

```bash
python scripts/workspace_doctor.py
python scripts/smoke_contracts.py
uv run --with pytest python -m pytest tests -q
```

`smoke_contracts.py` 只运行无写入、无真实下单的命令行和文件约定检查。任何需要凭证、网络、下载数据或提交订单的流程，都必须在对应子项目内显式执行。顶层测试包含 pytest 风格函数和 fixture，完整测试入口使用 `pytest`。

## 子项目委托检查

如果已经按上文安装了各子项目依赖，可以从顶层统一委托子项目自己的检查：

```bash
python scripts/run_submodule_checks.py --list-profiles
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile lint --submodule cross-sectional-trees
python scripts/run_submodule_checks.py --profile full --dry-run
```

配置文件是 [scripts/submodule_checks.json](../scripts/submodule_checks.json)。顶层脚本只进入对应子项目目录并运行清单中声明的命令；`ruff`、`pytest`、`basedpyright`、`pyright`、`mypy` 等规则仍由各子项目自己的 `pyproject.toml` 和依赖环境决定。
`lint` profile 还会委托子仓库已有的边界和维护债检查，例如数据平台质量治理与策略编排 maintainability ratchet。
