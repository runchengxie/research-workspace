# 量化研发工作区

`research-workspace` 用 Git 子模块锁定一组可以协同工作的量化研发仓库，并维护跨仓库文件约定、版本组合和轻量校验。

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
strategy-app
  执行策略特有的纯计算与研究应用
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
| `strategy-app/` | 组合数据、alpha 和回测的 owner 应用程序接口（API），运行 `DailyWatch20` 和热点板块选股两个应用族（各实验方向见 strategy-app 仓库的[研究应用目录](strategy-app/docs/application-catalog.md)） |
| `strategy-pipeline/` | 研究编排、命令行（CLI）、运行目录、持仓快照和目标文件导出 |
| `quant-execution-engine/` | `targets.json` 解析、预演、风控、券商执行和审计 |
| `src/research_contracts/` | 顶层直接维护的跨仓库产物契约校验薄包 |
| `alpha-research/src/alpha_research/style_factors/` | 风格因子计算内核（`alpha_research.style_factors`），ADR-0006 后由 alpha-research owner |
| `portfolio-backtester/src/portfolio_backtester/style_factors_backtest.py` | 分位数多空回测内核（`portfolio_backtester.style_factors_backtest`），由 portfolio-backtester owner |
| `strategy-research/style_factors/` | 表现层：风格因子归因、报告、图表、稳健性与发布校验（`python -m style_factors`），由 strategy-research 维护 |
| `strategy-research/pre_production/` | 长期跟踪型策略（已验证、值得跟踪、未完全生产化），目录与升格门槛见 [strategy-research/pre_production/README.md](strategy-research/pre_production/README.md) |
| `strategy-research/experiments/` | 一次性探索脚本与结论记录，目录与规则见 [strategy-research/experiments/README.md](strategy-research/experiments/README.md) |
| `strategy-research/packaging/` | 系统级复现打包器脚本（D11-H5），产物不进入仓库 |

策略身份、投资假设、生命周期和证据导航以 [strategy-research/README.md](strategy-research/README.md) 与 [strategy-research/catalog.json](strategy-research/catalog.json) 为准。代码放在哪个仓库不再用来表达策略是否处于生产状态。

仓库结构说明：上表中 `market-data-platform/`、`alpha-research/`、`portfolio-backtester/`、`strategy-app/`、`strategy-pipeline/`、`quant-execution-engine/` 六个目录是 git submodule，其版本由 `.gitmodules` 与各子仓库的 gitlink 锁定。`strategy-research/` 不是 submodule，而是本 superproject 内的普通顶层目录，其所有文件由本仓库直接版本化（不通过 gitlink 锁定子仓库 commit）。因此 `strategy-research` 的改动随本仓库主线提交，不存在跨仓库版本漂移风险；若未来需要把它独立成仓库，应先抽取历史再 `git submodule add`，当前按"顶层目录"治理即可。详见边界清单 SA-14。

四个研究侧 Python 包使用各自的权威命名空间：

- `alpha_research`
- `portfolio_backtester`
- `strategy_app`
- `strategy_pipeline`

工作区 2.0 已删除旧共享命名空间、兼容命令和隐式环境变量回退。权威命令是
`strategy` 与 `strategy-pipeline`。具体边界见
[ADR-0002](docs/adr/0002-owner-native-python-namespaces.md)。
策略知识、可执行应用和运行控制面的边界见
[ADR-0006](docs/adr/0006-strategy-knowledge-and-runtime-boundaries.md)。

## 子项目命令行（CLI）

各子项目通过 `uv run --project <子项目>` 调用，已注册的命令如下：

| 命令 | 所属子项目 | 用途 |
|------|------------|------|
| `strategy` | strategy-pipeline | 研究编排：读取数据资产、调用研究与回测、导出 `targets.json` |
| `strategy-pipeline` | strategy-pipeline | 同上（`strategy` 的等价命令名） |
| `qexec` | quant-execution-engine | 券商执行与预演：config、preflight、rebalance、orders |
| `stockq` | quant-execution-engine | 同上（`qexec` 的等价命令名） |
| `marketdata` | market-data-platform | 市场数据资产的采集、检查、发布与读取 |

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

