# 代码体量复查与拆分建议

本页是盘点报告的落地产物，聚焦子模块内长文件的拆分判断。结论先说：活跃库源码（`src/`）整体可控，真正偏长的文件多数属于研究产物或运维脚本，不应作为常规重构目标。

## 数据口径

统计排除 `build/`、`tests/`、`.venv/`、`__pycache__/`（构建产物与测试不计入源码体量）。长文件按 600 行以上筛选。

## 关键发现

超大文件主要分布在两类非库目录：

- 任意 `artifacts` 目录：一次性研究实验脚本（如 `strategy-pipeline/artifacts/.../campaign.py` 约 1353 行、`research-apps/artifacts/.../weekly_lp_probe.py` 约 1039 行）。这些是带日期的研究产物，按 AGENTS.md 规则进入归档，不属于维护对象。
- 任意 `scripts/operations` 目录：运维操作脚本（如 `market-data-platform/scripts/operations/cutover_a_share_minute.py` 约 1460 行、`archive_guan_mobile.py` 约 994 行）。有明确操作语义，拆分收益低且易引入误操作风险。

活跃库源码 `src/` 下最长文件：

| 文件 | 行数 | 判断 |
| --- | --- | --- |
| `portfolio-backtester/src/portfolio_backtester/execution_sim/orders.py` | 1173 | 订单模型集合，可按订单类型拆子模块 |
| `portfolio-backtester/src/portfolio_backtester/execution_sim/core.py` | 820 | 执行模拟核心，可抽离撮合与成本核算 |
| `market-data-platform/src/market_data_platform/providers/tushare_a_share_mins.py` | 1090 | 数据提供方适配，可按抓取/清洗分段 |
| `alpha-research/src/alpha_research/_daily_watch20_features_calc.py` | 592 | 接近阈值，因子计算可分批 |

## 拆分建议（按性价比）

低优先级，且应落在各子仓库自治范围，顶层不越界改子模块代码：

1. `portfolio-backtester/execution_sim/orders.py` 与 `core.py` 是最值得拆的库源码。订单模型与执行核心耦合度高，拆分能改善可读性与测试隔离，且不改变对外契约。
2. `market-data-platform/providers/tushare_a_share_mins.py` 可按抓取、校验、写入分段，但涉及数据正确性，需配套回归测试。
3. `artifacts/` 与 `scripts/operations/` 下的长文件保持原状。它们要么是研究记录、要么是带风险的操作脚本，重构会损害可追溯性或增加误操作面。

## 与治理机制的关系

维护性预算棘轮（`maintainability-refactor-roadmap.yml`）已覆盖 `src/style_factors` 等顶层包。子模块内的长文件若进入拆分，应同步在各仓的维护性基线里下调预算，沿用现有的"同一提交下调、独立决策上调"规则。当前子模块长文件未触发顶层门禁，因此不阻塞发布。

## 不做的事

- 不重写 `artifacts/` 历史研究脚本（属归档，保持原貌）。
- 不拆分 `scripts/operations/` 运维脚本（操作风险大于收益）。
- 顶层仓库不直接修改子模块 `src/` 代码，仅在此给出建议，由对应子仓库 owner 决策执行。
