# DailyWatch20（每日观察的 20 只 A 股名单，由 strategy-pipeline 产出给 market-intel） 旧仓再资格 v2：本地 IDE 执行笔记

生成日期：2026-07-21

## 目标

把 2026-07-21 的旧仓再资格探索升级为可审计的三臂研究协议：

1. guarded A4/B16（DailyWatch20 内部两袖：A 袖 4 只、B 袖 16 只） 生产式基准，
2. 同分数、同 entry membership、每日重置状态的 stateless control，
3. 仅增加旧仓状态携带的 stateful challenger。

这份笔记只覆盖必须在本地数据盘和完整工作区中执行的步骤。当前 V1–V4 结果属于 retrospective exploration，不计作新样本外（OOS），也不授权生产切换。

## 已创建的拉取请求（PR）

### 1. Portfolio owner

- PR：https://github.com/runchengxie/portfolio-backtester/pull/17
- 分支：`feat/incumbent-oos-controls-v2`
- 内容：
  - 严格 stateful OOS bridge，
  - stateless control bridge，
  - 缺少 `entry_eligible` 时失败关闭，
  - 自定义日期和证券列映射，
  - 两日状态、membership 和列映射测试。

### 2. Research Apps

- Draft PR：https://github.com/runchengxie/research-apps/pull/2
- 分支：`feat/incumbent-challenger-v2-controls`
- 依赖：portfolio-backtester PR #17
- 内容：
  - 三臂 challenger v2，
  - 内容寻址实验规格，
  - pairwise common-complete 统计口径，
  - 禁止自动晋级，
  - 状态隔离和失败关闭测试。

### 3. Strategy evidence 契约

- PR：https://github.com/runchengxie/strategy-pipeline/pull/28
- 分支：`feat/incumbent-evidence-contract-v2`
- 内容：
  - 时间点（PIT） entry membership 合并和覆盖审计，
  - 5 日 embargo refit ledger 校验，
  - NaN/Infinity 转换为 null 的严格 JSON，
  - 机器生成 evidence payload，
  - 禁止人工抄录统计指标。

## 合并和依赖顺序

按以下顺序操作，不要把 stacked 依赖倒着合并：

1. 检出并验证 portfolio-backtester PR #17。
2. 合并 PR #17，记录最终 main SHA。
3. 在 research-apps PR #2 中把 `pyproject.toml` 的 portfolio pin 从临时 head SHA 改为最终 main SHA。
4. 在 research-apps 运行 `uv lock`，提交 `uv.lock`。
5. 跑完整 Research Apps 门禁，通过后把 PR #2 标记 Ready 并合并。
6. Strategy PR #28 可独立验证和合并。
7. Strategy 的 v2 运行脚本接入最终 alpha、portfolio 和 research-apps main SHA 后，再更新 `pyproject.toml` 与 `uv.lock`。
8. 最后更新 research-workspace 子模块指针、workspace 清单和治理基线。

## 本地准备

```bash
cd /home/richard/code/research-workspace
git status --short
git submodule update --init --recursive
```

要求：

- 所有仓库工作树干净，
- 不在已有实验输出目录上覆盖写入，
- 数据根目录继续使用 `~/data/market-data-platform`，
- 新产物放入带版本和时间戳的新目录。

## Step 1：验证并合并 portfolio-backtester PR #17

```bash
cd /home/richard/code/research-workspace/portfolio-backtester
git fetch origin
git checkout feat/incumbent-oos-controls-v2
uv sync --locked --extra dev
uv run --locked pytest tests/test_incumbent_requalification_oos_contract.py
scripts/dev/run_tests.sh lint
scripts/dev/run_tests.sh format
scripts/dev/run_tests.sh typecheck
scripts/dev/run_tests.sh typecheck-release
scripts/dev/run_tests.sh all
scripts/dev/run_tests.sh maintainability
```

验收：

- stateful 第二日保留跌出 entry 区但仍在 exit buffer 内的旧仓，
- stateless 第二日按当日 entry membership 重选，
- stateful 换手低于 stateless，
- 缺少 `entry_eligible` 明确失败，
- 自定义日期和证券列测试通过，
- 全量测试无排除项。

合并后记录：

```bash
git checkout main
git pull --ff-only
PORTFOLIO_MAIN_SHA=$(git rev-parse HEAD)
printf '%s\n' "$PORTFOLIO_MAIN_SHA"
```

## Step 2：完成 Research Apps PR #2 的依赖锁和完整门禁

```bash
cd /home/richard/code/research-workspace/research-apps
git fetch origin
git checkout feat/incumbent-challenger-v2-controls
```

把 `pyproject.toml` 中：

```toml
portfolio-backtester = { git = "https://github.com/runchengxie/portfolio-backtester.git", rev = "..." }
```

改为 Step 1 的最终 main SHA，然后：

```bash
uv lock
uv sync --locked --extra dev
uv run --locked pytest tests/test_incumbent_challenger_v2.py
scripts/dev/run_tests.sh lint
scripts/dev/run_tests.sh format
scripts/dev/run_tests.sh typecheck
scripts/dev/run_tests.sh all
```

