# 热点板块 真正 3/5 日调仓诊断（2026-07-18）

## 结论

真正的每 3 个交易日调仓并没有自然解决换手：Numeric v2 Top10 每次调仓的名称换手仍为
98.32%，按 3 个交易日摊销为 32.77%/日。B15/E8 只把每次名称换手降至 98.02%，
`relevance=0.01` margin 没有进一步变化。

`每次最多新增 2 只 + carry` 在数学上达到了每次名称换手 20%、target full-L1 40%、
half-L1 20%，也没有产生超过 10 只的权重长尾。但组合平均 7.41/10 只已经不在当前候选池。
因此本轮没有可晋级的低换手方案。carry arm 收益较少为负不能视为改进证据，因为它主要改变了
持仓资格，变成大量持有过期候选。

本结果是事后观测的回顾性诊断（post-observation retrospective diagnostic），不是时点（PIT）/样本外（OOS），也不能授权实盘晋级（live promotion）。

## 实验口径

- 输入固定为 Numeric v2 回放的 Top30 候选与 `numeric_v2_rank`，窗口为 2026-01-15 至
  2026-06-29，共 107 个连续、价格日历可核验的交易日。冻结价格显示 2026-06-30 至
  2026-07-02 是交易日，但上游没有对应 ranking snapshot。本实验没有把缺失信号伪装成休市，
  也没有回填，因此在缺口前截断。
- 3 日实验完整检查 phase 0/1/2，5 日敏感性完整检查 phase 0–4。
- 信号在 T 收盘，T+1 `adj_open` 入场，持有到下一次 schedule 调仓，不使用每日 sleeve。
- 等权 Top10，单边成本 20 bps。
- 排序继续使用 Numeric v2，0.01 margin 单独使用 0–1 的 `candidate_relevance`。
- 固定 Top10 的最多替换 2 只已天然产生 full-L1 0.40，没有再叠加权重插值。
- 候选消失默认退出，只有名称上限 arm 显式使用 carry 补足 Top10。

## 主要结果

| Arm | phase均值收益 | 每次名称换手 | 日摊销名称换手 | target full-L1 | pretrade full-L1 | 平均过期候选 |
|---|---:|---:|---:|---:|---:|---:|
| 3日基线/退出 | -18.10% | 98.32% | 32.77% | 196.64% | 196.65% | 0.00/10 |
| 3日 B15/E8/退出 | -18.97% | 98.02% | 32.67% | 196.04% | 196.06% | 0.00/10 |
| 3日 B15/E8 + margin/退出 | -18.97% | 98.02% | 32.67% | 196.04% | 196.06% | 0.00/10 |
| 3日 + max-new2/carry | -8.03% | 20.00% | 6.67% | 40.00% | 43.46% | 7.41/10 |
| 5日基线/退出 | -21.69% | 98.04% | 19.61% | 196.07% | 196.10% | 0.00/10 |
| 5日 + max-new2/carry | -8.74% | 20.00% | 4.00% | 40.00% | 44.24% | 7.35/10 |

收益是各 schedule phase 的总收益均值。所有 arm 仍为负收益。名称与 target 权重指标排除初始建仓，
pretrade 指价格漂移后的调仓需求。

## 四层换手语义

组合 owner 现在分别输出：

1. 名称层：进入、退出、重合的 symbols/counts 与 `target_name_turnover`。
2. 目标权重层：`target_weight_full_l1` / `target_weight_half_l1`。
3. 漂移后需求层：pretrade buy/sell/full-L1/half-L1。
4. 实际执行层：executed buy/sell/full-L1/half-L1/cost，`executed_gross` 是 full-L1
   的兼容别名。

本次使用的是分数回测，没有真实订单或 fill，所以第 4 层明确为 null，
`execution_data_available=false`。20 bps 是模型成本，不冒充实际成交成本。

## 判断与下一步

已观察事实：当前候选池跨 3/5 日几乎完全换新，单纯 rank buffer 与小 margin 不足以形成滞回。
max-new2 只有靠持有大量已离开候选池的股票才能保持满仓。

由此推断，下一步不应继续调 buffer 或容忍无限 carry，而应让上期持仓进入一个更宽的、每日更新的
可交易资格池，并使用当日特征重新评分。只有重新评分后仍合格的旧股才允许滞回，否则退出。
如果退出后信号不足，需另建能够真实表达现金的执行器，再测试弱信号持币，不能在当前全仓归一化
模型中伪造现金。

## 证据与复现

冻结 spec：
`src/strategy_pipeline/campaign_specs/hotsector_low_turnover_retrospective_20260718.json`。

复现入口：
`scripts/research/hotsector_low_turnover_retrospective.py`。

本地 `create-once` 产物：
`artifacts/research/hotsector_low_turnover_retrospective/run_20260718_v5_calendar_complete_turnover_layers`。该目录包含全部 phase、
period、target holdings、过期候选标记、四层换手字段、report 与 receipt，发布器拒绝覆盖已有目录。
本地产物仍受 `artifacts/` ignore 规则管理，跨机器恢复需要后续 control-plane 制品注册表（artifact registry）。
