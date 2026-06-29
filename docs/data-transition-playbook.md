# 数据迁移优先级 playbook

> status: active
> owner: workspace
> last_verified: 2026-06-29
> source_of_truth: yes
> superseded_by: n/a

本页解决什么：把冻结港股到冷存储、保持 A 股活跃根目录简洁、继续分阶段验证 A 股的当前决策落成可执行顺序。\
边界：`market-data-platform` 的数据下载运维手册、`alpha-research` / `portfolio-backtester` 的研究实现，以及 `strategy-pipeline` 的 A 股 baseline 编排 playbook 仍在各自子仓库维护。\
适合谁：准备维护 A 股活跃数据、冻结或恢复港股资产，或判断是否晋升 A 股研究入口的人。

## 当前决策

截至 2026-06-29，A 股中期窗口数据已发布，港股转入冷存储。工作区按以下边界维护：

1. 活跃 `DATA_PLATFORM_ROOT` 保留 A 股 contract、资产和 registry。
2. 中国香港市场资产冻结到独立冷存储，活跃根目录只保留 freeze marker。
3. 港股历史复现、跨市场对照或明确跟踪需求出现时，先显式 hydrate。
4. A 股 `default` 已经是当前主研究入口；现有 price-only 能力仍不能描述成完整 PIT 研究能力。
5. 港股公开演示只作为外部暂停维护的合成组合参考，不改变冷存储和恢复边界，也不成为活跃工作区依赖。

代码维护债按各子仓库治理清单继续推进。A 股 baseline 可以先行；把现有下载结果描述成成熟主线前，必须先补齐治理和证据。

## A 股 readiness 分层

顶层只读命令按四档汇报状态：

```bash
python src/research_contracts/a_share_readiness.py \\
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --evidence-manifest /path/to/a_share_readiness_evidence.json \
  --pretty
```

| 就绪度 | 含义 |
| --- | --- |
| `baseline_reproducible` | contract、registry、`daily_clean`、by-date universe、研究输出、`targets.json` lineage 和 CN dry-run 证据齐全 |
| `complete_pit_research_data` | baseline 通过，并补齐 PIT 财务报表、历史行业 membership 和研究窗口覆盖 |
| `production_strategy_evidence` | 完整 PIT 数据通过，并补齐长窗口、benchmark、CPCV、feature evidence、promotion gate、turnover/cost、capacity 和 side-aware 交易规则 |
| `broker_trading_enabled` | 执行系统另行证明券商 adapter、账户权限、受监督冒烟证据和操作批准；不能由 CN 文件 dry-run 自动推导 |

旧键 `research_default_promotable` 保留为 `production_strategy_evidence` 的兼容 alias。
readiness 报告不会下载数据、跑训练或连接券商。当前已发布的 A 股 `daily_clean` 中期窗口是
`2024-01-02` 到 `2026-05-29`；研究 preset 不应继续暗示已有 `2015-01-01` 起的完整资产。

### A 股长窗口扩展计划

| 阶段 | 覆盖目标 | Provider / entitlement | 回滚点 |
| --- | --- | --- | --- |
| baseline | `2024-02-29` 到 `2026-05-29`，全 A by-date universe | TuShare 日线类接口 | 保留当前 `default` baseline 和已发布 alias |
| 长窗口日线 | 至少覆盖 10 年并跨多个市场阶段 | TuShare 日线、复权、估值、涨跌停；按 segment 可恢复下载 | latest alias 只在 validation 后更新 |
| 完整 PIT | 财报、预告、快报、分红、指标、审计、主营、披露日和历史行业 membership | 优先 VIP batch；non-VIP 只使用 spec 声明的安全 fallback | raw 可保留，normalized/PIT 未通过时不 publish |
| 策略证据 | 至少覆盖牛熊、震荡和流动性压力窗口 | 只读消费已发布 PIT 资产 | `default` 是当前 A 股主入口，`default_next` 保留为兼容别名 |

生产策略 evidence 至少包含全 A 等权 benchmark、可获得时的指数族 cohort、feature evidence、
最终 OOS 或书面替代说明、CPCV、turnover/cost、capacity 和压力窗口复核。候选不优于要求
benchmark 时，不能描述成生产级策略。
capacity evidence 由 `strategy-pipeline` 的 `cstree capacity-report` 基于日线 pricing
panel 和 `positions_by_rebalance.csv` 生成；顶层 readiness 仍要求 `turnover_cost_report` 和
`capacity_report` 同时通过。

长窗口重跑顺序与产物要求见
[`evidence/a-share-long-window-evidence-plan-20260601.json`](evidence/a-share-long-window-evidence-plan-20260601.json)。
剩余缺口见
[`evidence/a-share-production-limitations-20260601.json`](evidence/a-share-production-limitations-20260601.json)。

### A 股 baseline 持仓建议验收

`baseline_reproducible` 可以解释为已能复现一版 A 股 baseline 持仓建议，但只能在完整
文件链路同时存在时成立：

