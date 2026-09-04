# A 股数据与研究入口 playbook

> status: active
> owner: workspace
> last_verified: 2026-07-16
> source_of_truth: yes
> superseded_by: n/a

本页说明 A 股当前资产、研究入口和港股归档边界。数据下载运维手册由
`market-data-platform` 维护，研究与回测实现分别由 `alpha-research`、
`portfolio-backtester` 和 `strategy-pipeline` 维护。

## 当前决策

截至 2026-07-16，A 股长窗口日线、时间点（PIT）财务报表和历史行业变更已经写入 current
契约。港股继续按恢复专用归档管理。

1. 活跃 `DATA_PLATFORM_ROOT` 保留 A 股契约、资产和 registry。
2. 中国香港市场资产冻结到独立冷存储，活跃根目录只保留 freeze marker。
3. 港股历史复现、跨市场对照或明确跟踪需求出现时，先显式 hydrate。
4. A 股 `default` 是日线价格、日频估值和全市场逐日股票池基线。
5. 财务报表与历史行业特征通过 `configs/presets/a_share_pit.yml` 显式开启。
6. 港股公开演示只作为暂停维护的外部参考，不进入活跃工作区依赖。

当前数据发布状态不等同于策略已经晋升。完整 PIT 路线仍需补齐研究窗口、基准、成本、
容量和最终样本外证据。

## 当前资产快照

权威状态来自 `$DATA_PLATFORM_ROOT/metadata/current_assets/a_share_current.json`。2026-07-16
核对结果如下：

| 资产 | 当前状态 | 覆盖与规模 |
| --- | --- | --- |
| `daily_clean` | 已发布 | 2015-01-05 至 2026-07-16，11,498,830 行，5,785 只证券 |
| `pit_fundamentals` | 已发布 | `a_share_top800_union_20150227_20260529_three_statement_pit`，清单查询区间为 1994-02-19 至 2026-06-15，252,643 行，6,292 只证券，隔离 8 行 |
| `industry_changes` | 已发布 | 申万 2021 三级行业，数据截至 2026-03-04，7,780 行，5,851 只证券 |
| `normalized_fundamentals` | 已发布 | `a_share_all_normalized_fundamentals_20260814`，latest alias 指向该快照，清单查询区间 20150101 至 20260815，911,680 行，7,620 只证券，`schema_version=normalized.v2` |

`pit_fundamentals` 已经可以由显式 PIT 预设消费。它的快照名称、查询区间和研究股票池
口径不同，使用时应读取清单，不要仅凭目录名推断覆盖范围。`normalized_fundamentals`
已作为合并快照发布，PIT 语义按 `fundamentals_vintages/vintage=20260815` 的 revision-safe
目录对齐，消费前读取清单核对覆盖范围。

## 数据发布状态与策略生产证据对账

数据资产发布（PIT 财务、历史行业、2015 年以来日线）不等于策略已经晋升到生产级。
策略生产证据由 `strategy-research/research/evidence/<策略id>.json` 承载，并经策略证据门禁校验。
截至 2026-08-17，A 股研究证据（`docs/evidence/a-share-*.json`）的真实状态如下，缺口需在
证据包 `known_gaps` 中显式登记，不得用数据发布状态替代：

| 证据项 | 真实状态 | 来源 |
| --- | --- | --- |
| PIT 财务（时间点） | 已发布但研究侧 `statement_features_enabled=false`，未全量启用 | `a-share-readiness-evidence-20260601.json` |
| 长窗口日线 | 已发布（至 2026-07-16） | current 契约 |
| 历史行业 membership | 已发布，但 `historical_backtest_enabled=false` | `a-share-readiness-evidence-20260601.json` |
| `normalized_fundamentals` | 已发布（`normalized.v2`，911,680 行，7,620 只） | current 契约 |
| 容量（capacity） | `pending`，待长窗口 PIT 资产与组合构建固定后生成 | `a-share-capacity-20260601.json` |
| 换手/成本（turnover/cost） | `pending`，长窗口压力证据缺失 | `a-share-turnover-cost-20260601.json` |
| 最终样本外（final OOS） | 书面替代（substitute），明确不构成生产级 | `a-share-final-oos-substitute-20260601.json` |
| 券商实盘（broker trading） | `operational_approval=false`，CN 文件 dry-run 不能证明 | `a-share-readiness-evidence-20260601.json` |

