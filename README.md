# Research Workspace（量化研发工作区）

这是一个面向量化研发流程的可复现工作区，覆盖市场数据资产管理、盘口数据加工、策略研究与回测，以及执行前的持仓和分配结果输出。

当前仓库正式纳入的是数据、研究、目标持仓导出链路，以及作为可选执行下游固定版本的 `quant-execution-engine`。将执行引擎纳入 superproject 用于复现交接契约和联调基线，不表示 paper 或 live 已默认启用；券商连接仍需执行系统独立门禁。

## 平台能力

```text
市场数据 / 基本面                    港股盘口快照
       |                                  |
       v                                  v
market-data-platform  ------>  rqdata-hk-depth-snapshots (transition backend)
数据契约、CN provider、统一入口    HK depth 现存实现
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
quant-execution-engine（可选下游，已纳入 submodule）
券商下单、订单跟踪、对账、异常恢复
```

## 当前组成

| 项目 | 当前职责 | 主要交付 |
| --- | --- | --- |
| [`market-data-platform`](market-data-platform/) | HK / CN 数据平台入口；定义 contract / registry，原生承载 CN provider MVP，并调度过渡中的 HK 数据工具 | `marketdata ...`、版本化数据契约与资产索引 |
| [`rqdata-hk-depth-snapshots`](rqdata-hk-depth-snapshots/) | 迁移期间保留的 HK depth backend，通过 `marketdata rqdata hk-depth -- ...` 调用 | `tick_depth_raw`、`tick_depth_daily` 及未来成本模型输入 |
| [`cross-sectional-trees`](cross-sectional-trees/) | 策略研究与目标导出；迁移期间仍提供 HK RQData asset backend，通过 `marketdata rqdata hk-assets -- ...` 调用 | 研究输出，以及待迁移的数据维护实现 |
| [`quant-execution-engine`](quant-execution-engine/) | 可选的券商连接执行系统，读取目标持仓后执行下单、追踪、对账和异常恢复 | 执行审计、订单状态和复查证据 |

`quant-execution-engine` 现在作为可选 submodule 固定在工作区中，以便复现 `cross-sectional-trees` 的 `cstree export-targets` 到引擎 canonical `targets.json` 输入的交接。当前已验证导出文件可被引擎解析并生成离线调仓计划；港股计划要求显式配置 HKD 到 USD 汇率，券商侧的 paper / live 操作仍由执行系统独立门禁控制。

## 典型路径

1. 使用数据平台或现有数据维护工具发布版本化的日线、PIT、估值和盘口派生资产。
2. 由 `cross-sectional-trees` 读取已发布资产，开展特征研究、模型评估、回测和候选策略治理。
3. 生成持仓快照与执行前分配结果，并显式运行 `cstree export-targets` 生成可审计的执行交接文件。
4. 如需连接真实或模拟券商，将该目标文件交给可选执行引擎的预演 / paper 流程，并保留其独立门禁。

模块执行顺序、数据契约边界、执行验证状态和未来调度原则见 [平台工作流与集成边界](docs/platform-workflow.md)。

## 顶层职责

`research-workspace` 顶层只负责：

- 锁定一组可复现的 submodule commit 组合。
- 说明跨模块边界、文件契约和执行顺序。
- 提供轻量 workspace doctor / contract smoke 验证入口。
- 记录已验证版本矩阵和人工联调证据。

它不负责：

- 实现数据下载、研究、回测、下单等业务逻辑。
- import 子模块内部 Python 包。
- 维护替代各子项目配置系统的总配置。
- 作为无人值守真实交易调度器。

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

## 顶层文档与检查

| 主题 | 入口 |
| --- | --- |
| 新机器初始化 | [docs/bootstrap.md](docs/bootstrap.md) |
| 跨模块文件契约 | [docs/contracts.md](docs/contracts.md) |
| 已验证版本组合 | [docs/version-matrix.md](docs/version-matrix.md) |
| bump submodule 前检查 | [docs/release-checklist.md](docs/release-checklist.md) |
| workspace 健康检查 | `python scripts/workspace_doctor.py` |
| 只读契约 smoke | `python scripts/smoke_contracts.py` |
| 打印当前版本矩阵 | `python scripts/print_version_matrix.py` |
