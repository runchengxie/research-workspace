# Agent 任务级上下文边界

> status: active
> owner: workspace
> audience: human and agent
> last_verified: 2026-09-06
> source_of_truth: yes
> superseded_by: n/a

本页定义编码代理处理小任务时的最小阅读范围。权威机器可读映射位于
`scripts/context_manifest.py`，映射是显式配置，不通过递归读取仓库生成。

## 使用规则

先把任务归入一个区域：

```bash
python scripts/context_manifest.py --task alpha
```

默认只读取输出中的 `Default context` 和 `Repositories`。修改跨仓 artifact 时，再读取对应
`Contract routes` 中列出的直接生产方、契约文件、直接消费方和测试。一个任务涉及多个区域时，
分别生成 manifest，并在动手前写明跨越的契约。未知区域会失败关闭，不提供读取全部仓库的
`all` 模式。

| 区域 | 默认仓库 | 直接边界摘要 |
| --- | --- | --- |
| `data` | `market-data-platform` | 当前资产、研究特征和版本化数据产物 |
| `microstructure` | `deep-learning-tick-data-prediction` | L2 预测产物到 alpha |
| `alpha` | `alpha-research` | 信号与 metadata 到组合和编排 |
| `portfolio` | `portfolio-backtester` | 信号输入与持仓输出 |
| `strategy` | `strategy-research`、`strategy-app` | 策略知识、冻结合同和策略计算 |
| `orchestration` | `strategy-pipeline` | run manifest、发布和下游交接 |
| `execution` | `quant-execution-engine` | `targets.json`、风控和执行审计 |
| `market-intel` | 外部独立应用 `market-intel` | 正式策略产物到报告和投递 |

## `alpha-research`

- 职责：维护特征、模型、研究评估、稳健性诊断和信号产物。
- 允许依赖：`market-data-platform` 的公开数据接口和版本化产物、L2 预测契约、
  `research-contracts` 的共享 envelope 与校验接口。
- 禁止依赖：`portfolio-backtester` 内部实现、`strategy-pipeline` 运行时和
  `market-intel` 私有实现。
- 契约文件：`signals.parquet`、`signals.meta.json` 和
  `alpha-research/src/alpha_research/signal_artifact.py`。
- 最小测试：`pytest alpha-research/tests/test_signal_artifact.py -q`。

## `portfolio-backtester`

- 职责：维护组合构造、回测、成本、容量、暴露、风险计算和报告辅助能力。
- 允许依赖：版本化信号、持仓和行情输入，以及 `research-contracts` 的共享校验接口。
- 禁止依赖：`alpha_research` 和 `strategy_pipeline.pipeline` 的运行时内部实现、策略假设、
  数据下载与券商执行。
- 契约文件：`signals.parquet`、`positions_by_rebalance.csv`、
  `positions_by_rebalance.meta.json` 和
  `portfolio-backtester/src/portfolio_backtester/contracts.py`。
- 最小测试：`pytest portfolio-backtester/tests/test_position_outputs.py -q`。

## `strategy-research`

- 职责：维护策略身份、投资假设、参数语义、生命周期、评审结论和证据导航。
- 允许依赖：各 owner 仓的公开计算接口、版本化 artifact 和可审计 receipt。
- 禁止依赖：生产进程专用运行时代码、重复的数据、alpha、组合、编排或执行内核，以及用目录
  位置推断策略生命周期。
- 契约文件：`strategy-research/catalog.json`、`strategy-research/research/strategies/` 中的策略
  说明，以及输入的 `research-run.manifest.json`。
- 最小测试：`pytest strategy-research/tests/test_root_layout.py -q`。

## `strategy-app`

- 职责：维护策略专用纯计算、冻结实验合同、研究应用和 publication payload。
- 允许依赖：`market-data-platform`、`alpha-research` 和 `portfolio-backtester` 的公开接口与
  版本化 artifact，以及冻结的 JSON 规格。
- 禁止依赖：从 `src/strategy_app` 导入 `strategy_pipeline`、复制通用能力、承担生产发布或
  保存 provider 与 broker 凭证。
- 契约文件：`strategy-app/src/strategy_app/campaign_specs/*.json`、
  `strategy-app/src/strategy_app/daily_watch20/pipeline_publication.py`、`watchlist_20.csv` 和
  `selection_receipt.json`。
- 最小测试：
  `pytest strategy-app/tests/test_daily_watch20_publication_contracts.py -q`。

## `strategy-pipeline`

- 职责：维护 run 编排、外部调用、artifact reference、receipt、原子发布和下游 handoff。
- 允许依赖：owner 仓的公开 API、protocol、注入式 adapter 和版本化 artifact。
- 禁止依赖：私有研究内部模块、策略思想和模型实现、组合规则、provider 凭证与专有数据。
- 契约文件：`research-run.manifest.json`、`watchlist_20.csv`、`targets.json`、
  `strategy-pipeline/src/strategy_pipeline/control_plane/contracts.py` 和
  `strategy-pipeline/src/strategy_pipeline/control_plane/targets.py`。
- 最小测试：`pytest strategy-pipeline/tests/control_plane/test_contracts.py -q`。

## `market-intel`

- 职责：在独立私有运行环境中维护市场上下文、报告组装、Dashboard、投递、freshness、幂等和
  运行恢复。
- 允许依赖：公开 CLI、版本化文件、receipt 和已登记的 artifact 契约。
- 禁止依赖：直接导入工作区或其他 owner 的私有研究内部模块，以及把 provider、凭证或生产参数
  写入本公开工作区。
- 契约文件：消费 `watchlist_20.csv` 等正式策略产物，反向提供信号时遵守
  `signals.parquet` 和 `signals.meta.json` 契约。
- 最小测试：在 `market-intel` 独立检出中运行 `uv run pytest -k contract`。

## 扩大范围的条件

只有以下情况需要读取直接相邻区域：

- 修改 artifact 字段、schema 版本、文件名、兼容策略或 envelope。
- 修改生产方写入行为或消费方解析、校验行为。
- 修改会改变跨仓最小测试命令的公开入口。

仅修改一个 owner 仓的内部实现时，不读取间接消费方。`alpha` 任务不会因为
`strategy-pipeline` 最终向 `market-intel` 发布产物，就默认读取 `market-intel`。
