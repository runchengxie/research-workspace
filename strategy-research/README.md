# 策略研究与生命周期

本目录是工作区内策略身份、投资假设、生命周期、评审结论和证据导航的权威入口。可执行代码仍按职责放在各仓库，策略是否生产化由 [catalog.json](catalog.json) 的显式字段决定；代码位置不表达生命周期。

## 当前策略地图

| 策略或策略族 | 生命周期 | 可进入生产发布 | 人类可读说明 | 主要运行位置 |
| --- | --- | --- | --- | --- |
| DailyWatch20 | operational | 是 | [strategies/daily_watch20/README.md](strategies/daily_watch20/README.md) | `strategy-app`、`strategy-pipeline` |
| 热点板块选股 | research_shadow | 否 | [strategies/hotsector/README.md](strategies/hotsector/README.md) | `strategy-app`、`strategy-pipeline`、外部 `market-intel` |
| StyleReplica A80/B20 | operational_research | 否 | [strategies/style_replica/README.md](strategies/style_replica/README.md) | `strategy-research/style_factors`（`python -m style_factors`）、`strategy-pipeline` |
| D11-H5 五袖套 | shadow | 否 | [strategies/d11_h5_shadow/README.md](strategies/d11_h5_shadow/README.md) | `alpha-research`、`portfolio-backtester`、`strategy-pipeline` |
| 红利与成长 ETF 动量 | pre_production | 否 | [pre_production/dividend_growth_momentum/README.md](pre_production/dividend_growth_momentum/README.md) | `strategy-app`、`portfolio-backtester` |
| 次日开盘到最高价 | exploration | 否 | [experiments/next_open_to_high/README.md](experiments/next_open_to_high/README.md) | `experiments` |
| Guan 周度策略 | external_research | 否 | [strategies/guan_weekly/README.md](strategies/guan_weekly/README.md) | 外部 `guan-factor-research-framework`、`strategy-app` bridge |

完整机器可读字段、代码入口、变体和迁移债务见 [catalog.json](catalog.json)。

## 三层职责

| 层 | 负责 | 不负责 |
| --- | --- | --- |
| `strategy-research` | 策略想法、参数语义、生命周期、评审结论、证据索引 | 被生产进程导入的运行时代码 |
| `strategy-app` | 策略特有纯计算、冻结合同、owner API 薄组合 | 通用数据、alpha、统计、组合、执行能力与生产发布 |
| `strategy-pipeline` | 运行编排、外部调用、操作窗口、运行目录、原子发布、门禁、`targets.json` | 策略 thesis、研究算法、组合会计和重复 owner contract |

数据、特征、标签、模型和通用统计归 `market-data-platform` 与 `alpha-research`。组合构造、成本、可交易性和执行回放归 `portfolio-backtester`。交易执行归 `quant-execution-engine`。

## 什么算策略

策略必须描述可复核的投资假设、候选范围、信号、组合构造、调仓时点、成本假设和失败条件。以下对象不单独登记为策略：

- `strategy run --config ...` 是可配置运行流程
- `StrategySpec` 是信号到组合的技术合同
- Qlib pilot 是研究后端和方法评估
- 风格因子与基本面 shadow 是策略输入或策略族内实验
- F-lite、slow-volume、incumbent challenger、Numeric v2、低换手和 DeepSeek 是已登记策略族中的变体或挑战方案

## 生命周期

- `exploration`：快速试错，结论和可复现性仍可能不完整
- `pre_production`：值得长期跟踪，已有证据，尚未获得发布授权
- `shadow` 或 `research_shadow`：按真实时间追加观察，明确禁止生产发布
- `operational_research`：有稳定命令和运行合同，仍只用于研究
- `operational`：具备受控运行与发布路径，是否发布仍由当次门禁决定
- `external_research`：主要实现在外部仓库，本目录只维护身份与接入边界

每个阶段对应的强制证据清单和校验命令见 [../docs/strategy-evidence-gate.md](../docs/strategy-evidence-gate.md)。
生命周期变化必须配套证据包，禁止用单点回测数字代替证据清单。

## 新增与晋级

1. 先在本目录新增人类可读说明和 `catalog.json` 条目。
2. 探索脚本放入 `experiments`，可复用能力直接进入对应职责仓。
3. 只有策略特有的可执行组合进入 `strategy-app`。
4. 只有外部调用、运行控制和发布接线进入 `strategy-pipeline`。
5. 生命周期变化必须绑定证据路径、评审结论和 `production_eligible` 变更，不以移动代码代替评审。

旧实验、外部策略和 pipeline 内策略模块的排查结论已经登记在 catalog 的 `inventory_notes` 与各策略 `extraction_debt` 字段中。R0 至 R6 的迁移记录见[策略边界重构完成记录](../docs/strategy-boundary-refactor-roadmap.md)，剩余证据、接口和数据工作见[工作区路线图](../docs/roadmap.md)。

## 早期档案

港股月频、季频 PIT 研究与 A 股早期探索已经归档，权威索引入口见 [archive/](archive/README.md)。
原始文件冻结在 `strategy-pipeline/docs/archive/research/`，本目录只维护索引与结论，不复制被哈希绑定的内容。
