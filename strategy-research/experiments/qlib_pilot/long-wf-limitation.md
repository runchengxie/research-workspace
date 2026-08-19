# 长验证期回测（a_share）限制发现

> 日期：2026-08-09
> 配置：a_share_long_wf.yml（extends a_share，walk_forward test_size 0.4）

## 目的

把 a_share walk-forward 验证期拉长到 ~12 个月，验证实验（explore_valid_window）
显示 12 个月验证 OOS IC 0.10 优于 3 个月 0.06。

## 结果（回测崩溃）

- train_dates=14, test_dates=5（验证期未变长，仍是 5 个月度）
- walk_forward 请求 3 窗口只 fit 2（test_size 0.4 太大）
- 触发 alpha_research walk-forward 下游错误，回测中断
- 回测前段显示的结果（Sharpe 0.54, NAV -0.19%）仍是旧配置（test_size 未生效）

## 根因

a_share 数据窗只有约 27 个月（2024-02 到 2026-05）。test_size 0.4 想给 ~11 个月
验证，但 walk_forward 锚定末端 + 3 窗口时数据不够，只 fit 2 窗口且验证期仍被
压缩到 5 个月度。

## 结论

1. 验证期实验证明 12 个月验证 OOS IC 0.10 可靠（模型信号层面）。
2. 但 a_share 生产回测的 walk_forward 结构（3 窗口锚定末端）在 27 个月数据窗下
   不支持长验证期，参数不匹配导致崩溃。
3. 这不是方向错，而是数据窗长度与 walk_forward 窗口数的约束。

## 可选后续

- 扩展数据窗（start 提前到 2022 或更早），给长验证期留空间。
- 或降低 n_windows（如 2 窗口）配合长验证期。
- 或用 experiments 的滚动窗口框架做长验证期评估（已证明可行，不经生产回测）。
