# A 股生产就绪度与长窗口扩展

> status: superseded
> owner: workspace
> last_verified: 2026-06-10
> source_of_truth: no
> superseded_by: data-transition-playbook.md#a-股-readiness-分层

本页保留给旧链接。当前权威入口已经并入
[数据迁移优先级 playbook](data-transition-playbook.md#a-股-readiness-分层)。

## 当前口径

顶层就绪度仍分四档：

| 状态 | 含义 |
| --- | --- |
| `baseline_reproducible` | current contract、registry、`daily_clean`、by-date universe、研究输出、targets lineage 和 CN dry-run 可复现 |
| `complete_pit_research_data` | PIT universe、财务报表 PIT、历史行业 membership 和研究窗口覆盖已完整 |
| `production_strategy_evidence` | 长窗口、benchmark ladder、feature evidence、最终 OOS 或替代说明、CPCV、turnover/cost 和 capacity 复核完成 |
| `broker_trading_enabled` | 执行仓库另行证明真实券商 adapter、账户权限、受监督 smoke、对账、kill switch 和操作批准 |

旧键 `research_default_promotable` 只保留为兼容 alias，对应
`production_strategy_evidence`。CN `targets.json` dry-run 不能推导 `broker_trading_enabled`。

## 证据入口

- 长窗口重跑顺序与产物要求：
  [`evidence/a-share-long-window-evidence-plan-20260601.json`](evidence/a-share-long-window-evidence-plan-20260601.json)
- 剩余缺口：
  [`evidence/a-share-production-limitations-20260601.json`](evidence/a-share-production-limitations-20260601.json)