额外检查 wheel 包含冻结规格：

```bash
uv build
python - <<'PY'
from pathlib import Path
import zipfile

wheel = sorted(Path('dist').glob('*.whl'))[-1]
with zipfile.ZipFile(wheel) as archive:
    names = set(archive.namelist())
required = 'research_apps/campaign_specs/daily_watch20_incumbent_challenger_v2_20260721.json'
assert required in names, required
print(required)
PY
```

验收：

- daily 输出同时包含 `baseline_*`、`stateless_*`、`stateful_*`，
- `stateful_minus_stateless` 是主要缓冲归因，
- `stateful_minus_baseline` 仅表示整套替代策略差异，
- receipt 包含 spec SHA、完整 policy 和 `automatic_promotion_allowed=false`，
- 缺少 `entry_eligible` 时失败，
- `uv.lock` 与最终依赖 SHA 一致。

## Step 3：验证并合并 Strategy evidence 契约 PR #28

```bash
cd /home/richard/code/research-workspace/strategy-pipeline
git fetch origin
git checkout feat/incumbent-evidence-contract-v2
uv sync --locked --extra dev
uv run --locked pytest tests/test_daily_watch20_incumbent_evidence.py
scripts/dev/run_tests.sh lint
scripts/dev/run_tests.sh format
scripts/dev/run_tests.sh typecheck
scripts/dev/run_tests.sh all
```

验收：

- membership 缺日期、重复键或每日成员数不足时失败，
- embargo 小于 5 或 fit as-of 不早于评估块时失败，
- JSON 中不存在 `NaN`、`Infinity` 或 `-Infinity`，
- evidence payload 始终为 `research_only_non_promotable`，
- `manual_metric_transcription_allowed=false`。

## Step 4：生成历史 THS strict-v2 entry membership

不得直接猜原始文件格式。使用 market-data-platform 公共入口：

```python
from market_data_platform.research_views.daily_watch20_candidate_pool import (
    load_daily_watch20_candidate_pool,
)
```

对冻结评估日期逐日加载 `ths_hot_strict_v2` 候选池，并只输出正 membership：

```text
trade_date,symbol
2025-07-18,000001.SZ
2025-07-18,000002.SZ
...
```

输出目录建议：

```text
~/data/incumbent_challenger_v2/entry_membership/
  membership.csv
  membership_receipt.json
  per_date_receipts/
```

`membership_receipt.json` 至少包含：

- candidate pool mode 和 policy ID，
- 日期起止，
- 每日成员数最小值、最大值和分位数，
- rank coverage 状态，
- 缺失日期，
- 原始输入路径和 SHA-256，
- market-data-platform commit，
- current 契约和相关清单 SHA-256。

硬门槛：

- 每个评估日期都有 membership，
- 每日正成员数至少 20，
- `(trade_date, symbol)` 唯一，
- 不使用当前快照回填历史日期，
- 缺失日期不得自动退化到 all-market。

随后用 Strategy PR #28 的公共函数校验：

```python
from strategy_pipeline.daily_watch20_incumbent_evidence import attach_entry_membership

scored, membership_diagnostics = attach_entry_membership(
    scored,
    membership,
    minimum_members_per_date=20,
)
```

## Step 5：新增 v2 本地研究脚本

不要覆盖 v1 文件。新增：

```text
strategy-pipeline/scripts/research/daily_watch20_incumbent_challenger_v2.py
```

以现有 v1 脚本为数据加载骨架，必须完成以下改动。

### 5.1 升级 owner pins

至少使用：

- alpha-research：`528c40af26737468e41da85ed4baa591ed2099dc` 或之后包含 embargo ledger 的 main SHA，
- portfolio-backtester：PR #17 合并后的 main SHA，
- research-apps：PR #2 合并后的 main SHA，
- market-data-platform：membership 生成时使用的精确 SHA。

更新：

```text
pyproject.toml
uv.lock
research-workspace submodule pointers
```

### 5.2 使用生产一致模型身份

不要再把完整 `DAILY_WATCH20_FEATURES` 直接传入模型。使用 Strategy 当前生产 helper：

```python
from strategy_pipeline.daily_watch20_pipeline import (
    _feature_policy_id,
    _model_features,
    _selection_config,
)
```

模型配置必须使用：

```python
features=_model_features(config)
feature_policy_id=_feature_policy_id(config.minute_lag_trade_days)
label_policy_id=LIMIT_AWARE_NEXT_OPEN_LABEL_POLICY_ID
```

默认情况下 Hermite 只作为 guard，不进入 ranker 特征。

### 5.3 强制 5 日 embargo

```python
scored, refits = score_rolling_oos(
    ...,
    embargo_trade_days=5,
)
```

不得丢弃 `refits`。用 PR #28：

```python
validated_refits = validate_refit_ledger(
    refits,
    required_embargo_trade_days=5,
)
```

### 5.4 显式合并 entry membership

在调用 Research Apps v2 前执行 `attach_entry_membership`。禁止由 bridge 自动生成 entry 资格。

### 5.5 运行三臂协议