D11-H5 可移植复现包使用以下命令构建，默认写入 `~/Downloads` 目录：

```bash
python scripts/package_d11_h5_repro.py --component all
```

完整包约 3 GB，包含日频数据和冻结研究账本。TuShare 一分钟快照约 14 GB，作为独立可选包。
解压后的使用方法见[复现包说明](strategy-research/packaging/d11_h5/README.md)。
归档旁的 `restore_d11_h5_repro.sh` 会先校验 SHA-256，再恢复核心包。传入
`--component all` 可在同一次恢复中合并分钟数据。

## 本地质量门禁

先查看 pre-push 将运行哪些检查：

```bash
python scripts/run_pre_push_checks.py --repository "$PWD" --dry-run
```

日常检查常用以下三个入口：

```bash
python scripts/run_quality_checks.py --profile hard
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile full --dry-run
```

`full` 先验证 lockfile，再运行各仓库登记的本地权威门禁。本工作区刻意以本地 pre-push 钩子作为唯一质量门禁，不依赖持续集成：顶层与六个子模块的 GitHub Actions 权限均已禁用，所有检查在推送前由本地钩子完成。这是有意为之的设计，不是临时状态，新成员需要自行安装钩子（见下文）才能跑门禁。安装方法、完整命令和自动化状态统一记录在[工作区维护](docs/workspace-maintenance.md)与[质量治理](docs/quality-governance.md)中。

不依赖 Git 钩子的一键本地门禁：`bash scripts/check.sh`（等价于推送顶层仓库前会跑的检查集合）。

## 根测试契约

顶层 `tests/` 是跨仓库集成测试项目，其用例同时验证根工作区与六个子模块。根项目本身
`package = false`，不发布，不构建 wheel。测试环境借用 `strategy-pipeline` 的虚拟环境
运行（含 `alpha_research`、`strategy_pipeline` 与数据、组合、执行各 owner 包），命令为：

```bash
uv run --project strategy-pipeline --extra dev python -m pytest tests -q
```

带覆盖率统计的命令为：

```bash
uv run --project strategy-pipeline --extra dev \
  python -m coverage run -m pytest tests -q
python -m coverage report
```

覆盖率只统计根工作区 `src/`（`research_contracts` 与 `style_factors`），不统计子模块，
不设 `fail_under` 阈值。跨仓库集成测试不要求根项目达成固定覆盖率，质量看护以
`scripts/run_quality_checks.py --profile hard` 与各子模块自带的维护性预算为准。

## 重要边界

- 大型市场数据、研究输出、缓存和交易审计日志放在仓库外。
- 数据资产从 `$DATA_PLATFORM_ROOT/metadata/current_assets/*.json` 和 `dataset_registry.csv` 读取。
- A 股权威 current 契约 是 `metadata/current_assets/a_share_current.json`。
- 研究到执行的交接文件是 `targets.json`。
- 顶层脚本不会绕过执行引擎的模拟盘或实盘安全门禁。
- 凭证只放在对应子仓库规定的私有位置，不进入顶层 `.env`。

## 文档入口

- [工作区路线图](docs/roadmap.md)
- [研究判断治理](docs/research-decision-governance.md)
- [新机器初始化](docs/bootstrap.md)
- [平台工作流](docs/platform-workflow.md)
- [策略研究与生命周期](strategy-research/README.md)
- [架构边界](ARCHITECTURE.md)
- [跨仓库文件约定](docs/contracts.md)
- [工作区维护](docs/workspace-maintenance.md)
- [质量治理](docs/quality-governance.md)
- [外部框架支持矩阵](docs/framework-support-matrix.md)
- [版本矩阵](docs/version-matrix.md)
- [发布检查清单](docs/release-checklist.md)
- [文档总入口](docs/README.md)
- [文档归集与去重清单](docs/documentation-consolidation.md)
- [术语表](docs/glossary.md)
