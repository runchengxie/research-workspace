# Research Workspace（量化研发工作区）

这个仓库用来固定一组可以一起工作的量化研发项目版本。它帮助你在同一套工作区里完成市场数据准备、策略研究、目标持仓导出，以及可选的交易执行验证。

第一次使用时，建议先完成“快速开始”，再根据任务进入对应子项目。

## 适合做什么

- 初始化一套包含数据、研究和执行交接工具的工作区。
- 复现一组已经验证过的子项目版本。
- 查清市场数据、策略研究、目标持仓导出和执行验证之间的顺序。
- 找到每个子项目的 README、命令和检查入口。

## 主要模块

| 模块 | 用途 | 常用入口 |
| --- | --- | --- |
| [`market-data-platform`](market-data-platform/) | 统一市场数据入口，维护共享数据目录、当前可用数据清单、资产索引和港股十档盘口快照数据。 | `marketdata ...`、`rqdata-hk-depth ...` |
| [`rqdata-hk-depth-snapshots`](rqdata-hk-depth-snapshots/) | 港股十档盘口快照兼容仓；核心实现已迁入 `market-data-platform`。 | `marketdata rqdata hk-depth -- ...` |
| [`cross-sectional-trees`](cross-sectional-trees/) | 运行策略研究、特征工程、模型评估、回测、持仓快照和目标持仓导出。 | `cstree ...` |
| [`quant-execution-engine`](quant-execution-engine/) | 可选的交易执行系统，读取目标持仓文件后做预演、模拟盘或实盘执行。 | `qexec ...` |

## 基本流程

```text
准备并发布市场数据
  -> 策略研究、模型评估和回测
  -> 导出目标持仓文件 targets.json
  -> 可选：交给执行引擎做预演、模拟盘验证或实盘操作
```

执行引擎已经作为固定版本放入工作区，用于复现研究系统到执行系统的文件交接。券商连接、模拟盘和实盘操作仍由 `quant-execution-engine` 自己的检查和安全开关控制。

更完整的执行顺序和边界说明见 [平台工作流与集成边界](docs/platform-workflow.md)。

## 快速开始

克隆仓库并拉取全部子模块：

```bash
git clone --recurse-submodules https://github.com/runchengxie/research-workspace.git
cd research-workspace
```

如果已经克隆过顶层仓库，运行：

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

检查工作区状态：

```bash
python scripts/workspace_doctor.py
python scripts/smoke_contracts.py
```

如果需要从顶层委托各子项目运行自己的检查，可以使用：

```bash
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile full --dry-run
```

`run_submodule_checks.py` 只按 manifest 进入各子项目执行命令，不读取或解释子项目内部源码结构。

子项目依赖、凭证和数据根目录配置见 [新机器初始化](docs/bootstrap.md)。

## 常见任务入口

| 任务 | 从这里开始 |
| --- | --- |
| 新机器初始化 | [docs/bootstrap.md](docs/bootstrap.md) |
| 查看数据、研究和执行之间的顺序 | [docs/platform-workflow.md](docs/platform-workflow.md) |
| 查看跨模块文件约定 | [docs/contracts.md](docs/contracts.md) |
| 查看当前锁定了哪些子项目版本 | [docs/version-matrix.md](docs/version-matrix.md) |
| 更新子模块版本前做检查 | [docs/release-checklist.md](docs/release-checklist.md) |
| 市场数据平台说明 | [market-data-platform/README.md](market-data-platform/README.md) |
| 策略研究说明 | [cross-sectional-trees/README.md](cross-sectional-trees/README.md) |
| 港股盘口快照说明 | [rqdata-hk-depth-snapshots/README.md](rqdata-hk-depth-snapshots/README.md) |
| 交易执行引擎说明 | [quant-execution-engine/README.md](quant-execution-engine/README.md) |

## 版本锁定方式

本仓库通过 Git submodule 固定四个子项目的提交版本。子项目仍在各自目录里独立开发、测试和发布；顶层仓库记录的是“这几个提交可以一起使用”的组合。

日常开发通常在子项目目录中完成：

```bash
cd cross-sectional-trees
git status
git add <files>
git commit -m "..."
git push
```

确认子项目版本后，再回到顶层仓库提交新的子模块指针：

```bash
cd ..
git status
git add cross-sectional-trees
git commit -m "Bump cross-sectional-trees"
git push
```

发布或更新版本组合前，请使用 [发布检查清单](docs/release-checklist.md)。

## 常见术语

| 术语 | 在本仓库中的意思 |
| --- | --- |
| submodule | Git 子模块；顶层仓库用它锁定各子项目的具体提交。 |
| contract | 文件约定；下游按这个约定读取上游输出。 |
| registry | 已发布数据资产索引，主要用于查找和审计。 |
| `targets.json` | 研究系统导出的目标持仓文件，执行引擎按它生成调仓计划。 |
| paper / live | 模拟盘 / 实盘。实盘必须通过执行引擎自己的安全门禁。 |
| lineage | 记录一个输出来自哪些输入、配置和运行过程的审计信息。 |