```python
from research_apps.daily_watch20.incumbent_challenger_v2 import (
    run_incumbent_challenger_v2,
)
```

每档成本分别运行：

```text
10 bps
20 bps
30 bps
50 bps
```

### 5.6 机器生成证据

使用：

```python
payload = build_incumbent_evidence_payload(
    source_date=source_date,
    summaries=summaries,
    refits=validated_refits,
    membership=membership_diagnostics,
    lineage=lineage,
)
write_strict_json(output_dir / 'incumbent_evidence_v2.json', payload)
```

禁止再手工建立一份数字摘要 JSON。Markdown 报告必须从 `incumbent_evidence_v2.json` 渲染。

lineage 至少包含：

- 五个 owner 仓库 commit，
- research-workspace commit，
- feature policy ID，
- label policy ID，
- model version 和完整 model params，
- current 契约 SHA，
- daily、minute、membership 清单 SHA，
- campaign spec SHA，
- daily CSV、summary JSON、refit ledger 和 membership 文件 SHA。

## Step 6：参数政策

今天的 V1–V4 已经查看了同一个 trailing OOS 窗口，因此不再具有组合超参数层面的新 OOS 身份。

禁止：

- 在同一 252 日窗口继续扫描 entry=40、50、60 后选最优，
- 把 nominal p 值称为确认性显著，
- 根据本轮结果自动晋级。

推荐二选一：

### 路径 A：直接冻结未来 shadow 候选

在看 v2 历史结果前预先固定一个候选，例如：

```text
entry_rank_limit=50
exit_rank_limit=100
max_new_positions=10
industry_cap=4
min_score_improvement=0
allow_cash=true
```

该组参数只作为待验证假设，不宣称历史最优。

### 路径 B：继续做 retrospective 网格

可以扫描，但必须：

- 明确标记 exploratory retrospective，
- 冻结完整参数族和多重检验族，
- 只用于挑选一个未来 shadow 候选，
- 所有历史 p 值做 Holm 或同类修正，
- 不把扫描窗口结果计入最终晋级证据。

## Step 7：历史稳定性诊断

在 252 日历史范围内拆成四个非重叠 63 日窗口，仅作稳定性诊断：

- stateful - stateless turnover delta，
- stateful - stateless gross/net paired delta，
- cash weight，
- buffered incumbent count，
- industry exposure，
- gross exposure，
- return completeness，
- blocked trade weight。

同时输出：

1. 实际 NAV 口径，现金收益按冻结假设，
2. invested-capital return，
3. 与 challenger 每日 gross exposure 匹配的缩放 baseline。

任何绝对均值必须携带：

```text
observations
coverage
sample_scope
```

任何 paired delta 必须携带：

```text
common_complete_dates
common_complete_date_ratio
```

## Step 8：未来追加式 shadow

参数和代码身份冻结后，从下一个未观察交易日开始：

```text
T+20  第一次健康检查
T+60  中期检查
T+120 成熟检查
```

规则：

- 只追加，不回写，
- 中途不改参数，
- 参数变化必须开启新 policy ID 和新 shadow series，
- 每日保存三臂目标、membership receipt、refit identity 和执行审计，
- 未达到 T+120 不进入生产晋级讨论。

## Step 9：质量门禁

每个 owner 仓都运行自身完整门禁，再运行 workspace 组合门禁：

```bash
cd /home/richard/code/research-workspace
scripts/dev/run_tests.sh lint
scripts/dev/run_tests.sh format
scripts/dev/run_tests.sh typecheck
scripts/dev/run_tests.sh all
scripts/dev/run_tests.sh maintainability
```

不要通过整体重生成 maintainability baseline 来消除新失败。仅在确认扫描范围变化或新增合法文件后，提交最小、可解释的基线差异。

## 最终验收清单

- [ ] portfolio-backtester PR #17 完整门禁通过并合并
- [ ] research-apps PR #2 更新最终 pin 和 `uv.lock`
- [ ] research-apps wheel 包含 v2 spec
- [ ] strategy-pipeline PR #28 完整门禁通过并合并
- [ ] alpha pin 包含 5 日 embargo 和 refit ledger
- [ ] 历史 THS strict-v2 membership 无缺失日期
- [ ] v2 脚本使用生产一致 features 和 policy IDs
- [ ] 三臂 daily 输出完整
- [ ] `stateful - stateless` 为主要缓冲归因
- [ ] 所有 JSON 可由标准 `json.loads` 读取
- [ ] evidence 数字全部由原始 summary 自动生成
- [ ] 当前 V1–V4 标记为 retrospective、non-promotable
- [ ] 新 shadow 参数和 policy ID 已冻结
- [ ] 未修改生产发布路径

## 旧证据的处理

保留以下文件用于历史追溯，不删除：

```text
docs/evidence/incumbent-challenger-20260721.json
docs/research/incumbent-challenger-20260721/
```

在索引或后续报告中明确标记：

```text
retrospective_exploration
superseded_for_inference_by_v2_protocol
not_eligible_for_promotion
```

原文件中的人工摘要数字不得继续作为决策来源。v2 证据以 strict JSON 机器产物为唯一统计事实来源。
