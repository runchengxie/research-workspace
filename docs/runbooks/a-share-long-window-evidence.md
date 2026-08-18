# A 股长窗口晋级证据生成 runbook

生成日期：2026-08-18

## 目标

把 A 股研究证据从 2026-06-01 短窗口基线升级为 2015 至最新的长窗口晋级证据，覆盖就绪度报告的
`production_strategy_evidence` 档。本 runbook 只记录命令级步骤。实际回测需要较长计算时间，
可以按年份或证据项分批执行，每批结果单独留存。

证据项与就绪度检查的对应关系见 `docs/evidence/a-share-readiness-evidence-20260601.json` 和
[`docs/data-transition-playbook.md`](../data-transition-playbook.md)。

## 前置条件

- 平台已发布 2015 起数据资产，current 契约见 `metadata/current_assets/a_share_current.json`。
- `DATA_PLATFORM_ROOT` 指向平台根目录。
- 六个子模块已检出，`strategy` 命令可用。
- 每条命令完成后记录数据清单、代码提交和配置哈希，核对表见文末。

## 数据物化

### 平台资产直接读取

`default` 预设使用 `data.source_mode: platform_assets`，流水线直接从 `$DATA_PLATFORM_ROOT`
读取资产，不需要把数据复制进 `strategy-pipeline/artifacts/assets/`。形如 `artifacts/assets/...`
的相对路径由 `market_data_platform.artifacts.resolve_data_input_path` 映射到平台根目录。
current 契约中 2015 至最新的 `daily_clean` 约 1160 万行，`universe_by_date` 覆盖 139 个调仓日。

### benchmark 收益文件

`strategy backtest benchmark-ladder` 与回测的 benchmark 对比需要
`strategy-pipeline/artifacts/benchmarks/` 下的日收益 CSV，每份为 `trade_date, benchmark_return`
两列，格式与 `strategy-pipeline` 的 `tests/test_pipeline_e2e_benchmarks.py` 一致。来源为平台
`assets/tushare/a_share/index_daily/` 资产和 top800 等权股票池。当前仓库没有现成生成命令，
需要先构建，文件名与 `configs/experiments/sweeps/a_share__research_protocol_benchmark_ladder.yml`
的 `returns_file` 一致：

```text
artifacts/benchmarks/a_share_csi300_000300_SH_daily_returns_20150101_20260529.csv
artifacts/benchmarks/a_share_csi500_000905_SH_daily_returns_20150227_20260529.csv
artifacts/benchmarks/a_share_csi800_000906_SH_daily_returns_20150227_20260529.csv
artifacts/benchmarks/a_share_csi1000_000852_SH_daily_returns_20150227_20260529.csv
artifacts/benchmarks/a_share_top800_liquid_pit_equalw_daily_returns_20150227_20260529.csv
```

构建步骤：

1. 从 `assets/tushare/a_share/index_daily/` 各时期资产读取 `000300.SH`、`000905.SH`、
   `000906.SH`、`000852.SH` 的日收益并拼接。
2. top800 等权收益从 `assets/universe/top800_by_date.csv` 与 `daily_clean` 计算。
3. 写入 `strategy-pipeline/artifacts/benchmarks/`。

## 长窗口候选 run

`configs/presets/a_share.yml` 的 `data.start_date` 当前为 `20240229`。长窗口需要在
`strategy-pipeline` 新建变体配置，例如 `configs/experiments/variants/a_share_long_window.yml`，
继承 `a_share.yml` 并覆盖：

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

run 目录为 `artifacts/runs/<run_name>_<时间戳>_<配置哈希>/`，后缀哈希即本次配置哈希。目录内含
`summary.json`、`config.used.yml`、`inputs.lock.json`、`dataset.parquet`、
`eval_scored.parquet`、`backtest_net.csv`、`backtest_periods.csv`、
`positions_by_rebalance.csv`、`positions_current.csv`。

## 证据命令

按顺序执行，把 `<run_dir>`、`<tag>` 等占位符替换为真实值。命令与配置均来自
`strategy-pipeline` 的 `docs/cli.md` 和 `configs/experiments/sweeps/`。

### benchmark-ladder

```bash
strategy backtest benchmark-ladder \
  --config configs/experiments/sweeps/a_share__research_protocol_benchmark_ladder.yml
```

配置要求 `strategy_returns_file` 指向 `<run_dir>/backtest_net.csv`，每个 benchmark 显式声明
`market: a_share`。输出写往 `artifacts/reports/a_share_benchmark_ladder.json` 与同名 CSV。

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

输出目录默认 `artifacts/reports/cpcv_<config_stem>/`，其中 `cpcv_summary.json` 会被
promotion-gate 引用。

### promotion-gate

先补 exposure-screen 与 pbo 报告，再运行 promotion-gate：

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

