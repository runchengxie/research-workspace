# 热点板块 Numeric v2 回顾性 challenger 结果（2026-07-17）

## 结论

Numeric v2 在同一份 2026-01-15 至 2026-07-15 历史回放中改善了原 Numeric，尤其是
H3。但所有执行单元仍为负收益，H1 也没有超过候选池 Top30 等权基准。固定的
Buffer15 只把 v2 名称换手降低 1.48 个百分点，仍高于原 Numeric。因此该版本不进入
自动晋级，也没有足够证据进入新的 OOS 影子分配。

本结果属于事后观测的回顾性历史回放（`post_observation_retrospective_historical_replay`）：候选在观察日之后重建，评分
假设也在看过旧回放后提出。它既非时点（PIT）也非样本外（OOS），不可用于实盘晋级（live promotion）。

## 冻结假设

- 先按原 `candidate_relevance`、`candidate_score`、symbol 选出 Top30 主题相关候选。
- 在 Top30 内使用唯一一组固定权重：relevance 10%、daily confirmation 30%、盘中稳定性
  20%、流动性 25%、趋势 15%。
- 对 `ret_5d > 12%`、`ret_10d > 20%`、`amount_ratio_20d > 3` 做单调分段惩罚，并对
  接近 20 日高点且 5 日过热增加交互惩罚。
- `NUMERIC_V2_BUFFER15` 仅保留当前 v2 排名仍在前 15 名的昨日持仓，再按当日 v2 排名补足
  Top10，没有扫描 buffer 或权重。
- T 日收盘信号、T+1 开盘执行，H1/H3/H5，单边 10/20/50 bps，涨跌停、停牌和终端
  carry buffer 与原 challenger 完全相同。

完整合同位于
`src/strategy_pipeline/campaign_specs/hotsector_numeric_v2_retrospective_20260717.json`。

## 20 bps 主结果

| Variant | H1收益 | H1 Sharpe | H1 MDD | H3收益 | H3 Sharpe | H5收益 | H5 Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|
| NUMERIC | -62.84% | -4.32 | -65.81% | -36.57% | -2.25 | -27.23% | -1.73 |
| CANDIDATE_POOL_EQW | -58.61% | -4.73 | -61.14% | -31.01% | -2.23 | -27.17% | -2.04 |
| NUMERIC_V2 | -59.30% | -4.61 | -60.26% | -25.66% | -1.70 | -26.56% | -1.92 |
| NUMERIC_V2_BUFFER15 | -58.22% | -4.51 | -59.20% | -24.21% | -1.55 | -26.17% | -1.85 |

10/20/50 bps 的所有 variant × horizon 结果都为负。完整网格在
`execution_metrics.parquet`，没有根据收益选择成本、持有期或参数。

## 主动收益与稳定性

20 bps 下，v2 相对原 Numeric 的平均日主动收益为 H1 +6.50 bps、H3 +12.57 bps、
H5 +0.28 bps，Buffer15 分别为 +8.67、+14.27、+0.79 bps。但置信区间均跨零。
对应年化信息比率分别为 0.55、1.80、0.06（Buffer15 为 0.74、2.06、0.17）。这些
信息比率来自同一回顾窗口，不能替代 OOS 证据。

H1 Buffer15 相对 Numeric 的三个时间块为 +41.93、-36.08、+19.32 bps/日，方向不稳定。
相对候选池等权，v2 的 H1 为 -1.19 bps/日，Buffer15 为 +0.98 bps/日，同样没有统计
证据。v2 与原 Numeric 的日均 Top10 重合仅 3.87 只，说明它改变了排序，但尚未形成
可靠 Alpha。

## 换手

| Variant | 单边名称换手均值 |
|---|---:|
| NUMERIC | 93.13% |
| CANDIDATE_POOL_EQW | 89.10% |
| NUMERIC_V2 | 96.35% |
| NUMERIC_V2_BUFFER15 | 94.87% |

