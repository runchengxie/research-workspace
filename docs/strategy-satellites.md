# 外部策略项目接入

> status: reference
> owner: workspace
> last_verified: 2026-07-19
> source_of_truth: no
> superseded_by: n/a

`research-workspace` 锁定六个核心子模块，其中 `research-apps` 承载工作区内研究应用。
热点候选、AI 重排和共享 A 股因子的外部输入目前由
独立的 `market-intel` 仓库维护。外部项目通过版本化文件接入，业务实现和运行命令以
`market-intel` 自身文档为准。

## 当前项目

| 项目 | 所有者 | 交接产物 | 在本工作区的用途 |
| --- | --- | --- | --- |
| `hot-sector-screener` | `market-intel` | `candidate_universe.json`、`signals.parquet` 和 lineage | 热点候选池、Numeric 排名和历史 challenger 输入 |
| `ai-stock-picker` | `market-intel` | `selection.json`、Prompt 与响应 sidecar、投递或观察 receipt | DeepSeek shadow、稳定性实验和风险诊断 |
| `a-share-factor-core` | `market-intel` | 由 owner 项目内部消费 | 共享因子实现，不作为本工作区公开依赖 |

Guan 与 TuShare 分钟数据由 `market-data-platform` 统一发布。研究代码读取已发布资产和
来源标识，不直接调用供应商下载接口。

## 文件流向

```text
hot-sector-screener
  candidate_universe.json + signals.parquet + lineage
        ↓
strategy-pipeline
  历史 challenger 或 append-only AI shadow
        ↓
portfolio-backtester / staggered execution
  成本、现金、涨跌停、停牌和卖出 carry 审计
```

AI 选择还要保存准确 Prompt、原始响应、模型标识、代码版本、哈希和 `available_at`。
缺少这些正文时，只能保留为 retrospective 或 tombstone，不能补写成 样本外（OOS）。

## 接入规则

- `research-workspace` 不通过 `PYTHONPATH` 导入外部项目源码。
- 候选池、信号和选择结果必须携带观察日期、生成时间、文件哈希和证据限制。
- `strategy-pipeline` 负责统计验证和组合执行，外部项目负责候选生成和 provider 调用。
- 历史重建保留真实生成时间，并标记为 `post_observation_generation`。
- 未来 OOS shadow 在 T 日收盘后、T+1 开盘前完成 append-only 冻结。错过日期保持缺失。
- DeepSeek 当前只适合受保护分数带内的 tie-break 或语义风险 veto。

顶层 `scripts/path_b_production.py`、`scripts/concept_etf_ml_backtest.py` 和
`scripts/path_c_m1_validate.py` 属于旧探索入口，不代表当前接入方式。它们的保留或移除
由 `docs/script-lifecycle.yml` 和维护性治理记录决定。