promotion-gate 配置的 `baseline_run`、`candidate_run`、`cpcv.*`、`dsr.*` 都是占位符，运行前
替换为真实 run 目录和报告路径。

### capacity-report

```bash
strategy backtest capacity \
  --run-dir artifacts/runs/<run_dir> \
  --pricing-file <日线定价面板含 liquidity 列> \
  --portfolio-value 500000,1000000,2000000,5000000,10000000,50000000,100000000 \
  --participation-rate 0.01,0.03,0.05,0.10 \
  --liquidity-col medadv20_amount --liquidity-col amount \
  --output-json docs/evidence/a-share-capacity-<YYYYMMDD>.json
```

`medadv20_amount` 由流水线在运行期计算。`--run-dir` 默认读取 `positions_by_rebalance.csv`，
`--pricing-file` 需要含 `trade_date`、`symbol`、价格与 liquidity 列的面板。

### turnover-cost

没有独立 CLI。从 run 的 `backtest_periods.csv`、`summary.json` 和 cpcv 输出取平均换手与成本
拖累，写成 `docs/evidence/a-share-turnover-cost-<YYYYMMDD>.json`，结构沿用
`a-share-turnover-cost-20260601.json`，长窗口压力证据完成后把 `status` 置为 passed。

### final OOS 或书面替代

`eval.final_oos` 默认关闭。需要保留独立最终 OOS 切片，或记录书面替代说明到
`docs/evidence/a-share-final-oos-substitute-<YYYYMMDD>.json`。书面替代不能描述为真实样本外。

## 刷新就绪度证据

长窗口 run 产出后：

1. 新建 `docs/evidence/a-share-readiness-evidence-<YYYYMMDD>.json`，把 `research_run_dir`、
   `targets_file`、`targets_lineage_file` 指向新 run 目录，`research_profile.configured_start_date`
   更新为 `20150101` 或 `20150227`。
2. 用 `strategy export-targets` 生成交接文件：

```bash
strategy export-targets \
  --run-dir artifacts/runs/<run_dir> \
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

## 证据缺口三态登记表（E2 进度快照）

> 状态口径：本表为缺口登记，不是晋级结论。三态含义：`命令就绪` 表示 runbook 命令与变体配置已落地，
> `数据就绪` 表示依赖的 current 资产与清单已发布，`计算未跑` 表示实际长窗口回测尚未执行，证据未生成。
> 任何状态不得标 `passed`，除非对应 `docs/evidence/a-share-*.json` 真实出现该结论（E1 门禁约束）。

| 证据项 | 命令就绪 | 数据就绪 | 计算未跑 | 缺口说明 |
| --- | --- | --- | --- | --- |
| benchmark-ladder | 是 | 是 | 是 | 基准阶梯需按变体 `a_share_long_window.yml`（20150101 起）重跑 |
| feature-evidence | 是 | 是 | 是 | 特征证据需覆盖长窗口样本，当前仅短窗口基线 |
| cpcv | 是 | 是 | 是 | CPCV 需长窗口折叠重采样，未执行 |
| promotion-gate | 是 | 是 | 是 | 晋级门禁命令就绪，但前置证据全为 pending 时不触发晋级 |
| capacity | 是 | 是 | 是 | 容量压力证据 `docs/evidence/a-share-*.json` 仍 `pending`（roadmap E2） |
| turnover-cost | 是 | 是 | 是 | 成本压力证据 `docs/evidence/a-share-*.json` 仍 `pending`（roadmap E2） |
| final-oos | 是 | 是 | 是 | 最终样本外 `daily_watch20` 的 `final_oos` 非 pass，属客观事实 |

登记基准日：2026-08-19。三态随实际 run 输出更新，不得在未跑计算时预填 `passed`。

## 命令核对引用

每条证据命令完成后记录三项内容：

- 数据清单：`inputs.lock.json`、current 契约与平台 manifest 的状态和覆盖区间。
- 代码提交：`strategy-pipeline`、`portfolio-backtester`、`alpha-research` 当前 git 提交。
- 配置哈希：run 目录名后缀，或 `config.used.yml` 内容。

## 资源估算

当前机器为 4 核、31GB 内存、约 464GB 可用磁盘。平台资产已就绪，磁盘新增主要是 run 输出，
估算在数十 GB 内。内存瓶颈在把 2015 至今约 1160 万行 `daily_clean` 与特征面板载入内存，
估算峰值 8 至 15GB，本机 31GB 可以容纳，但 4 核 CPU 会让完整 11 年 XGB 回测耗时较长。
完整长窗口回测建议在内存 64GB 以上、16 核以上的机器执行，或先按年份分片验证再合并证据。

## 验收

- 就绪度报告 `production_strategy_evidence` 档所有检查通过。
- `docs/evidence/a-share-*.json` 的 turnover-cost、capacity、final-oos 状态全部为 passed。
- 证据文件引用的路径在 R4 owner 布局下真实存在。
