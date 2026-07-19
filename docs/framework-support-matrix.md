# 外部框架支持矩阵

> status: active
> owner: workspace
> last_verified: 2026-07-19
> source_of_truth: yes
> superseded_by: n/a

本页记录当前 `main` 中可验证的 Qlib、LEAN、vn.py 和 Backtrader 支持。判断依据依次为当前源码、依赖声明、锁文件和可执行测试。历史候选分支只用于说明来路，不能作为当前版本的能力证明。

## 状态说明

| 状态 | 含义 |
| --- | --- |
| 已实现，条件化验证 | 当前源码包含适配器。安装可选依赖后才能运行真实框架测试 |
| 仅有接口 | 当前源码只有框架中立接口和原生实现 |
| 设计参考 | 只借鉴领域模型或职责划分，没有运行时集成 |
| 规划中 | 已记录采用条件，当前源码没有适配器 |
| 范围外 | 该仓库不直接依赖该框架 |

## 当前矩阵

| 仓库 | Qlib | LEAN | vn.py | Backtrader |
| --- | --- | --- | --- | --- |
| `market-data-platform` | 已实现，条件化验证 | 范围外 | 范围外 | 范围外 |
| `alpha-research` | 仅有接口，适配器规划中 | 范围外 | 范围外 | 范围外 |
| `portfolio-backtester` | 仅有接口，差分后端规划中 | 设计参考 | 范围外 | 规划中 |
| `research-apps` | 范围外 | 范围外 | 范围外 | 范围外 |
| `strategy-pipeline` | 通过职责仓接口间接使用 | 范围外 | 范围外 | 范围外 |
| `quant-execution-engine` | 范围外 | 范围外 | 仅有通用执行接口，适配器规划中 | 范围外 |

## 逐仓证据

### market-data-platform

Qlib `DataLoader` 适配器已经进入当前 `main`：

- 可选依赖位于 `pyproject.toml` 的 `qlib` extra
- 适配器位于 `src/market_data_platform/integrations/qlib.py`
- 延迟加载封装位于 `src/market_data_platform/integrations/_qlib_runtime.py`
- 对照和导入测试位于 `tests/test_published_assets.py`

该适配器只读取已经发布的 Parquet 资产。它不包含 `DataHandler`、`Trainer` 或 `Recorder`，也不会改变资产登记表和当前指针。标准 `dev` 门禁没有安装 `pyqlib`，真实运行时测试可能跳过。需要确认外部框架兼容性时，应额外安装 `qlib` extra 并核对测试没有跳过。

### alpha-research

当前 `main` 提供 `DatasetBackend`、`TrainerBackend` 和 `ExperimentRecorder` 接口，以及对应的原生实现。源码位于 `src/alpha_research/backends/`，测试位于 `tests/test_research_backends.py`。

当前依赖和源码均未包含 Qlib 适配器。旧堆叠式开发分支中出现过基于已删除 `cstree` 命名空间的候选实现，该实现没有进入当前 `main`。如需恢复，应使用现有归属仓库原生接口重新实现，并重新生成差分证据。

### portfolio-backtester

当前后端登记表只包含原生回放。接口和实现位于 `src/portfolio_backtester/backends/`，现有基准样例只覆盖流动性充足的原生只做多场景。

Qlib 差分后端和 LEAN 文件化场景曾出现在旧候选分支，当前 `main` 没有对应源码、依赖或测试。LEAN 目前只用于职责划分参考。Backtrader 仍处于规划阶段，当前没有适配器、固定样例或运行时门禁。

### research-apps 与 strategy-pipeline

`research-apps` 组合数据、alpha 和组合回测职责仓接口，不直接安装外部框架。`strategy-pipeline` 负责配置和调用顺序，只能通过职责仓接口间接消费后端结果。两个仓库都不得把第三方框架对象写入公开结果或跨仓库产物。

### quant-execution-engine

当前 `main` 提供框架中立的订单、事件和券商适配器边界，并支持 Longport、Alpaca 与 IBKR 可选依赖。当前没有 vn.py extra 或传输层实现。

旧堆叠式开发分支中曾有 vn.py 影子模式和模拟模式候选实现，最终候选没有进入当前 `main`。后续若恢复，应基于现有 `quant_execution_engine` 命名空间重新实现，并通过真实的影子下单阻断、重复回报、重启恢复和对账测试。

## 采用原则

- 原生路径在差分证据通过前保持默认。
- 外部框架对象只存在于适配器内部。
- 跨仓库边界继续使用平台自己的请求、回执和文件产物。
- 历史候选分支、格式校验测试和导入边界测试不能单独证明运行时可用。
- 新适配器需要有可选依赖、无框架导入测试、真实运行时测试、差分证据和回滚说明。

长期边界见 [ADR-0001](adr/0001-framework-integration-boundaries.md)。采用取舍与后续顺序见 [框架采用评估](framework-adoption-assessment.md)。历史候选发布记录见 [外部框架适配器候选发布](framework-adapter-release.md)。
