# 数据迁移优先级 playbook

本页解决什么：把“先审计共享数据根目录、再冻结港股、再分阶段验证 A 股”的当前决策落成可执行顺序。\
本页不解决什么：不替代 `market-data-platform` 的数据下载运维手册，也不替代 `cross-sectional-trees` 的 A 股 baseline playbook。\
适合谁：准备判断是否下载 A 股完整数据、是否先归档港股资产，或是否应先处理代码维护债的人。

## 当前决策

当前不建议直接开始 A 股完整数据下载。工作区应先完成：

1. 审计 `DATA_PLATFORM_ROOT`，确认 current contract 和 registry 的真实状态。
2. 补齐中国香港市场 legacy / archival 数据资产的冻结证据。
3. 用 A 股 staged baseline 验证 `daily_clean`、`a_share_current.json` 和 `default_next`。
4. 只有 staged baseline 稳定后，才扩大到 A 股完整数据范围。

代码维护债应继续按各子仓库治理清单推进，但不应阻塞小范围 A 股 baseline；它会阻塞的是“把完整下载结果包装成已成熟主线”的判断。

## 1. 数据根目录审计

先设置共享数据根目录并跑顶层检查：

```bash
export DATA_PLATFORM_ROOT=/data/market-data-platform
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/workspace_doctor.py
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/smoke_contracts.py
```

必须确认：

- `metadata/current_assets/hk_current.json` 存在，或明确记录为什么本轮不验证港股。
- `metadata/current_assets/a_share_current.json` 存在，或明确记录 A 股还没有发布 current contract。
- `metadata/dataset_registry.csv` 存在，或计划用 `marketdata registry build --artifacts-root "$DATA_PLATFORM_ROOT"` 重建。
- 如果存在 `metadata/current_assets/cn_current.json`，只能作为历史兼容 alias 处理，不能作为新的 A 股权威入口。

## 2. 港股归档冻结

中国香港市场数据资产当前定位是 legacy / archival。除非存在明确资金、模拟盘、人工跟踪或跨市场验证需求，不应新增港股研究功能或扩大港股数据下载。

归档前至少确认：

```bash
marketdata rqdata inspect-hk-current \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --fail-on-severity warning

marketdata registry build \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --market all
```

如果检查发现缺口，优先补齐 current contract、manifest、registry 和关键研究 run 的输入锁定文件；不要先开始新的港股 sweep。

## 3. A 股 staged baseline

A 股 staged baseline 只要求先把 price-only / `daily_clean` 路线跑稳，不把它写成完整 PIT 研究能力。

数据平台侧先验证 `daily_clean`：

```bash
marketdata tushare validate-a-share-daily-clean \
  --daily-clean-dir "$DATA_PLATFORM_ROOT/assets/tushare/a_share/daily/a_share_all_daily_clean_latest" \
  --require-valuation \
  --require-limit-status

marketdata contract build \
  --market a_share \
  --provider tushare \
  --artifacts-root "$DATA_PLATFORM_ROOT"

marketdata registry build \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --market all
```

研究侧再验证迁移候选入口：

```bash
cd cross-sectional-trees
cstree run --config default_next
```

通过后检查 run 产物里的 `config.used.yml`，至少应能看到：

- `market: a_share`
- `data.provider: tushare`
- `data.source_mode: platform_assets`
- `research_universe.mode: static`
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
- `default_next` 能稳定产出 `summary.json`、`config.used.yml` 和持仓文件。
- A 股 `targets.json` 已通过执行引擎基础 dry-run。
- PIT universe、PIT fundamentals 和行业历史仍未补齐时，文档明确声明当前仍是 price-only / static-universe baseline。

如果任一条件不满足，优先修 contract、质量门禁或研究入口；不要用更大规模下载掩盖边界缺口。
