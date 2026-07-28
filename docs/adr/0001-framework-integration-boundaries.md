# ADR-0001：Qlib、LEAN、vn.py 与 Backtrader 的集成边界

- 状态：accepted
- 日期：2026-07-13
- 决策范围：`research-workspace` 及六个固定版本的子模块
- 迁移账本：[`../framework-integration-ledger.yml`](../framework-integration-ledger.yml)
- 当前状态：[`../framework-support-matrix.md`](../framework-support-matrix.md)

## 背景

当前平台已经形成 A 股数据治理、时间点（PIT）语义、研究证据与晋升门禁、确定性组合回放，以及执行审批、审计和对账等领域能力。同时，通用数据集处理、实验记录、Top-K 基线、Gateway、事件分发和 订单管理系统（OMS）状态归一化与成熟开源框架存在重合。

本决策的目标是保留领域资产，为通用能力建立可替换后端，并避免第三方框架对象成为跨仓库契约。

## 决策

### Qlib 是可选研究与差分回测后端

- `market-data-platform` 仍是原始数据、PIT 语义、资产清单、资产登记表和发布指针的唯一权威来源。
- `alpha-research` 可以通过 framework-neutral port 使用 Qlib 的 Dataset、DataHandler、Model 和 Recorder 能力。
- `portfolio-backtester` 可以使用 Qlib 运行通用基线和差分测试。A 股特有的可交易性、费用、T+1 和确定性回放仍由 native backend 定义。
- Qlib 只能通过 optional extra 安装。没有安装 Qlib 时，native 路径必须可导入、可测试、可运行。
- Qlib 对象不得写入 `signals`、`positions`、`targets` 或其他跨仓库 artifact。

### vn.py 是可选执行传输层

- `quant-execution-engine` 继续拥有目标校验、policy、approval、preflight、幂等、持久 journal、kill switch、evidence 和 reconciliation。
- vn.py 可以提供 Gateway 生命周期、订单请求、回报事件和账户、合约、持仓状态的归一化。
- vn.py 适配器先以影子模式和模拟模式进入。影子模式必须在类型和运行时两层阻止真实报单。
- vn.py 内存 OMS 不作为 qexec 的审计权威来源。可恢复状态仍由 qexec 持久证据归约产生。
- vn.py 只能通过 optional extra 安装，且不得被 core import path 隐式加载。

### LEAN 是领域模型与 golden reference

- LEAN 不进入当前 Python 主运行时，也不成为跨仓库依赖。
- 平台借鉴 `Insight -> PortfolioTarget -> Risk-adjusted target -> Execution` 的职责拆分，明确区分研究信号、组合目标、风险决策和订单意图。
- LEAN 对照通过 framework-neutral scenario、fill 和 summary 文件交换完成。对照运行可以独立于工作区执行。
- 是否把 LEAN 提升为运行时，需要新的 架构决策记录（ADR），并以全球多资产、统一事件驱动回测与实盘等明确需求为前提。

### Backtrader 暂缓采用

- Backtrader 只保留在 `portfolio-backtester` 的评估清单中。
- 当前没有适配器、可选依赖、固定样例或真实运行时门禁。
- 后续采用前需要明确它能替换的维护面，并与原生 A 股回放完成文件化差分。

### `strategy-pipeline` 收敛为应用编排层

- 该仓库保留 命令行（CLI）、配置合成、职责仓接口编排、运行回执和纯目标导出。
- 数据生产、PIT 关联、模型训练、组合算法和券商行为分别委托给对应职责仓。
- 迁移期间允许保留登记在册且注明退役版本的兼容入口。不得新增未登记的重复实现。

## 跨仓库不变量

1. native 路径在 parity evidence 被接受前保持默认。
2. 第三方框架类型不得进入跨仓库 Python public result 或 artifact schema。
3. 适配器失败不得改变权威资产、研究晋升决策或执行审计状态。
4. 删除原生通用实现前必须具备确定性固定样例、差分报告、迁移说明和回滚路径。
5. superproject 只在下游提交进入 `main` 且组合验证通过后更新 子模块 pin。
6. 单元测试不连接数据服务商、真实券商或外部框架服务。

## 未选择的方案

### 整体迁移到 Qlib

这会把数据资产权威、PIT 治理和研究晋升边界绑定到 Qlib 内部对象，同时不能覆盖执行控制面，因此不采用。

### 整体迁移到 vn.py

vn.py 适合实时传输层和 Gateway 生态，无法覆盖以产物为中心的研究链、持久审批证据和可复现晋升流程，因此不整体采用。

### 以 LEAN 作为当前主运行时

当前主线是 Python、A 股横截面研究和文件化交接。引入完整 LEAN runtime 的迁移成本高于现阶段收益，因此只保留 reference integration。

### 继续扩张全部 native 通用框架

这会继续增加 Dataset、Recorder、Gateway、OMS 和事件回测等重复维护面，因此冻结这类扩张。只有 A 股领域语义、研究可信度、契约 和执行控制面可以直接新增能力。

## 当前实现说明

本 ADR 记录长期边界，不声明适配器已经完成。截至 2026-07-19，当前 `main` 中只有数据平台的 Qlib `DataLoader` 适配器属于真实外部框架实现。alpha、回测和执行仓库仍停留在框架中立接口、原生实现或规划阶段。历史候选分支中的 Qlib、LEAN 和 vn.py 代码没有完整进入当前职责仓原生主线。

## 后果

- 短期内 native 与 framework adapter 会并存，代码总量可能暂时上升。
- 每个 adapter 都必须以可删除的边界模块存在，并用差分证据证明价值。
- 迁移完成度由机器可读账本记录，不以依赖已安装或 demo 跑通作为完成标准。
- 外部框架升级只能影响适配器。跨仓库产物和职责仓接口必须保持兼容。

## 官方参考

- [Qlib data layer](https://qlib.readthedocs.io/en/latest/component/data.html)
- [Qlib experiment manager and recorder](https://qlib.readthedocs.io/en/latest/component/recorder.html)
- [LEAN Algorithm Framework](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview)
- [vn.py repository and engine examples](https://github.com/vnpy/vnpy)
