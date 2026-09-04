# A 股长窗口晋级证据生成 runbook

生成日期：2026-08-18
最近核对：2026-08-25

## 目标

把 A 股研究证据从 2026-06-01 短窗口基线升级为 2015 至最新的长窗口晋级证据，覆盖就绪度报告的
`production_strategy_evidence` 档，并为策略晋级门禁生成可校验的 canonical promotion receipt。
实际回测可以按证据项分批执行，但最终晋级 receipt 必须绑定同一冻结评审所采用的数据清单、代码提交、
配置文件和持久化源证据。

证据项与就绪度检查的对应关系见 `docs/evidence/a-share-readiness-evidence-20260601.json` 和
[`docs/data-transition-playbook.md`](../data-transition-playbook.md)。

## 前置条件

- 平台已发布 2015 起数据资产，current 契约见 `metadata/current_assets/a_share_current.json`。
- `DATA_PLATFORM_ROOT` 指向平台根目录。
- 六个子模块已检出，`strategy` 命令可用。
- 每条命令完成后记录数据清单、代码提交和配置哈希，核对表见文末。
- canonical receipt 只引用可持续复核的源文件。只存在于已删除 worktree、临时目录或日志文本中的数字不能作为晋级源。

## 数据物化

### 平台资产直接读取

`default` 预设使用 `data.source_mode: platform_assets`，流水线直接从 `$DATA_PLATFORM_ROOT`
读取资产，不需要把数据复制进 `strategy-pipeline/artifacts/assets/`。形如 `artifacts/assets/...`
的相对路径由 `market_data_platform.artifacts.resolve_data_input_path` 映射到平台根目录。
实际资产路径和覆盖日期以 `$DATA_PLATFORM_ROOT/metadata/current_assets/a_share_current.json` 为准。

### benchmark 收益文件

`strategy backtest benchmark-ladder` 与回测的 benchmark 对比需要
`strategy-pipeline/artifacts/benchmarks/` 下的日收益 CSV，每份为 `trade_date, benchmark_return`
两列。`strategy_pipeline.e2_evidence` 已提供指数收益与 PIT 等权股票池收益生成入口，不再手工拼接 CSV。

指数收益示例：

```bash
cd strategy-pipeline
python -m strategy_pipeline.e2_evidence index-returns \
  --input "$DATA_PLATFORM_ROOT/<index_daily_asset>" \
  --symbol 000300.SH \
  --start-date 20150101 \
  --end-date <latest-trade-date> \
  --output artifacts/benchmarks/a_share_csi300_daily_returns.csv
```

对 `000905.SH`、`000906.SH`、`000852.SH` 重复运行，并把输出路径写入
`configs/experiments/sweeps/a_share__research_protocol_benchmark_ladder.yml`。

PIT Top800 等权收益示例：

```bash
python -m strategy_pipeline.e2_evidence top800-equal-weight \
  --universe "$DATA_PLATFORM_ROOT/<top800_by_date_asset>" \
  --daily "$DATA_PLATFORM_ROOT/<daily_clean_asset>" \
  --membership-lag-days 1 \
  --start-date 20150227 \
  --end-date <latest-trade-date> \
  --output artifacts/benchmarks/a_share_top800_pit_equalw_daily_returns.csv
```

`--membership-lag-days 1` 用来避免按当日流动性选入股票后又计入同日收益的前视偏差。具体资产路径不得从
历史示例硬编码，运行前从 current 契约解析。

## 长窗口候选 run

当前长窗口变体位于 `strategy-pipeline/configs/experiments/variants/a_share_long_window.yml`，历史冻结版本也可
带日期后缀保存。晋级评审使用的配置必须明确：

```yaml
data:
  start_date: "20150101"
  end_date: "<latest-trade-date>"
  asset_coverage_start_date: "20150101"
```

运行并记录 run 目录：

```bash
cd strategy-pipeline
strategy run --config configs/experiments/variants/a_share_long_window.yml
```

run 目录为 `artifacts/runs/<run_name>_<时间戳>_<配置哈希>/`。至少核对 `summary.json`、
`config.used.yml`、`inputs.lock.json`、`dataset.parquet`、`eval_scored.parquet`、
`backtest_net.csv`、`backtest_periods.csv`、`positions_by_rebalance.csv` 与 `positions_current.csv`。

## 证据命令

按顺序执行，把 `<run_dir>`、`<tag>` 等占位符替换为真实值。命令与配置来自
`strategy-pipeline` 的 `docs/cli.md`、`configs/experiments/sweeps/` 与 E2 evidence 模块。

### benchmark-ladder

```bash
strategy backtest benchmark-ladder \
  --config configs/experiments/sweeps/a_share__research_protocol_benchmark_ladder.yml
```

配置要求 `strategy_returns_file` 指向 `<run_dir>/backtest_net.csv`，每个 benchmark 显式声明
`market: a_share`。晋级用报告必须持久化到可版本控制或可发布复核的位置，不能只保留临时 run 输出。

### feature-evidence

```bash
strategy alpha feature-evidence generate-ablation \
  --config configs/experiments/sweeps/a_share__research_protocol_feature_evidence.yml
```

