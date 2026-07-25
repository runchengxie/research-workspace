# 策略总览（导航索引）

> status: reference
> owner: workspace
> last_verified: 2026-07-25
> source_of_truth: no
> superseded_by: n/a

本文件是策略相关文档的单一入口与术语澄清，本身不重复各策略的细节。工作区内研究应用的完整目录见 [research-apps/docs/application-catalog.md](../research-apps/docs/application-catalog.md)，外部卫星项目见 [strategy-satellites.md](strategy-satellites.md)。

## 先澄清几个容易混淆的词

本工作区里策略一词被重载使用，读文档前先对齐：

- `研究应用`（research app）：`research-apps` 仓里真正承载策略研究逻辑的单元，分 `DailyWatch20` 与热点板块选股两族（候选池 OOS、F-lite、慢速成交量、旧仓再资格、Numeric v2、低换手、AI 影子、DeepSeek 等）。这是新人最常问的策略所指。
- `信号`（signal）：`alpha_research.signals` 契约规定的 `signals.parquet` 产物，是带评分的模型输出（含 `raw_pred`、`rank`、`model_version`、`eligible_for_backtest/live` 等字段），由 `alpha-research` 产出。
- `StrategySpec`：`strategy_pipeline` 里的组合构建规格（`name`、`top_k`、`weighting`、`long_only`、`execution` 等），描述如何把信号变成组合，而非交易想法本身。
- `卫星`（satellite）：特指由 `market-intel` 维护、以版本化文件接入本工作区的外部项目（`hot-sector-screener`、`ai-stock-picker`、`a-share-factor-core`）。它们提供候选池、信号与选择结果，不是本工作区内部代码。

## 策略生命周期（跨仓库链路）

```text
market-data-platform   提供已发布资产与来源标识（不直接调供应商）
        ↓
alpha-research         通用特征、标签、模型 → 信号产物 signals.parquet
        ↓
research-apps          策略级研究：组合研究流程、预注册合同、证据解释（返回 Python 值 / DataFrame / 报告 / 回执）
        ↓
strategy-pipeline      外部模型调用、操作时段、统计验证、导出 targets.json
        ↓
portfolio-backtester   组合构造、成本 / 容量 / 风险、错峰（staggered）队列执行
        ↓
quant-execution-engine 解析 targets.json、盘前仿真、风险、受控交易
```

外部卫星的输入在 `strategy-pipeline` 之前汇入（见下方链接）。

## 去哪里找细节（按问题选文档）

| 我想了解 | 看这里 |
| --- | --- |
| 工作区内每个研究应用做什么、入口函数、比较组、证据用途 | [research-apps/docs/application-catalog.md](../research-apps/docs/application-catalog.md) |
| 冻结实验规格（内容寻址 JSON）清单与 SHA-256 约束 | [research-apps/docs/application-catalog.md](../research-apps/docs/application-catalog.md)（冻结实验规格节） |
| 外部卫星项目（market-intel）如何接入、交接产物与文件流向 | [strategy-satellites.md](strategy-satellites.md) |
| 信号产物（signals.parquet）的字段与契约 | [alpha-research/docs/reference/signal-artifacts.md](../alpha-research/docs/reference/signal-artifacts.md) |
| StrategySpec（组合构建规格）字段定义 | [strategy-pipeline/src/strategy_pipeline/contracts/strategy.py](../strategy-pipeline/src/strategy_pipeline/contracts/strategy.py) |
| 单个 campaign 的预注册、结果与回执 | [strategy-pipeline/docs/research/README.md](../strategy-pipeline/docs/research/README.md) |
| 研究协议与结果归档（迁移字节身份） | [research-apps/docs/research/README.md](../research-apps/docs/research/README.md) |

## market-intel 有没有策略

没有。market-intel 是数据 / 情报 / 投递层：它产出因子（`a-share-factor-core`）、候选池与信号（`hot-sector-screener`，`eligible_for_live=false`）、AI 重排列表（`ai-stock-picker`），但这些都不含买卖 / 仓位 / 执行逻辑。真正端到端的策略与执行在本工作区的 `research-apps` → `strategy-pipeline` → `quant-execution-engine` 链路中。market-intel 在本索引里只以卫星身份出现（见 [strategy-satellites.md](strategy-satellites.md)）。

## 维护提示

- 新增研究应用：更新 [research-apps/docs/application-catalog.md](../research-apps/docs/application-catalog.md)，不要在本文件复制细节。
- 新增外部接入：更新 [strategy-satellites.md](strategy-satellites.md)。
- 本文件只维护术语澄清与链接索引，细节以各源文档为准（均标 `source_of_truth: yes` 或带 `last_verified`）。
