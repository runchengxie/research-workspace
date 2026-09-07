# 执行现金台账归属清理实施计划

> 面向智能体执行者：必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`。每个 owner API 都使用 TDD。

目标：将历史执行成交的通用结算逻辑移动到 `portfolio-backtester`，同时将 strategy-research 的 VWAP 凭证便捷 API 保留为薄兼容门面。

架构：`portfolio-backtester` 负责与券商无关的组合会计和执行回放。因此，可复用的 `settle_execution_fills` 函数成为公开组合 API。`strategy-research` 保留 `settle_vwap_replay`，因为从 VWAP 凭证中选择一条研究资金路径属于研究专属编排，结算则委托给组合 owner。实时券商和订单状态逻辑不进入组合仓库。

规格：`docs/superpowers/specs/2026-08-30-cross-repo-boundary-cleanup-design.md`、归属矩阵和 strategy-research 清理章节。

## 任务 1：通过测试定义组合 owner 契约

仓库：`runchengxie/portfolio-backtester`

文件：
- Add: `tests/test_execution_ledger.py`
- Modify: `tests/test_package_smoke.py`

- [ ] 在生产代码前迁移现有 strategy-research 结算测试：
  - 费用、整手和次日卖出。
  - A 股 T+1 下当日买入不能卖出。
  - 现金不足时阻止买入。
  - 初始资金无效时失败关闭。
- [ ] 增加 package smoke 预期，检查 `portfolio_backtester.execution_ledger` 模块和顶层 `settle_execution_fills`。
- [ ] 运行针对性测试，确认由于 `main` 尚不存在模块和公开 API，测试处于 RED 状态。

## 任务 2：以最小范围实现组合 owner

仓库：`runchengxie/portfolio-backtester`

文件：
- Add: `src/portfolio_backtester/execution_ledger.py`
- Modify: `src/portfolio_backtester/__init__.py`

- [ ] 在不改变成交和标记列契约的前提下迁移当前通用 `settle_execution_fills` 语义：
  - input columns `trade_date`, `instrument_id`, `side`, `filled_notional`, `average_fill_price`;
  - marks `trade_date`, `instrument_id`, `price`;
  - sell proceeds can fund same-day buys;
  - same-day buys remain unavailable for sale (T+1);
  - buys respect round lots and available cash;
  - sells may use odd lots but cannot exceed opening inventory;
  - configurable buy/sell fee and stamp-tax bps;
  - output daily cash, holdings value, NAV, blocked shares/notional and fees.
- [ ] 不要将研究专属的 `settle_vwap_replay` 移入组合仓库。
- [ ] 在包根导出 `settle_execution_fills`。
- [ ] 运行针对性测试和 package smoke，预期为 GREEN。
- [ ] 在完整检出目录中运行仓库常规 lint、格式、类型检查、完整测试和可维护性门禁，再进入 Ready 或 Merge。

## 任务 3：精简 strategy-research 台账门面

仓库：`runchengxie/strategy-research`

依赖：先合并 portfolio provider PR。

文件：
- Modify: `src/style_factors/execution_cash_ledger.py`
- Modify: `tests/test_execution_cash_ledger.py`
- Add: `tests/test_execution_ledger_boundary.py`
- Modify: `pyproject.toml`
- Regenerate: `uv.lock`

- [ ] 增加 RED 边界测试，要求导入并委托给公开的 `portfolio_backtester.settle_execution_fills`，并禁止本地保留实现主体。
- [ ] 保留现有研究导入路径 `style_factors.execution_cash_ledger.settle_execution_fills` 作为委托给组合仓库的兼容门面。
- [ ] 保持 `settle_vwap_replay` 在本地。它按 `capital` 过滤研究 VWAP 凭证表，再调用委托的 owner 结算 API。
- [ ] 将组合依赖固定到已合并的 provider 提交，并重新生成 `uv.lock`。
- [ ] 现有行为测试必须保持不变并继续通过。

## 完成标准

- [ ] 通用历史成交结算在 `portfolio-backtester` 中只有一份规范实现。
- [ ] strategy-research 保留旧导入路径，但不再保留会计算法。
- [ ] `settle_vwap_replay` 继续由研究仓库负责，并委托给 owner。
- [ ] 实时券商和 execution-engine 职责不进入组合仓库。
- [ ] 消费者 PR 进入 Ready 前，provider-first 固定版本必须指向默认分支可访问的提交。
