# 量化研发平台

这个仓库是量化研发平台，负责把数据平台、alpha 研究、组合回测、策略编排和交易执行固定在一组可以一起工作的版本上，并说明它们之间怎样交接。

如果你是第一次接触这个项目，可以把这里理解成一张入口地图：

```text
market-data-platform
  生产并发布数据资产
        |
        v
alpha-research
  因子、模型、稳健性和信号产物
        |
        v
portfolio-backtester
  组合构造、回测、容量和报告
        |
        v
cross-sectional-trees
  研究编排、CLI 兼容层和目标持仓导出
        |
        v
quant-execution-engine
  读取 targets.json，做预演、模拟盘或受控实盘执行
```

当前活跃方向是 A 股数据、研究和执行交接。中国香港市场真实资产和研究输出按冷存储 /
恢复流程保留。公开展示使用工作区外、暂停维护状态的合成演示仓库：
`https://github.com/runchengxie/hk-cross-sectional-strategy-demo`。该演示仓库独立于本工作区，
不进入顶层 CI、发布矩阵或日常工作流。

## 先知道什么

- 顶层仓库只做集成、文档、轻量检查和子模块版本锁定。
- 大型市场数据、研究输出、provider 缓存、交易审计日志不要放在顶层仓库。
- 数据资产的正式入口是共享数据根目录下的 `metadata/current_assets/*.json` 和 `metadata/dataset_registry.csv`。
- 研究到执行的正式交接文件是 `targets.json`，由 `cross-sectional-trees` 编排导出，由 `quant-execution-engine` 读取。
- 模拟盘和实盘能力由执行引擎自己的安全门禁控制；顶层脚本不会直接触发真实券商交易。

## 第一次启动

克隆仓库并拉取子模块：

```bash
git clone --recurse-submodules https://github.com/runchengxie/research-workspace.git
cd research-workspace
```

如果你已经克隆了顶层仓库：

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

先跑顶层健康检查：

```bash
python scripts/workspace_doctor.py
python scripts/smoke_contracts.py
```

更完整的新机器配置，包括子项目依赖、`DATA_PLATFORM_ROOT` 和委托检查，见 [新机器初始化](docs/bootstrap.md)。

## 你现在要做什么

| 目标 | 建议入口 |
| --- | --- |
| 先把工作区跑起来 | [docs/bootstrap.md](docs/bootstrap.md) |
| 了解数据、研究、执行怎样衔接 | [docs/platform-workflow.md](docs/platform-workflow.md) |
| 推进 A 股主线或恢复港股归档 | [docs/data-transition-playbook.md](docs/data-transition-playbook.md) |
| 查看中国香港市场归档状态 | [docs/archive/hk/README.md](docs/archive/hk/README.md) |
| 查看港股公开拆分清单 | [docs/hk-public-split-manifest.yml](docs/hk-public-split-manifest.yml) |
| 查跨仓库文件约定和边界 | [docs/contracts.md](docs/contracts.md) |
| 查看维护债治理入口 | [docs/maintainability-governance.md](docs/maintainability-governance.md) |
| 查看文档生命周期和归档规则 | [docs/documentation-lifecycle.md](docs/documentation-lifecycle.md) |
| 查看废弃入口删除条件 | [docs/deprecations.md](docs/deprecations.md) |
| 看当前锁定的子模块组合 | [docs/version-matrix.md](docs/version-matrix.md) |
| 更新子模块指针或发布一组组合 | [docs/workspace-maintenance.md](docs/workspace-maintenance.md)、[docs/release-checklist.md](docs/release-checklist.md) |
| 找全部顶层文档入口 | [docs/README.md](docs/README.md) |

## 活跃子项目

| 子项目 | 负责什么 | 从哪里读 |
| --- | --- | --- |
| [market-data-platform](market-data-platform/) | 维护共享数据目录、当前数据清单、资产索引、中国香港市场 RQData 资产、港股十档盘口快照数据，以及 A 股数据入口。 | [market-data-platform/README.md](market-data-platform/README.md) |
| [alpha-research](alpha-research/) | 承载 `cstree.alpha.*`：特征、模型、CPCV/PBO、feature evidence、signal artifact 和 alpha 诊断。 | [alpha-research/README.md](alpha-research/README.md) |
| [portfolio-backtester](portfolio-backtester/) | 承载 `cstree.backtesting.*`：组合构造、回测、执行模拟、容量、暴露、turnover 和报告。 | [portfolio-backtester/README.md](portfolio-backtester/README.md) |
| [cross-sectional-trees](cross-sectional-trees/) | 只读消费已发布数据资产，保留研究编排、CLI、兼容 facade、持仓快照和 `targets.json` 导出。 | [cross-sectional-trees/README.md](cross-sectional-trees/README.md) |
| [quant-execution-engine](quant-execution-engine/) | 读取标准 `targets.json`，负责解析、dry-run、风控、模拟盘、实盘门禁和执行审计。 | [quant-execution-engine/README.md](quant-execution-engine/README.md) |

港股公开演示仓库独立于这些活跃子项目，仅用于作品集展示。真实港股历史复现以
[中国香港市场归档](docs/archive/hk/README.md)、冷存储发布包、清单、恢复演练
和对应子仓库兼容入口为准；迁出或删除候选面由
[港股公开拆分清单](docs/hk-public-split-manifest.yml) 记录。旧的兼容面和公开演示说明页仍作为兼容入口保留；默认阅读路径从 [docs/README.md](docs/README.md) 开始。

## 常用顶层命令

```bash
python scripts/workspace_doctor.py
python scripts/smoke_contracts.py
python scripts/a_share_readiness.py --artifacts-root "$DATA_PLATFORM_ROOT" --pretty
python scripts/print_version_matrix.py
uv run --with pytest python -m pytest tests -q
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile full --dry-run
python scripts/run_submodule_checks.py --profile release_typecheck --dry-run
python scripts/run_quality_checks.py --profile hard
```

`run_submodule_checks.py` 只按清单进入子项目运行它们自己的命令，不读取或解释子项目内部源码结构。`full` 默认使用 Ruff、ty 和 pytest；`release_typecheck` 才运行 BasedPyright / Pyright。更详细的维护方式见 [工作区维护](docs/workspace-maintenance.md)。

`a_share_readiness.py` 只读检查 A 股迁移证据，不会下载数据、训练模型或连接券商。完整 baseline 验收时通过 `--evidence-manifest <json>` 提供研究输出、目标文件 lineage 和执行 dry-run 报告。

## 协作边界

日常开发通常在对应子项目中完成；跨仓库文件约定、子模块指针、顶层 doctor、发布检查清单或工作区说明需要变化时，再修改顶层仓库。

团队级协作入口见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [ARCHITECTURE.md](ARCHITECTURE.md)。
新增废弃兼容面、一次性脚本、质量检查排除项、`targets.json` 文件约定影响，或新增 provider / broker 凭证读取时，先更新对应治理文档。

修改文档时请保持市场称谓清晰：优先使用中国香港市场、港股、港股通、中国大陆市场、A 股等业务表述。当前 A 股权威 current contract 文件名是：

```text
metadata/current_assets/a_share_current.json
```

旧称 `cn_current.json` 只作为历史兼容或 alias 说明，不作为新文档里的权威入口。
