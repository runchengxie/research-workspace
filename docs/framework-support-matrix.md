# 外部框架支持矩阵

> status: active
> owner: workspace
> last_verified: 2026-09-02
> source_of_truth: yes
> superseded_by: n/a

本页记录当前 `main` 中可验证的外部框架支持，以及已经完成架构评估但尚未接入运行时的候选。判断依据依次为当前源码、依赖声明、锁文件和可执行测试。历史候选分支只用于说明来路，不能作为当前版本的能力证明。

## 状态说明

| 状态 | 含义 |
| --- | --- |
| 已实现，条件化验证 | 当前源码包含适配器。安装可选依赖后才能运行真实框架测试 |
| 仅有接口 | 当前源码只有框架中立接口和原生实现 |
| 设计参考 | 只借鉴领域模型或职责划分，没有运行时集成 |
| 评估候选 | 已明确 owner、用途和采用门禁，当前没有适配器 |
| 规划中 | 已记录采用方向，尚未形成完整采用门禁 |
| 范围外 | 该仓库不直接依赖该框架 |

## 当前运行时矩阵

| 仓库 | Qlib | LEAN | vn.py | Backtrader |
| --- | --- | --- | --- | --- |
| `market-data-platform` | 已实现，条件化验证 | 范围外 | 范围外 | 范围外 |
| `alpha-research` | 已实现，条件化验证 | 范围外 | 范围外 | 范围外 |
| `portfolio-backtester` | 仅有接口，差分后端规划中 | 设计参考 | 范围外 | 规划中 |
| `strategy-app` | 范围外 | 范围外 | 范围外 | 范围外 |
| `strategy-pipeline` | 通过职责仓接口间接使用 | 范围外 | 范围外 | 范围外 |
| `quant-execution-engine` | 范围外 | 范围外 | 仅有通用执行接口，适配器规划中 | 范围外 |

## 新评估候选

以下项目目前只登记角色，不代表已经进入运行时：

| 项目 | 目标 owner | 状态 | 允许用途 | 明确禁止 |
| --- | --- | --- | --- | --- |
| vectorbt | `alpha-research` / `strategy-research` | 评估候选 | 大规模技术规则、参数 surface、快速 hypothesis screening | 作为 A 股权威成交/回测引擎 |
| RQAlpha | `portfolio-backtester` | 评估候选 | 固定样例 differential backtest，逐日比较成交、费用、持仓、现金和市场规则 | 替换平台 PIT、晋级门禁或原生执行语义 |
| PyPortfolioOpt | `portfolio-backtester` | 评估候选 | 常规约束优化、Black-Litterman、tracking-error 类对照 | 第三方对象进入跨仓产物 |
| cvxportfolio | `portfolio-backtester` | 设计参考 / 评估候选 | 成本感知、多期优化架构和研究对照 | 未完成许可证/差分评估前成为分发依赖 |
| Riskfolio-Lib | `portfolio-backtester` | 设计参考 | 更广风险度量与稳健优化研究对照 | 扩大生产优化自由度而没有预注册研究门禁 |
| Alphalens Reloaded | `alpha-research` | 评估候选 | IC、分组、换手、factor tear-sheet 差分验证 | 取代平台 PIT、特征证据和晋级流程 |
| Evidently | `alpha-research` / presentation projection | 设计参考 | research-vs-live 数据/信号漂移计算参考 | 直接决定策略生命周期或投资结论 |
| MLflow | `alpha-research` | 设计参考 | `ExperimentRecorder` 的可选实现、模型 run/metric lineage | 取代 `research_spec`、PBO、证据门禁和 claim/counterexample 治理 |
| Dagster | workspace | 设计参考 | asset graph、freshness、lineage 概念参考 | 新建第二套编排控制面而未证明维护收益 |
| OpenBB | `market-data-platform` / `market-intel` | 设计参考 | provider normalization 和 connect-once-consume-everywhere 模式 | 绕过数据 owner、PIT 和授权边界 |
| NautilusTrader | `quant-execution-engine` | 设计参考 | research/live parity、确定性事件语义 | 直接替换中国市场执行 transport 规划 |

新增候选的完整边界见 `docs/superpowers/specs/2026-09-02-platform-publication-and-research-platform-design.md`。

## 逐仓证据

### market-data-platform

Qlib `DataLoader` 适配器已经进入当前 `main`：

- 可选依赖位于 `pyproject.toml` 的 `qlib` extra
- 适配器位于 `src/market_data_platform/integrations/qlib.py`
- 延迟加载封装位于 `src/market_data_platform/integrations/_qlib_runtime.py`
- 对照和导入测试位于 `tests/test_published_assets.py`