`strategy-pipeline` 的 `strategy capacity-report` 基于日线 pricing panel 与
`positions_by_rebalance.csv` 生成容量证据。该项与 turnover/cost 报告均仍为 `pending`，
是 `production_strategy_evidence` 就绪档的剩余阻塞项。

## A 股就绪度（readiness）分层

顶层只读命令按四档汇报状态：

```bash
python src/research_contracts/a_share_readiness.py \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --evidence-manifest /path/to/a_share_readiness_evidence.json \
  --pretty
```

| 就绪度 | 含义 |
| --- | --- |
| `baseline_reproducible` | 契约、registry、`daily_clean`、逐日股票池、研究输出、`targets.json` lineage 和 CN dry-run 证据齐全 |
| `complete_pit_research_data` | baseline 通过，并补齐 PIT 财务报表、历史行业 membership 和研究窗口覆盖 |
| `production_strategy_evidence` | 完整 PIT 数据通过，并补齐长窗口、benchmark、组合对称交叉验证（CPCV）、feature evidence、promotion gate、turnover/cost、capacity 和 side-aware 交易规则 |
| `broker_trading_enabled` | 执行系统另行证明券商 adapter、账户权限、受监督冒烟证据和操作批准，CN 文件 dry-run 无法自动证明这一档 |

旧键 `research_default_promotable` 保留为 `production_strategy_evidence` 的兼容 alias。
就绪度报告不会下载数据、运行训练或连接券商。它按契约、registry、研究产物和
执行证据判断状态。数据资产已发布后，仍需由证据清单证明各档就绪度。

### 当前入口与剩余工作

| 路线 | 当前入口 | 状态 |
| --- | --- | --- |
| 日频基线 | `strategy run --config default` | 已接入长窗口 `daily_clean`、日频估值和逐日股票池 |
| 迁移兼容入口 | `strategy run --config default_next` | 与 `default` 使用同一 A 股基线 |
| 显式 PIT 路线 | `strategy run --config configs/presets/a_share_pit.yml` | 可消费已发布 PIT 财务和历史行业资产，仍需完整研究证据 |
| 完整策略证据 | 就绪度的 `production_strategy_evidence` | 尚未因数据发布自动通过 |

生产策略 evidence 至少包含全 A 等权 benchmark、可获得时的指数族 cohort、feature evidence、
最终样本外（OOS）或书面替代说明、CPCV、turnover/cost、capacity 和压力窗口复核。候选未通过要求的
benchmark 时，不能描述成生产级策略。capacity evidence 由 `strategy-pipeline` 的
`strategy capacity-report` 基于日线 pricing panel 和 `positions_by_rebalance.csv` 生成。
顶层就绪度仍要求 `turnover_cost_report` 和 `capacity_report` 同时通过。

历史长窗口计划与限制记录已转为参考证据：

- [`evidence/a-share-long-window-evidence-plan-20260601.json`](evidence/a-share-long-window-evidence-plan-20260601.json)
- [`evidence/a-share-production-limitations-20260601.json`](evidence/a-share-production-limitations-20260601.json)
- 长窗口证据的生成步骤见 [`runbooks/a-share-long-window-evidence.md`](runbooks/a-share-long-window-evidence.md)。

### A 股 baseline 持仓建议验收

`baseline_reproducible` 可以解释为已能复现一版 A 股 baseline 持仓建议，但只能在完整
文件链路同时存在时成立：

```text
market-data-platform
  发布 metadata/current_assets/a_share_current.json、dataset_registry.csv、daily_clean、逐日股票池
alpha-research
  产出模型、稳健性、feature evidence 和 signals.parquet
portfolio-backtester
  消费信号和行情，产出回测、capacity、positions_current*.csv
strategy-pipeline
  编排研究流程，产出 summary.json、config.used.yml
  通过 strategy-pipeline export-targets 生成 targets.json 和 targets.json.lineage.json
quant-execution-engine
  读取 targets.json，完成 CN local dry-run 证据
```

`market-data-platform` 不训练模型、不选择持仓、不生成 `positions_current*.csv` 或
`targets.json`。CN local dry-run 只证明文件契约和基础执行计划可交接，不能推导
`broker_trading_enabled`。生产级 A 股策略还需通过 `production_strategy_evidence`。

