# 量化研发工作区

`research-workspace` 用 Git 子模块锁定一组协同工作的量化研发仓库，维护跨仓库契约、
版本组合、发布流程和轻量检查。大型数据、研究运行产物和交易审计记录位于仓库外的
数据目录，当前数据入口见 `~/data/README.md`。

## 工作区组成

| 目录 | 职责 |
| --- | --- |
| `market-data-platform/` | 采集、检查、发布和读取市场数据 |
| `deep-learning-tick-data-prediction/` | L2 事件流清洁审计、模型训练和预测产物 |
| `alpha-research/` | 特征、模型、稳健性诊断和信号产物 |
| `portfolio-backtester/` | 组合构造、回测、成本、换手、容量和风险分析 |
| `strategy-app/` | 策略专用计算、冻结合同和研究应用 |
| `strategy-pipeline/` | 研究编排、运行目录、结果汇总和 `targets.json` 导出 |
| `strategy-research/` | 策略身份、投资假设、生命周期、实验和证据导航 |
| `quant-execution-engine/` | 目标解析、预演、风控、券商执行和审计 |
| `src/research_contracts/` | 顶层维护的跨仓库产物契约校验 |

职责边界见 [架构说明](ARCHITECTURE.md)。子模块的内部实现、依赖、参数和完整命令以
各自仓库的 README、`AGENTS.md` 和 `docs/` 为准。

## 数据与产物边界

- 大型市场数据、研究产物、缓存、运行凭证和交易审计日志放在 `~/data` 或专用生产目录。
- A 股权威当前契约是 `metadata/current_assets/a_share_current.json`。
- 研究到执行的交接文件是 `targets.json`。
- 策略生命周期以 `strategy-research/catalog.json` 为准，代码位置不表达生产状态。
- 生产代码使用 `/home/richard/code/production/` 下的版本化目录，开发和实验使用独立 worktree。
- 凭证只放在对应子仓库规定的私有位置，不进入仓库和共享数据说明。

## 快速开始

首次获取完整工作区：

```bash
git clone --recurse-submodules https://github.com/runchengxie/research-workspace.git
cd research-workspace
git submodule sync --recursive
git submodule update --init --recursive
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
```

新机器的完整安装步骤见 [初始化工作区](docs/bootstrap.md)。各项目的开发依赖、测试和
命令以子项目文档为准。

## 常用检查

```bash
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
python scripts/run_quality_checks.py --profile hard
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_pre_push_checks.py --repository "$PWD" --dry-run
```

本地 `pre-push` 是完整质量门禁。远端 CI 按仓库可见性管理：public 仓库默认启用 GitHub Actions，private 仓库默认关闭。private 仓库如需启用远端 CI，应在对应仓库说明原因、检查范围和资源成本。

已合并的临时分支可以使用显式清理命令。命令会先通过 `gh` 确认对应 PR 已合并，
只有同时提供 `--yes` 才会执行远程删除，`main`、tag 和未合并分支不会被删除：

```bash
python scripts/cleanup_merged_branches.py \
  --repo runchengxie/research-workspace \
  --branch fix/example \
  --dry-run
python scripts/cleanup_merged_branches.py \
  --repo runchengxie/research-workspace \
  --branch fix/example \
  --yes
```

本顶层仓库是 public 仓库，`.github/workflows/contracts.yml` 会在相关拉取请求、手动触发和每周计划任务中运行无需私有子模块的公开检查。完整跨仓检查仍由本地 `pre-push` 和发布流程负责。各子模块的当前自动化状态见 [质量治理](docs/quality-governance.md)。

根项目的集成测试使用工作区测试 runner。它会初始化检查源码树，并按工作区边界准备
`PYTHONPATH`，不要直接用 `strategy-pipeline` 环境收集顶层测试：

```bash
python scripts/run_workspace_tests.py
```

## 命令行入口

| 命令 | 所属项目 | 用途 |
| --- | --- | --- |
| `strategy` | `strategy-pipeline` | 编排研究流程并导出目标文件 |
| `strategy-pipeline` | `strategy-pipeline` | `strategy` 的完整命令名 |
| `qexec` | `quant-execution-engine` | 预演、风控和受控交易 |
| `stockq` | `quant-execution-engine` | `qexec` 的兼容命令名 |
| `marketdata` | `market-data-platform` | 市场数据采集、检查、发布和读取 |

各命令使用 `uv run --project <项目>` 调用。策略知识、计算内核、编排和执行之间的边界
由 [ADR-0006](docs/adr/0006-strategy-knowledge-and-runtime-boundaries.md) 维护。

## 发布与生产目录

生产发布使用 `scripts/promote-production.sh`。脚本在成功切换 `current` 后清理旧版本，
默认保留最近 5 个版本，并始终保留当前版本和至少一个回滚版本。

查看清理计划：

```bash
bash scripts/promote-production.sh --repo all --dry-run
```

完整发布流程见 [生产更新](docs/production-update.md) 和 [发布检查清单](docs/release-checklist.md)。

## 文档入口

- [文档总入口](docs/README.md)
- [架构边界](ARCHITECTURE.md)
- [新机器初始化](docs/bootstrap.md)
- [平台工作流](docs/platform-workflow.md)
- [跨仓库文件契约](docs/contracts.md)
- [质量治理](docs/quality-governance.md)
- [工作区维护](docs/workspace-maintenance.md)
- [版本矩阵](docs/version-matrix.md)
- [生产更新](docs/production-update.md)
- [术语表](docs/glossary.md)

### 文档写作

当前文档以中文为主，正文使用中文标点和直接表达。命令、路径、配置键、包名、API 名称
和数据字段保留原文。文档分工和写作约定见 [文档写作与维护](docs/documentation-style.md)。
