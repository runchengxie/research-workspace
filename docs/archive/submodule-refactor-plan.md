# 子模块巨型文件拆分方案

> status: archived
> owner: workspace
> last_verified: 2026-08-17
> source_of_truth: no
> superseded_by: ../maintainability-governance.md

本页保留当时的拆分设计，其中部分文件已经完成拆分。当前热点、预算和优先级以[维护性治理](../maintainability-governance.md)、`maintainability-refactor-roadmap.yml` 和[工作区路线图](../roadmap.md)为准。

本页是盘点报告里「子模块巨型文件拆分」的落地设计。当前先给出方案，执行前需各子仓 owner 确认。拆分原则是保持对外契约不变、配套回归测试、同步维护性预算。

## 现状核实

实测子模块超长文件分三类：

| 类别 | 例子 | 是否本方案范围 |
| --- | --- | --- |
| 研究产物 `artifacts/` | `strategy-pipeline/artifacts/.../campaign.py` 约 1353 行 | 不在范围（带日期的历史证据，保持原貌） |
| 运维脚本 `scripts/operations/` | `market-data-platform/scripts/operations/cutover_a_share_minute.py` 约 1460 行 | 不在范围（操作风险大于收益，改动易引入误操作） |
| 库源码 `src/` | `portfolio-backtester/execution_sim/orders.py` 1173 行、`core.py` 820 行，`market-data-platform/providers/tushare_a_share_mins.py` 1090 行 | 在范围 |

重要事实：`portfolio-backtester/execution_sim/orders.py` 与 `core.py` 是 2026-07-29 刚从 2393 行的 `core.py` 拆出的结果（见 `maintainability-refactor-roadmap.yml` 第 111、769 行）。子模块拆分本身已在项目节奏中推进，受 ratchet 严格约束，不宜在顶层仓冒进重复拆。

## 对外契约约束

`portfolio-backtester/execution_sim/__init__.py` 以包级 `from .core import (...)` 和 `from .orders import (...)` 重新导出公开符号，内部为 `_` 私有函数。因此把 `orders.py` 的私有函数按主题拆到 `orders_buy.py`、`orders_nav.py`、`orders_ideal.py` 等子模块，只要 `__init__.py` 的导出不变，对外契约零影响。这是风险最低、收益明确的拆分。

## 建议的拆分步骤

1. portfolio-backtester/execution_sim（低风险，先执行）
   - `orders.py` 按主题拆为：`orders_construct.py`（目标权重与理想再平衡订单构造）、`orders_nav.py`（NAV 多日订单推进与状态机）、`orders_ideal.py`（理想日频 NAV 执行）。
   - `core.py` 已按 `models/capacity/orders/reporting` 思路在 7-29 接收拆分，进一步可按 `simulate_capacity_execution` / `simulate_execution_adjusted_nav` / `simulate_ideal_daily_nav` 三段拆到 `core_capacity.py`、`core_adjusted_nav.py`、`core_ideal_nav.py`。
   - 每拆一步，跑 `portfolio-backtester` 的 `test_execution_sim.py` 等回归，并刷新该仓维护性基线（若未超阈值则只刷新快照，超阈值则同一提交下调 budget）。

2. market-data-platform/providers/tushare_a_share_mins.py（中风险，后执行）
   - 按抓取、校验、写入三段拆到 `tushare_a_share_mins_fetch.py`、`_validate.py`、`_write.py`。
   - 涉及数据正确性，需配套数据回归（核对既有 current 契约产物字节一致）。

## 不在本方案范围

- `artifacts/` 研究产物与 `scripts/operations/` 运维脚本：保持原状，理由是可追溯性与操作风险。
- 顶层仓库 `src/`、`scripts/`：已在前面任务中治理（doctor 加漂移检查、check.sh 入口）。

## 执行门槛

每个子模块拆分需在对应子仓内完成检查与测试，再更新顶层 gitlink。跨子仓改动不越界到顶层直接改子模块源码之外的治理文件，除非预算变化需同步 roadmap。