Buffer15 相比裸 v2 仅降低 1.48 个百分点，且比原 Numeric 高 1.74 个百分点。固定 buffer
没有实现预期的低换手经济目标，后续不应在同一窗口继续扫描 buffer 参数。

## 执行数据质量

执行价格共有 190,283 行，其中 up/down limit 各缺 6,412 行，任一 limit 缺失比例为
3.37%。每个成本档（合并 H1/H3/H5）因此产生 1,740 个 missing-limit blocked orders，
另有 176 个 missing-price-row blocks。20 bps 下，候选池等权、Numeric、v2、Buffer15 的
missing-limit blocks 分别为 924、268、274、274，对应 missing-price-row 为 127、17、
16、16。

各 arm 的目标名称数和现金暴露不同，缺失价格/涨跌停字段可能影响相对收益。因此
`execution_data_quality.complete=false`，该质量门保持 fail-closed，不能把主动收益差异
全部解释为排序 Alpha。

## Benchmark ladder

- 原 Numeric：available，同一执行器。
- 候选池 Top30 等权：available，同一执行器。
- 沪深300、中证1000：unavailable，冻结 campaign 输入中没有可验证的指数收益序列。
- 行业/风格中性基准：unavailable，没有冻结的 PIT 暴露面板。

因此 `benchmark_ladder.complete=false`，promotion gate 明确失败，没有联网补数，也没有用
不完整快照替代。

## 证据与复现

不可变产物：
`artifacts/research/hotsector_numeric_v2_retrospective/run_20260717_r5`。目录包含输入哈希、
候选信号、排名、targets、成交/持仓/订单、全成本网格、主动收益、三段结果和 receipt，
发布器拒绝覆盖已有目录。

由于完整本地产物受 `artifacts/` ignore 规则管理，版本库另存了一个小型、带内容哈希的
证据回执：
`docs/research/evidence/hotsector-numeric-v2-retrospective-receipt-20260717.json`。它固化
关键 execution metrics、information ratio、换手、benchmark 状态以及本地 report、receipt
和 Parquet 的 `SHA-256`，12MB 明细仍需后续接入 `control-plane` 制品注册表（artifact registry）才能跨机器
完整恢复。

候选生产者固定为完整 commit
`dfe6dcc3678a7e1247009d01cdfa186a28180382`，`b96a71e...` 仅标记 strategy-pipeline
parent/base context，不被声明为可复现实现。实际未提交实现由逐文件 source hash map 和
canonical bundle `SHA-256`
`cbcb64216784c1a492cb436760b5f63bbe1a7acb28ca6818ce290042e75a74d5` 锚定，覆盖 Numeric
v2、runner、执行账本、统计、`daily_watch20_flite_contract` 及直接跨子模块依赖。相同
bundle record 同时写入 r5 report 和 receipt。为满足 maintainability policy，主 campaign
入口保持 74 行，并把纯 report builder 移到 reporting owner，campaign 文件由 508 降至 453
行。该重构不改变经济逻辑或产物 frame 内容。

复现入口：`scripts/research/hotsector_numeric_v2_retrospective.py`。该入口没有 provider、
模型或网络调用。

## 质量门

- Numeric v2 定向单元测试：8 passed。
- `scripts/dev/run_tests.sh lint`：passed（含 Ruff、C901 debt、边界和 split smoke）。
- `scripts/dev/run_tests.sh typecheck`：passed。
- `scripts/dev/run_tests.sh basedpyright`：release baseline ratchet passed，现有 baseline 为
  489 errors / 56 files，未增加受保护债务。
- `scripts/dev/run_tests.sh maintainability`：ratchet passed，无 >250 行函数、无新增 C901
  ignore、无 >800 行 Python 文件。
- 经济实现阶段全量测试：995 passed、1 skipped，本轮 provenance 增量按要求执行定向测试
  与全部静态 ratchet，未再次运行全量测试。
