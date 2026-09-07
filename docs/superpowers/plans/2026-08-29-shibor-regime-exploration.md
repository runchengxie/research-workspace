# Shibor 状态探索实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

目标：构建可复现、非生产用途的探索实验，检验 Shibor 状态和 Shibor×股票暴露是否能为每日截面基线增加解释力。

架构：数据由 `market-data-platform` 负责。顶层实验通过 owner API 读取已发布的 `a_share` 和 `cn_context` 契约，只计算研究专属的变换、连接、标签和诊断，并写入可审计结果资产，不修改执行或生产策略代码。

技术栈：Python、pandas、PyYAML、现有 `market_data_platform` 和 `alpha_research` API、pytest。

规格：`strategy-research/experiments/macro_context_shadow/experiment.yml`

## 全局约束

- Shibor 是主要背景变量，PMI 仅用于探索，不能支持可晋升的结论。
- 主要标签周期为 20 个交易日，5 日和 60 日为次要周期。
- 实验必须保留 `available_at <= feature_as_of`，并记录契约哈希。
- 不接入生产策略、执行或 DailyWatch20。
- 可以报告重建的背景数据行，但必须明确标记，并排除在严格证据之外。

### 任务 1：定义探索协议和结果模式

**Files:**
- Modify: `strategy-research/experiments/macro_context_shadow/experiment.yml`
- Modify: `strategy-research/experiments/macro_context_shadow/README.md`
- Test: `strategy-research/tests/test_shibor_regime_exploration.py`

**Interfaces:**
- Produces frozen regime names, horizons, cost assumptions, and result field names for later tasks.

- [ ] Write tests for the frozen protocol and strict exclusion of reconstructed rows.
- [ ] Run the focused tests and confirm they fail for the missing protocol helpers.
- [ ] Add the protocol fields and minimal validation helpers.
- [ ] Run focused tests and commit.

### 任务 2：实现 PIT 安全的 Shibor 状态和暴露变换

**Files:**
- Create: `strategy-research/experiments/macro_context_shadow/shibor_regime.py`
- Modify: `strategy-research/tests/test_shibor_regime_exploration.py`

**Interfaces:**
- `build_shibor_regimes(context_pit: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame`
- `build_shibor_exposure_interactions(stock_frame: pd.DataFrame, regimes: pd.DataFrame) -> pd.DataFrame`
- `build_forward_labels(prices: pd.DataFrame, horizons: Sequence[int]) -> pd.DataFrame`

- [ ] Add failing tests for as-of filtering, regime direction, exposure interactions, and forward-label non-lookahead.
- [ ] Run tests and verify expected failures.
- [ ] Implement the smallest pure functions using published rows only.
- [ ] Run focused tests, format/lint, and commit.

### 任务 3：增加真实数据探索运行器

**Files:**
- Create: `strategy-research/experiments/macro_context_shadow/run_shibor_regime_exploration.py`
- Modify: `strategy-research/tests/test_shibor_regime_exploration.py`
- Modify: `strategy-research/experiments/macro_context_shadow/README.md`

**Interfaces:**
- CLI arguments: `--data-root`, `--output`, `--as-of`, `--dry-run`.
- Output JSON contains contract hashes, row counts, PIT audit, regime counts, and an explicit `evidence_status`.

- [ ] Add failing runner tests for dry-run output and missing-input failure.
- [ ] Implement contract loading, data discovery, diagnostics, and JSON output.
- [ ] Run the focused tests and local real-data dry run.
- [ ] Commit.

### 任务 4：运行证据诊断并记录限制

**Files:**
- Create: `strategy-research/experiments/macro_context_shadow/README.md` result section or `results/README.md`
- Test: existing focused tests plus runner smoke test

- [ ] Run the runner against the current data root for 20-day primary horizon.
- [ ] Report sample coverage, reconstructed share, regime balance, and whether strict evidence is eligible.
- [ ] Do not claim alpha where the current data history is insufficient.
- [ ] Run final verification and create a draft PR for review.