```text
market-data-platform
  发布 metadata/current_assets/a_share_current.json、dataset_registry.csv、daily_clean、by-date universe
alpha-research
  产出模型、稳健性、feature evidence 和 signals.parquet
portfolio-backtester
  消费信号和行情，产出回测、capacity、positions_current*.csv
strategy-pipeline
  编排研究流程，产出 summary.json、config.used.yml
  通过 cstree export-targets 生成 targets.json 和 targets.json.lineage.json
quant-execution-engine
  读取 targets.json，完成 CN local dry-run 证据
```

`market-data-platform` 不训练模型、不选择持仓、不生成 `positions_current*.csv` 或
`targets.json`。CN local dry-run 只证明文件契约和基础执行计划可交接，不能推导
`broker_trading_enabled`。如果需要描述生产级 A 股策略，必须另行通过
`production_strategy_evidence`。

## 1. 数据根目录审计

先设置共享数据根目录并跑顶层检查：

```bash
export DATA_PLATFORM_ROOT=/data/market-data-platform
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/workspace_doctor.py
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/smoke_contracts.py
```

必须确认：

- `metadata/frozen_markets/hk.json` 明确记录港股冷存储位置，或本次完全不涉及港股归档复现。
- `metadata/current_assets/a_share_current.json` 存在，或明确记录 A 股还没有发布 current contract。
- `metadata/dataset_registry.csv` 存在，或计划用 `marketdata registry build --artifacts-root "$DATA_PLATFORM_ROOT"` 重建。
- 如果存在 `metadata/current_assets/cn_current.json`，只能作为历史兼容 alias 处理，不能作为新的 A 股权威入口。

## 2. 港股归档冻结

中国香港市场数据资产当前定位是 legacy / archival。除非存在明确资金、模拟盘、人工跟踪或跨市场验证需求，不应新增港股研究功能或扩大港股数据下载。

2026-06-01 的实际冻结记录见 [中国香港市场归档](archive/hk/README.md)。
真实业务代码如需进入私有暂停维护归档，先按
[中国香港市场归档](archive/hk/README.md) 中的私有归档门禁运行只读检查，并在工作区外准备暂存目录；
私有归档仓库不加入 submodule。港股 provider 生产面已从活跃 `market-data-platform` 主线删除；需要复现时从 freeze tag 或恢复专用归档恢复。

冻结或恢复前至少确认：

```bash
marketdata migration freeze-hk --help
marketdata migration hydrate-hk --help

marketdata registry build \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --market a_share
```

然后先查看 freeze 计划，再显式执行：

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

如果检查发现缺口，优先补齐 current contract、manifest、registry 和关键研究 run 的输入锁定文件，再考虑新的港股 sweep。需要恢复时运行：

```bash
marketdata migration hydrate-hk \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --apply
```

## 3. A 股 staged baseline

A 股 staged baseline 先把 price-only / `daily_clean` 路线跑稳；完整 PIT 研究能力需要补齐额外资产和证据后再描述。

数据平台侧先验证 `daily_clean`：

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

研究侧再验证当前主入口：

```bash
cd strategy-pipeline
cstree run --config default
```

`default_next` 仍可作为同一 A 股 preset 的兼容别名使用：

```bash
cstree run --config default_next
```

通过后检查 run 产物里的 `config.used.yml`，至少应能看到：

- `market: a_share`
- `data.provider: tushare`
- `data.source_mode: platform_assets`
- `research_universe.mode: pit`
- `research_universe.require_by_date: true`
- `execution.market: a_share`

## 4. 执行 dry-run 证据

`cstree export-targets` 能导出 A 股 `targets.json` 只说明研究到执行文件契约可交接。进入执行 dry-run 前必须显式配置 CNY 到 USD 汇率；缺失汇率时执行侧应阻断。

```bash
export FX_CNY_USD=<rate>
qexec rebalance <targets.json> --broker <paper-broker>
```

不要在顶层脚本里追加 `--execute`。实盘能力、券商账户权限和中国大陆市场报单能力必须由执行系统单独验证。

## 5. 何时扩大到 A 股完整数据

只有同时满足以下条件，才建议开始 A 股完整下载或把下载范围扩大到全市场长期窗口：

- `a_share_current.json` 和 `dataset_registry.csv` 已能稳定重建。
- `daily_clean` 质量门禁通过，并且覆盖行数、证券数、估值 overlay 和涨跌停标记符合预期。
- `default` 能稳定产出 `summary.json`、`config.used.yml` 和持仓文件；`default_next` 作为兼容别名应保持同一 A 股路径。
- A 股 `targets.json` 已通过执行引擎基础 dry-run。
- PIT fundamentals 和行业历史仍未补齐时，文档明确声明当前仍是
  price-only / `daily_clean` + full-market by-date PIT universe baseline。

如果任一条件不满足，优先修 contract、质量门禁或研究入口；更大规模下载不能替代边界缺口修复。
