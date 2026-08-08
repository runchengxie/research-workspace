# A 股风格因子 2015–2026 约束稳健性附录

> status: superseded
> owner: workspace
> last_verified: 2026-08-02
> source_of_truth: no
> superseded_by: docs/style-factor-constrained-robustness-2008-2026.md

> 研究状态：screen-grade constrained sensitivity。本文不替换 2008–2026 raw 长历史报告，
> 也不触发共享数据目录的正式 `latest` 发布。
> 2026-08-02 起由[全历史约束稳健性附录](style-factor-constrained-robustness-2008-2026.md)
> 接替。本文仅保留为 P0 历史快照。

## 研究问题

本附录在每个因子的共同暴露交易日内，对照以下三个口径：

- `raw/gross`：2026-08-01 全量 raw 运行的共同窗口收益。
- `constrained/gross`：改用 `daily_clean`、PIT 形成日股票池和交易约束，不扣成本。
- `constrained/net`：在 constrained/gross 上按多空两腿实际成交名义额扣 10 bps 成本。

目标是检查原风格结论是否依赖股票池、上市天数、ST、涨跌停、停牌、退市和换手处理，
不是为现有结果追加一个更乐观的回测版本。

## 数据覆盖与质量

| 数据 | 覆盖 | 规模 | 本次处理 |
| --- | --- | --- | --- |
| `daily_clean` | 2015-01-05 至 2026-07-31 | 11,559,606 行、5,792 只证券 | 主价格、估值和交易约束入口，`trade_date + symbol` 无重复 |
| `universe_by_date` | 2015-02-27 至 2026-07-31 | 567,904 行、138 个形成日 | 只在形成日过滤，不能称为逐日股票池 |
| `stock_st` | 2022-01-04 至 2026-07-30 | 169,524 行、601 只证券 | 只使用精确日期记录，覆盖前日期保持未知 |
| instruments | 截至 2026-07-31 | 5,853 只证券、327 只有退市日期 | 用退市日期触发末端收益压力情景 |
| `limit_status` | 2015-01-05 至 2026-07-31 | 经 `daily_clean` overlay 消费 | 使用 `is_limit_up`、`is_limit_down` 控制订单 |

`daily_clean.is_st` 来自 latest instruments snapshot，属于非 PIT 标记，本次没有用它回填历史。
形成日过滤共识别 12,908 个上市不足 180 天的股票月观察和 7,844 个已有逐日证据的 ST
股票月观察。当前 `universe_by_date` 只具备形成日快照语义，不具备逐日股票池语义，文档和
metadata 均保留这一边界。

## 执行与成本逻辑

- 月末收盘形成信号，下一市场交易日收盘开始尝试调仓。成交仓位从后续收盘到收盘区间开始计算收益，避免用当日收盘涨跌停状态决定成交后又取得同日收益。
- 多头涨停不能买、跌停不能卖，空头代理跌停不能开、涨停不能回补。
- 缺少当日行情视为停牌或不可交易。未完成订单逐日重试，直到成交或被下一次调仓覆盖。
- 持有期间缺失价格继续冻结资本。样本内退市在退市日映射到可配置末端收益，计价后移除仓位。
- 默认退市末端收益为 `-50%`，另测 `-30%` 和 `-100%`。
- 成本按多空两腿实际成交名义额扣除，压力情景为 0、10、20、30 bps。
- 空头腿仍是 bottom quintile 理论代理。涨跌停规则只改善成交约束，不能替代真实券源、费率和召回历史。

## 核心结果

| 因子 | 共同观察日 | raw/gross 年化% | constrained/gross 年化% | constrained/net 年化% | net-raw 百分点 | net 最大回撤% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Size 大市值 | 2,778 | -21.56 | -15.86 | -16.33 | +5.23 | -86.98 |
| Value 低估值 | 2,778 | +11.87 | +7.62 | +6.90 | -4.97 | -18.33 |
| Momentum 动量 | 2,778 | -12.02 | -15.40 | -18.55 | -6.53 | -89.70 |
| Quality 复合质量 | 2,778 | +7.32 | -0.58 | -1.30 | -8.62 | -31.46 |
| Earnings Yield 盈利估值 | 2,778 | +8.48 | +2.52 | +1.74 | -6.74 | -27.36 |
| LowVol 低波动 | 2,778 | +12.47 | +6.27 | +3.38 | -9.09 | -38.63 |
| Growth 成长 | 2,778 | +9.28 | +2.54 | +1.66 | -7.62 | -26.44 |
| Leverage 低杠杆 | 2,778 | +1.95 | -1.16 | -1.61 | -3.56 | -32.49 |
| Beta 低贝塔 | 2,671 | -4.06 | -5.83 | -6.68 | -2.62 | -62.57 |
| Liquidity 低换手 | 2,778 | +29.44 | +13.58 | +10.97 | -18.47 | -18.12 |
| LiquidityFlow 大单资金流 | 96 | +3.93 | -0.76 | -4.55 | -8.48 | -3.86 |
| ChipConcentration 筹码集中度 | 854 | +3.01 | +8.15 | +5.02 | +2.01 | -15.81 |
| InstitutionHolding 机构持仓 | 833 | +6.07 | +7.64 | +4.57 | -1.50 | -14.53 |
| DividendYield 股息率 | 2,778 | +6.91 | +4.69 | +3.85 | -3.06 | -18.82 |
| PSValue 市销率价值 | 2,778 | +6.43 | +3.44 | +2.90 | -3.53 | -19.59 |

