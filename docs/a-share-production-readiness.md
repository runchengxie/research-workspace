# A 股生产 readiness 与长窗口扩展

A 股当前默认入口用于可复现 baseline 和跨仓库 contract 验收，不代表完整 PIT 数据、
生产策略证据或真实券商报单已经放行。顶层 readiness 按四档汇报：

| 状态 | 含义 |
| --- | --- |
| `baseline_reproducible` | current contract、registry、`daily_clean`、by-date universe、研究输出、targets lineage 和 CN dry-run 可复现 |
| `complete_pit_research_data` | PIT universe、财务报表 PIT、历史行业 membership 和研究窗口覆盖已完整 |
| `production_strategy_evidence` | 长窗口、benchmark ladder、feature evidence、最终 OOS 或替代说明、CPCV、turnover/cost 和 capacity 复核完成 |
| `broker_trading_enabled` | 执行仓库另行证明真实券商 adapter、账户权限、受监督 smoke、对账、kill switch 和操作批准 |

旧键 `research_default_promotable` 只保留为兼容 alias，对应
`production_strategy_evidence`。CN `targets.json` dry-run 不能推导 `broker_trading_enabled`。

## 长窗口扩展计划

| 阶段 | 覆盖目标 | Provider / entitlement | 刷新节奏 | 回滚点 |
| --- | --- | --- | --- | --- |
| baseline | `2024-02-29` 到 `2026-05-29`，全 A by-date universe | TuShare 日线类接口 | 日频增量，月度 contract review | 保留当前 `default` baseline 和已发布 alias |
| 长窗口日线 | 至少覆盖 10 年并跨多个市场阶段 | TuShare 日线、复权、估值、涨跌停；按 segment 可恢复下载 | 日频增量，季度全量 audit | latest alias 只在 validation 后更新 |
| 完整 PIT | 财报、预告、快报、分红、指标、审计、主营、披露日；历史行业 membership | 优先 VIP batch；non-VIP 只使用 spec 声明的安全 fallback | 财报窗口增量，季度 stale-window review | raw 可保留，normalized/PIT 未通过时不 publish |
| 策略证据 | 至少覆盖牛熊、震荡和流动性压力窗口 | 只读消费已发布 PIT 资产 | 候选变化时重跑 | default alias 可回滚，`default_next` 保留 A 股路径 |

## Benchmark ladder 与证据包

生产策略 evidence 至少包含：

1. 全 A 等权 benchmark。
2. 可获得时的 CSI 300、CSI 500、CSI 1000 等指数族 cohort。
3. Feature evidence、最终 OOS 或书面替代说明、CPCV。
4. Turnover、成本拖累、容量假设和压力窗口复核。
5. 候选不优于要求 benchmark 时，不能描述成 production-grade strategy。

`cross-sectional-trees/configs/experiments/sweeps/a_share__research_protocol_*.yml` 提供脚本化
入口。短窗口 promotion 只能说明 pipeline baseline 可运行，不能替代长窗口生产证据。
顶层 readiness manifest 还必须提供 `final_oos_or_substitute_report`、
`turnover_cost_report` 和 `capacity_report`。报告状态不是 `passed` 时，
`production_strategy_evidence` 必须保持未通过。
长窗口重跑顺序与产物要求见
[`evidence/a-share-long-window-evidence-plan-20260601.json`](evidence/a-share-long-window-evidence-plan-20260601.json)。

## 执行边界

真实 A 股报单由 `quant-execution-engine` 独立拥有。新增 broker adapter 时必须补账户权限、
市场订单约束、受监督提交 smoke、对账、kill switch 和显式操作批准。研究仓库只导出
`targets.json`，顶层脚本不追加 `--execute`。

2026-06-01 的剩余缺口记录见
[`evidence/a-share-production-limitations-20260601.json`](evidence/a-share-production-limitations-20260601.json)。
