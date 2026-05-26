# Research Workspace（量化研发工作区）

这是一个面向量化研发流程的可复现工作区，覆盖市场数据资产管理、盘口数据加工、策略研究与回测，以及执行前的持仓和分配结果输出。

当前仓库正式纳入的是数据、研究与目标持仓导出链路。连接券商的交易执行系统作为可选下游存在；在 paper / dry-run 联调与运维门禁验证完成前，不将其锁定为本工作区的必选组成部分。

## 平台能力

```text
市场数据 / 基本面                    港股盘口快照
       |                                  |
       v                                  v
market-data-platform  <------  rqdata-hk-depth-snapshots
数据控制面、发布契约              下载、检查、聚合、交付
       |
       v
已发布资产 / current contract
       |
       v
cross-sectional-trees
特征、模型、回测、研究治理、持仓分配
       |
       | canonical targets.json + lineage
       v
quant-execution-engine（可选下游，未纳入 submodule）
券商下单、订单跟踪、对账、异常恢复
```

## 当前组成

| 项目 | 当前职责 | 主要交付 |
| --- | --- | --- |
| [`market-data-platform`](market-data-platform/) | HK / CN 市场数据控制面，定义共享路径、current contract、dataset registry 和健康检查 / 发布规范 | 版本化数据契约与资产索引 |
| [`rqdata-hk-depth-snapshots`](rqdata-hk-depth-snapshots/) | RQData 港股十档盘口快照下载、质量检查、日频聚合、对账和交付打包 | `tick_depth_raw`、`tick_depth_daily` 及未来成本模型输入 |
| [`cross-sectional-trees`](cross-sectional-trees/) | 截面策略研究、特征工程、模型评估、历史回测、候选治理、持仓与执行前分配分析，以及显式执行目标导出 | `summary.json`、`positions_current*.csv`、snapshot / alloc 输出、canonical `targets.json` |
| [`quant-execution-engine`](https://github.com/runchengxie/quant-execution-engine) | 可选的券商连接执行系统，读取目标持仓后执行下单、追踪、对账和异常恢复 | 执行审计、订单状态和复查证据 |

`quant-execution-engine` 目前只作为平台链路的可选下游列出，不是本仓库的 submodule。`cross-sectional-trees` 已提供 `cstree export-targets`，用于将已保存的 long-only live 持仓导出为执行引擎的 canonical `targets.json`，并另写 lineage sidecar；券商侧的 paper / live 操作仍由执行系统独立门禁控制。

## 典型路径

1. 使用数据平台或现有数据维护工具发布版本化的日线、PIT、估值和盘口派生资产。
2. 由 `cross-sectional-trees` 读取已发布资产，开展特征研究、模型评估、回测和候选策略治理。
3. 生成持仓快照与执行前分配结果，并显式运行 `cstree export-targets` 生成可审计的执行交接文件。
4. 如需连接真实或模拟券商，将该目标文件交给可选执行引擎的预演 / paper 流程，并保留其独立门禁。

模块执行顺序、数据契约边界、执行引擎纳入条件和未来调度原则见 [平台工作流与集成边界](docs/platform-workflow.md)。

## 仓库组织方式

本仓库是一个 Git superproject，用来锁定相关项目的一组可复现版本。它不是 monorepo：各模块的代码、依赖、测试和发布仍由各自仓库维护；大型数据、缓存和运行产物也不提交到顶层 Git 仓库。

这种组织方式用于复现一套经过确认的数据与研究环境，而不是让顶层仓库直接拥有各模块的业务实现。

## 克隆工作区

子模块 URL 使用 HTTPS，便于在没有 GitHub SSH key、但具备相应仓库访问权限的环境中初始化全部模块：

```bash
git clone --recurse-submodules https://github.com/runchengxie/research-workspace.git
```

如果已经克隆了顶层仓库，再初始化或同步子模块：

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

## 开发与版本锁定

子项目仍在各自目录中独立开发、提交和推送：

```bash
cd cross-sectional-trees
git status
git add <files>
git commit -m "..."
git push
```

子项目版本确认后，回到顶层仓库提交新的 submodule 指针：

```bash
cd ..
git status
git add cross-sectional-trees
git commit -m "Bump cross-sectional-trees"
git push
```

拉取顶层仓库后，可让本地子模块切换到顶层记录的已确认版本：

```bash
git pull
git submodule update --init --recursive
```

## 边界约定

- 顶层仓库只追踪平台说明、少量 workspace 配置和 submodule 指针，不递归提交子项目文件。
- 可复用数据通过数据契约、manifest 和发布资产交接，不通过引用其他项目工作目录交接。
- `cross-sectional-trees` 当前负责研究、持仓 / 分配输出和显式 `targets.json` 交接文件生成；券商侧执行必须经执行系统自身的安全门禁。
- 在 paper / dry-run 联调和执行运维验证稳定之前，不在顶层加入自动触发真实交易的中央调度逻辑。