## 1. 数据根目录审计

先设置共享数据根目录并运行顶层检查：

```bash
export DATA_PLATFORM_ROOT=/data/market-data-platform
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/workspace_doctor.py
UV_CACHE_DIR=/tmp/uv-cache uv run python src/research_contracts/smoke_contracts.py
```

需要确认：

- `metadata/frozen_markets/hk.json` 记录港股冷存储位置，或本次工作不涉及港股归档复现。
- `metadata/current_assets/a_share_current.json` 存在并指向已通过校验的资产。
- `metadata/dataset_registry.csv` 存在，必要时用 `marketdata registry build --artifacts-root "$DATA_PLATFORM_ROOT"` 重建。
- `metadata/current_assets/cn_current.json` 只作为历史兼容 alias，不能作为新的 A 股权威入口。

## 2. 港股归档冻结

中国香港市场数据资产按归档管理。出现明确资金、模拟盘、人工跟踪或跨市场验证需求后，
再恢复对应资产。2026-06-01 的冻结记录见
[中国香港市场归档](archive/hk/README.md)。私有归档仓库不加入子模块。

冻结或恢复前先查看命令与 registry：

```bash
marketdata migration freeze-hk --help
marketdata migration hydrate-hk --help

marketdata registry build \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --market a_share
```

先查看冻结计划，再显式执行：

```bash
marketdata migration freeze-hk \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --cold-root /data/market-data-platform-cold \
  --name hk-freeze-20260526 \
  --checksum sha256 \
  --json

marketdata migration freeze-hk \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --cold-root /data/market-data-platform-cold \
  --name hk-freeze-20260526 \
  --checksum sha256 \
  --apply
```

需要恢复时运行：

```bash
marketdata migration hydrate-hk \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --apply
```

## 3. A 股研究入口

先验证平台当前发布的 `daily_clean`：

```bash
marketdata tushare validate-a-share-daily-clean \
  --daily-clean-dir "$DATA_PLATFORM_ROOT/assets/tushare/a_share/daily/a_share_all_daily_clean_latest" \
  --require-valuation \
  --require-limit-status \
  --profile baseline \
  --out "$DATA_PLATFORM_ROOT/reports/a_share_daily_clean_validation.json"

marketdata contract build \
  --market a_share \
  --provider tushare \
  --artifacts-root "$DATA_PLATFORM_ROOT"

marketdata registry build \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --market a_share
```

研究侧验证日频主入口及其兼容别名：

```bash
cd strategy-pipeline
strategy run --config default
strategy run --config default_next
```

需要财务报表和历史行业特征时，显式运行：

```bash
strategy run --config configs/presets/a_share_pit.yml
```

检查运行产物中的 `config.used.yml`，至少应能看到：

- `market: a_share`
- `data.provider: tushare`
- `data.source_mode: platform_assets`
- `research_universe.mode: pit`
- `research_universe.require_by_date: true`
- `execution.market: a_share`

## 4. 执行 dry-run 证据

`strategy-pipeline export-targets` 导出的 A 股 `targets.json` 用于研究到执行的文件交接。进入执行
dry-run 前必须显式配置 CNY 到 USD 汇率，缺失汇率时执行侧应阻断。

```bash
export FX_CNY_USD=<rate>
qexec rebalance <targets.json> --broker <paper-broker>
```

顶层脚本不追加 `--execute`。实盘能力、券商账户权限和中国大陆市场报单能力由执行系统
单独验证。

## 5. 发布后检查

每次更新 current 契约后检查：

- `a_share_current.json` 和 `dataset_registry.csv` 可以稳定重建。
- `daily_clean` 质量门禁通过，覆盖行数、证券数、估值 overlay 和涨跌停标记符合预期。
- `default` 稳定产出 `summary.json`、`config.used.yml` 和持仓文件。
- `default_next` 与 `default` 保持同一 A 股基线路径。
- A 股 `targets.json` 通过执行引擎基础 dry-run。
- `a_share_pit.yml` 使用的 PIT 财务和行业资产与 current 契约、清单和 registry 一致。
- `normalized_fundamentals` 已发布为可消费资产，消费前按 current 契约和清单核对覆盖范围。

检查失败时，先修契约、质量门禁或研究入口。新增下载范围不能替代这些发布条件。
