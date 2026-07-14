# 量化研发工作区

`research-workspace` 用 Git 子模块锁定一组可以协同工作的量化研发仓库，并维护跨仓库文件约定、版本组合和轻量检查。

```text
market-data-platform
  发布数据资产
        ↓
alpha-research
  生成特征、模型和信号产物
        ↓
portfolio-backtester
  构造组合并完成回测、成本和容量分析
        ↓
strategy-pipeline
  编排研究流程并导出 targets.json
        ↓
quant-execution-engine
  预演、风控、执行和审计
```

当前活跃主线是 A 股数据、研究和执行交接。港股真实资产与历史研究输出进入恢复专用归档。公开合成演示仓库独立维护，不参与本工作区的版本锁定和检查。

## 仓库组成

| 目录 | 职责 |
| --- | --- |
| `market-data-platform/` | 采集、检查、发布和读取市场数据资产 |
| `alpha-research/` | 特征工程、模型训练、稳健性诊断和信号产物 |
| `portfolio-backtester/` | 组合构造、回测、成本、换手、容量、暴露和报告 |
| `strategy-pipeline/` | 研究编排、CLI、运行目录、持仓快照和目标文件导出 |
| `quant-execution-engine/` | `targets.json` 解析、预演、风控、券商执行和审计 |
| `src/research_contracts/` | 顶层直接维护的跨仓库产物契约校验薄包 |

三个研究侧 Python 包已经采用各自的权威命名空间：

- `alpha_research`
- `portfolio_backtester`
- `strategy_pipeline`

历史 `cstree` 兼容入口只由 `strategy-pipeline` 在 1.x 期间提供，计划在工作区 2.0 删除。

## 快速开始

```bash
git clone --recurse-submodules https://github.com/runchengxie/research-workspace.git
cd research-workspace
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
```

已有本地仓库时先同步子模块：

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

新机器的完整安装步骤见 [docs/bootstrap.md](docs/bootstrap.md)。

## 常用检查

顶层测试：

```bash
uv run --project strategy-pipeline --extra dev \
  --with 'matplotlib>=3.8' --with 'tabulate>=0.9' \
  python -m pytest tests -q
```

顶层质量检查：

```bash
python scripts/run_quality_checks.py --profile hard
python scripts/run_quality_checks.py --profile basedpyright
```

委托子仓库执行各自的检查：

```bash
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile full --dry-run
python scripts/run_submodule_checks.py --profile release_typecheck --dry-run
```

`full` 运行各仓库当前的 Ruff、格式、`ty` 和 `pytest` 检查。`release_typecheck` 运行 BasedPyright 诊断。

当前没有启用顶层 GitHub Actions workflow。`.github/workflows/superproject.yml.disabled` 只保存停用模板，本地命令和人工发布检查仍是当前事实来源。

## 重要边界

- 大型市场数据、研究输出、缓存和交易审计日志放在仓库外。
- 数据资产从 `$DATA_PLATFORM_ROOT/metadata/current_assets/*.json` 和 `dataset_registry.csv` 读取。
- A 股权威 current contract 是 `metadata/current_assets/a_share_current.json`。
- 研究到执行的交接文件是 `targets.json`。
- 顶层脚本不会绕过执行引擎的模拟盘或实盘安全门禁。
- 凭证只放在对应子仓库规定的私有位置，不进入顶层 `.env`。

## 文档入口

- [新机器初始化](docs/bootstrap.md)
- [平台工作流](docs/platform-workflow.md)
- [架构边界](ARCHITECTURE.md)
- [跨仓库文件约定](docs/contracts.md)
- [工作区维护](docs/workspace-maintenance.md)
- [质量治理](docs/quality-governance.md)
- [版本矩阵](docs/version-matrix.md)
- [发布检查清单](docs/release-checklist.md)
- [文档总入口](docs/README.md)