`generate-ablation` 生成特征族消融运行，后续用 `summarize-ablation` 汇总。配置的 `scored_file`
与 `factor_ic_file` 引用候选 run 的 `eval_scored.parquet` 与 `dataset.parquet`。

### cpcv

```bash
strategy alpha cpcv \
  --config configs/experiments/sweeps/a_share__research_protocol_cpcv.yml \
  --n-groups 8 \
  --test-groups 2
```

输出目录默认 `artifacts/reports/cpcv_<config_stem>/`。晋级 receipt 中的 `cpcv` check 只在最终持久化的
CPCV 报告通过且字段满足 canonical 契约时置为 `passed`。

### promotion-gate

先补 exposure-screen 与 pbo 报告，再运行研究层 promotion-gate：

```bash
strategy backtest exposure-screen \
  --summary artifacts/runs/<run_dir>/summary.json \
  --out artifacts/reports/<tag>/exposure_screen.json

strategy alpha pbo \
  --returns <收益矩阵 csv 或 parquet> \
  --out artifacts/reports/pbo_<tag>/pbo_summary.json

strategy promotion-gate \
  --config configs/experiments/sweeps/a_share__research_protocol_promotion_gate.yml
```

此处的 pipeline promotion-gate 是研究计算的一部分。顶层
`python scripts/strategy_evidence_gate.py --strict --zero-gaps` 负责最终 lifecycle 与 canonical source 复核，
两者不能互相替代。

### capacity-report

```bash
strategy backtest capacity \
  --run-dir artifacts/runs/<run_dir> \
  --pricing-file <日线定价面板含 liquidity 列> \
  --portfolio-value 500000,1000000,2000000,5000000,10000000,50000000,100000000 \
  --participation-rate 0.01,0.03,0.05,0.10 \
  --liquidity-col medadv20_amount --liquidity-col amount \
  --output-json <持久化 capacity 报告路径>
```

A 股 Tushare `amount` 与订单名义金额的单位必须一致。2026-08-24 的早期 capacity 诊断曾因 1000 倍单位
错误被 supersede，晋级时只能引用单位修正后的结果。当前 `a_share_long_window` promotion profile 把
`capacity` 作为独立 profile check，即使策略当前生命周期分母不包含 capacity，也必须有 canonical
`passed` 证据才能通过零缺口晋级评审。

### turnover-cost

`strategy_pipeline.e2_evidence` 已提供独立 CLI：

```bash
python -m strategy_pipeline.e2_evidence turnover-cost \
  --summary artifacts/runs/<run_dir>/summary.json \
  --output <持久化 turnover-cost 报告路径> \
  --long-window-stress-completed
```

在包含 strategy-pipeline PR #86 的版本中，`--cpcv-evidence <cpcv_summary.json>` 为可选诊断输入。
CPCV 状态不再决定 cost check 是否通过，避免 `cost` 与 `cpcv` 两个独立晋级维度互相绑架。cost 的
canonical check 仍需至少两个不同 `cost_bps` 场景及其净表现指标，单一成本点不能晋级。

### final OOS

晋级需要真实冻结的最终样本外切片。canonical `final_oos` check 至少记录 `oos_start`、评估指标、
`frozen_before_evaluation: true` 与 `retuned_after_freeze: false`。

书面替代、diagnostic 或 2026-08-24 的 Final OOS 摘要本身不能自动升级为 canonical `passed`。只有在原始
配置、代码提交、current 数据契约和持久化源报告都能按哈希重新核验时，才可进入 canonical receipt。

## 生成 canonical promotion receipt

strategy-pipeline PR #86 提供 `strategy_pipeline.e2_promotion_receipt` writer。该 writer 只把研究人员已经
明确给出的评审状态与 checks 固化为哈希化 receipt，不会自行把 diagnostic 推断成 `passed`。

先准备一个临时 spec JSON，明确：

- `strategy_id`、`profile_id=a_share_long_window`、`review_id`、`generated_at` 与顶层 `status`。
- `research_window.configured_start_date=20150101` 与实际 `end_date`。
- `lineage.repositories` 中实际依赖的 owner 子模块 40 位 commit SHA。
- workspace-relative 配置路径。
- data-platform-relative current contract 与 manifest 路径。
- 可持续复核的 `source_artifacts` 路径。
- 本次真实形成的 `checks`。尚未完成的项目保持 `pending` 或不写入，禁止预填 `passed`。

生成 receipt：

```bash
cd strategy-pipeline
python -m strategy_pipeline.e2_promotion_receipt \
  --spec artifacts/reports/<tag>/promotion-receipt-spec.json \
  --workspace-root .. \
  --data-platform-root "$DATA_PLATFORM_ROOT" \
  --output ../strategy-research/research/evidence/promotion/<strategy_id>/<review_id>.json
```

随后在 `strategy-research/research/evidence/<strategy_id>.json` 顶层增加 `promotion_evidence` 映射。每个已经形成
canonical source 的 lifecycle check 以及 profile check 指向对应 receipt，例如：