共同观察日按 raw 与 constrained 都有实际暴露的日期取交集。LiquidityFlow、
ChipConcentration 和 InstitutionHolding 覆盖稀疏，不能把其观察日理解为连续 11 年。

## 解读

Value 和 Liquidity 在约束与 10 bps 成本后仍保持正收益，但强度明显下降。Value 几何年化从
`+11.87%` 降到 `+6.90%`，最大回撤从 `-15.89%` 扩大到 `-18.33%`。Liquidity 从
`+29.44%` 降到 `+10.97%`。成本提高到 30 bps 后为 `+5.92%`，说明原始强度明显依赖
股票池和交易假设，不能直接按 headline alpha 使用。

Quality 和 Leverage 在 constrained/net 下转负。Earnings Yield、LowVol、Growth、
DividendYield 和 PSValue 仍为正，但相对 raw 都明显衰减。Size 仍显著为负，Momentum 更差，
说明 A 股历史小市值和反转代理没有因约束消失，同时其回撤和真实空头可实现性仍不合格。

辅助因子的共同观察日较少。LiquidityFlow 转负，ChipConcentration 与 InstitutionHolding
为正，但目前只适合数据覆盖和机制研究，不能与 2,778 日的核心因子横向排名。

## 可复现运行

先生成或指定一份完整 raw/gross 风格因子产物，再运行：

```bash
DATA_PLATFORM_ROOT=/path/to/market-data-platform \
  uv run python -m src.style_factors.robustness \
  --baseline-artifacts /path/to/full-raw-artifacts \
  --outdir /tmp/style-factor-robustness \
  --min-listed-days 180 \
  --transaction-cost-bps 10 \
  --delist-terminal-return -0.5
```

输出包含完整对照、压力情景、诊断、30 条 constrained gross/net 日收益序列、Markdown
报告和对照图。该命令只写 `--outdir`，不会更新共享 `latest`。

## 后续数据批次

### P1：早期交易约束与历史 ST

下一轮应在 `market-data-platform` 独立完成并单独发布数据资产：

1. 所有 TuShare 请求固定经 `https://fast.xiaodefa.cn`，凭证只从本地 15,000 积分账户环境变量读取。
2. 回填 2008–2014 `adj_factor` 与 `stk_limit`，按交易日核对 daily 覆盖、唯一键和空分区。
3. 分页摄取 `namechange`，保存原始记录和请求 receipt，根据名称生效区间重建 ST 状态。
4. 用 2022 年后的 `stock_st` 做日期级交叉验证，未通过覆盖率和冲突率门禁前不进入 constrained 主口径。
5. 摄取 `margin_secs` 作为融券资格上界，并在 schema 中明确它不代表券源、费率或可借数量。

`namechange` 单次查询会触及 10,000 行上限，必须实现分页、去重、断点续跑和完整性 receipt，
不能用一次无分页请求冒充历史全量。

### P2：revision-safe PIT v2

PIT v2 从现在开始保存不可变观测版本，至少包含：

- `symbol`、报告期、报表类型、字段名和披露日。
- `available_date`、`source_retrieved_at`、observation vintage 和 revision 序号。
- 原始行 hash、请求 ID、源文件 hash 与上游 snapshot ID。
- 字段级 revision coverage、freshness 验证结果和 quarantine 原因。

2026 年取得的历史数据只能发布为 `reconstructed_pit`。只有持续归档产生的真实历史观测版本
才能标为 `revision_safe_pit_v2`。PIT v2 未满足 revision coverage、freshness 和
`source_retrieved_at <= as_of_date` 前，不允许 constrained 附录升级为 decision-grade。

## 晋升条件

正式 `latest` 至少需要同时满足：

- 2008 年以来的 clean/limit/adjustment 覆盖和质量报告通过。
- 历史 ST 区间完成并通过 2022 年后交叉验证。
- 退市整理期或现金清算收益有可信来源，不再只用压力代理。
- 多空收益在合理成本、涨跌停和券源约束下方向稳定。
- fundamentals 通过 revision-safe PIT v2 的 as-of loader 和字段级 provenance 门禁。

在此之前，三份现有长历史报告继续保留 screen-grade 标记和原 headline 数字。