该适配器只读取已经发布的 Parquet 资产。它不包含 `DataHandler`、`Trainer` 或 `Recorder`，也不会改变资产登记表和当前指针。标准 `dev` 门禁没有安装 `pyqlib`，真实运行时测试可能跳过。需要确认外部框架兼容性时，应额外安装 `qlib` extra 并核对测试没有跳过。

OpenBB 当前只作为 provider normalization 的设计参考。数据资产、PIT 语义、版本身份、质量回执和 current pointer 仍由 `market-data-platform` 负责。

### alpha-research

当前 `main` 提供 `DatasetBackend`、`TrainerBackend` 和 `ExperimentRecorder` 接口，以及对应的原生实现。源码位于 `src/alpha_research/backends/`，测试位于 `tests/test_research_backends.py`。

Qlib 适配器已进入当前 `main`（ADR-0005）：

- 可选依赖位于 `pyproject.toml` 的 `qlib` extra（`pyqlib>=0.9.5`）
- 适配器位于 `src/alpha_research/backends/qlib.py`，提供 `QlibTrainerBackend` 和 `QlibDatasetBackend`
- 未安装 `pyqlib` 时原生路径保持可导入、可测试
- 训练与预处理测试位于 `tests/test_backends_qlib.py`

该适配器只做训练与横截面标准化预处理，不接 Qlib 的 Recorder 或实验管理，也不把 Qlib 对象写入跨仓库产物。判断依据来自 `experiments/qlib_pilot` 的真实 A 股数据对打：完整预处理管线带来的 IC 提升约 0.048。标准 `dev` 门禁没有安装 `pyqlib`，真实运行时测试可能跳过。

vectorbt、Alphalens Reloaded、Evidently 和 MLflow 目前均没有运行时适配器。任何接入都必须保持现有 native/Qlib 路径可用，并把结果归一化为平台自己的普通数据/metadata。

### portfolio-backtester

当前后端登记表只包含原生回放。接口和实现位于 `src/portfolio_backtester/backends/`，现有基准样例只覆盖流动性充足的原生只做多场景。

Qlib 差分后端和 LEAN 文件化场景曾出现在旧候选分支，当前 `main` 没有对应源码、依赖或测试。LEAN 目前只用于职责划分参考。Backtrader 仍处于规划阶段，当前没有适配器、固定样例或运行时门禁。

RQAlpha 的优先用途是 A 股 differential backtest，用于对照原生语义。组合优化侧应先建立框架中立 request/result，再评估 PyPortfolioOpt/cvxportfolio/Riskfolio 适配器。现有 equal/rank/sleeve/HRP 构造继续作为基线。

### strategy-app 与 strategy-pipeline

`strategy-app` 组合数据、alpha 和组合回测职责仓接口，不直接安装外部框架。`strategy-pipeline` 负责配置和调用顺序，只能通过职责仓接口间接消费后端结果。两个仓库都不得把第三方框架对象写入公开结果或跨仓库产物。

### quant-execution-engine

当前 `main` 提供框架中立的订单、事件和券商适配器边界，并支持 Longport、Alpaca 与 IBKR 可选依赖。当前没有 vn.py extra 或传输层实现。

旧堆叠式开发分支中曾有 vn.py 影子模式和模拟模式候选实现，最终候选没有进入当前 `main`。后续若恢复，应基于现有 `quant_execution_engine` 命名空间重新实现，并通过真实的影子下单阻断、重复回报、重启恢复和对账测试。NautilusTrader 仅作为 research/live parity 与确定性事件模型参考。

## 采用原则

- 原生路径在差分证据通过前保持默认。
- 外部框架对象只存在于适配器内部。
- 跨仓库边界继续使用平台自己的请求、回执和文件产物。
- 历史候选分支、格式校验测试和导入边界测试不能单独证明运行时可用。
- 新适配器需要有可选依赖、无框架导入测试、真实运行时测试、固定场景差分证据、许可证检查和回滚说明。
- screening backend 的结果不能直接获得策略晋级资格，必须回到平台 PIT/OOS/成本/容量/证据门禁。

长期边界见 [ADR-0001](adr/0001-framework-integration-boundaries.md)。采用取舍与后续顺序见 [框架采用评估](framework-adoption-assessment.md)。历史候选发布记录见 [archive/framework-adapter-release.md](archive/framework-adapter-release.md)。