```json
{
  "promotion_evidence": {
    "pit": "strategy-research/research/evidence/promotion/<strategy_id>/<review_id>.json",
    "cost": "strategy-research/research/evidence/promotion/<strategy_id>/<review_id>.json",
    "capacity": "strategy-research/research/evidence/promotion/<strategy_id>/<review_id>.json"
  }
}
```

多个 check 可以引用同一个冻结 review receipt。legacy `evidence` 字段继续作为研究导航，不能替代
`promotion_evidence`。

## 刷新就绪度证据

长窗口 run 产出后：

1. 新建 `docs/evidence/a-share-readiness-evidence-<YYYYMMDD>.json`，把 `research_run_dir`、
   `targets_file`、`targets_lineage_file` 指向新 run 目录，`research_profile.configured_start_date`
   更新为 `20150101`。
2. 由 owner adapter 生成 `holdings.json` 后，用公共 pipeline 生成交接文件：

```bash
strategy-pipeline export-targets \
  --holdings artifacts/runs/<run_dir>/holdings.json \
  --out artifacts/reports/<tag>/targets.json \
  --lineage-out artifacts/reports/<tag>/targets.json.lineage.json
```

3. 运行 readiness 报告并写入 `docs/evidence/`：

```bash
python src/research_contracts/a_share_readiness.py \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --evidence-manifest docs/evidence/a-share-readiness-evidence-<YYYYMMDD>.json \
  --out docs/evidence/a-share-readiness-report-<YYYYMMDD>.json \
  --pretty
```

4. 运行策略晋级评审：

```bash
DATA_PLATFORM_ROOT="$DATA_PLATFORM_ROOT" \
  python scripts/strategy_evidence_gate.py --strict --zero-gaps
```

日常 pre-push 继续使用 `--strict`，不会因为尚未生成 canonical receipt 或本机没有数据平台根目录而冻结。
`--strict --zero-gaps` 会读取 receipt 本体，复算 config、current contract、manifest 和 source artifact 的
SHA256，并核对 receipt 中声明的子模块提交与 superproject 当前 gitlink。

## 证据缺口三态登记表（E2 进度快照）

> 状态口径：本表为缺口登记，不代表晋级结论。`命令就绪` 表示生成入口已存在，`数据就绪` 表示依赖的
> current 资产已发布，`计算未完成` 表示真实长窗口计算或 canonical 固化仍缺失。任何项目都不能仅凭
> 文档摘要或历史短窗口结果标成 `passed`。

| 证据项 | 命令就绪 | 数据就绪 | 计算未完成 | 缺口说明 |
| --- | --- | --- | --- | --- |
| benchmark-ladder | 是 | 是 | 是 | 需按 2015 至 latest 的冻结配置重跑并持久化报告 |
| feature-evidence | 是 | 是 | 是 | 当前晋级所需长窗口消融证据仍需生成 |
| cpcv | 是 | 是 | 是 | 需冻结选择后运行并持久化 CPCV 报告 |
| promotion-gate | 是 | 是 | 是 | 前置证据未齐时不得生成通过结论 |
| capacity | 是 | 是 | 是 | 已有修正 diagnostic，canonical promotion check 仍未形成 |
| turnover-cost | 是 | 是 | 是 | CLI 已工具化，仍需真实多成本压力场景与 canonical receipt |
| final-oos | 是 | 是 | 是 | 已有 frozen diagnostic，仍需可核验的 canonical source lineage |
| canonical-receipt | 已合并 #86 | 是 | 是 | writer 已同步到顶层 gitlink，五策略当前均无 canonical receipt |

登记基准日：2026-08-25。表中状态随实际 run 与 merged owner 版本更新，不得在计算未完成时预填
`passed`。

## 命令核对引用

每条证据命令完成后记录：

- 数据清单：`inputs.lock.json`、current 契约与平台 manifest 的状态、覆盖区间和 SHA256。
- 代码提交：实际参与研究的 `strategy-pipeline`、`portfolio-backtester`、`alpha-research` 等 owner commit。
- 配置哈希：冻结配置文件的完整 SHA256，不能只依赖 run 目录短哈希。
- 源证据：用于形成 canonical check 的持久化 JSON 或发布资产及其 SHA256。

## 资源估算

完整 2015 至最新的计算仍属于重任务。是否分片执行取决于当前机器资源，分片结果最终必须回到同一冻结
评审语义中，不能把不同代码、配置或数据版本的局部结果拼成一个 `passed` receipt。

## 验收

- 就绪度报告 `production_strategy_evidence` 档所有检查通过。
- 策略生命周期要求的 PIT、walk-forward、benchmark、cost、final OOS、CPCV、regime 等实际必需项通过。
- `a_share_long_window` profile 的 capacity 与 2015 历史覆盖通过。
- 每个晋级 check 有 `strategy_promotion_evidence.v2` canonical source，并能复算所有声明哈希。
- `python scripts/strategy_evidence_gate.py --strict --zero-gaps` 对目标策略通过。
- diagnostic、substitute、superseded 和缺失原始源产物的历史摘要均不能充当 canonical `passed`。
