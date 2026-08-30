# A 股基本面特征族与长周期 Shadow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不修改任何生产默认的前提下，把 Value / Quality / Growth 基本面研究整理成唯一 owner contract、可复跑的族级 ablation、20 日主周期与 60 日慢基本面 challenger，并把 fund context 固定为 VQG 的辅助研究变量。

**Architecture:** 采用 provider-first 的跨仓 PR 栈。`market-data-platform` 只稳定暴露估值输入；`alpha-research` 拥有 family 语义、Value 变换、P0/T0 feature-set helper 与 horizon profile；`strategy-research` 只负责编排 frozen experiment、训练/评分、common-intersection 统计、portfolio 调用与 receipt；`portfolio-backtester` 复用现有 `backtest_topk`，仅在实现时确认现有公共 API 无法表达所需低频回放时才补 owner API。最后 `research-workspace` 只同步已经合并的 owner commits 与研究文档。

**Tech Stack:** Python 3.11/3.12、pandas、numpy、DuckDB、PyArrow、XGBoost、statsmodels、pytest、ruff、ty、uv、Git submodules。

**Spec:** `docs/superpowers/specs/2026-08-30-fundamental-family-shadow-design.md`

## Global Constraints

- Production impact 必须保持 `none`：本系列不得修改 `configs/presets/a_share.yml`、`DAILY_WATCH20_FEATURES` 的生产 schema、生产模型参数或自动晋级状态。
- Quality/Growth 必须复用 `alpha_research.daily_watch20_pit_features` 的 strict PIT 实现，继续要求 `provenance_policy=require_observed`、`revision_safe=true`、`freshness_verified=true`、observation age <= 3 天、report age <= 250 天、exact-date as-of 与完整 lineage。
- Value family 固定覆盖 PB、PE_TTM、PS_TTM 三个尺度；非有限或非正分母必须产生 null，不允许跨日期 forward-fill。
- `P0` 是当前 production feature anchor；`T0` 必须从 P0 中移除 `value_yield` 与 `earnings_yield`，两者语义不可混淆。
- 主 family arms 固定为 `P0/T0/V/Q/G/VQ/VG/QG/VQG`；`VQG_F` 只能是 auxiliary，不进入主 promotion decision family。
- 20 日是唯一 primary horizon；60 日是 preregistered slow-fundamental challenger；5 日只做 diagnostic。
- 每个 horizon 必须使用单一 horizon label `((horizon, 1.0),)`，训练 purging 以 `forward_label_end_date` 为准，embargo 分别为 5/20/60 个交易日。
- 所有 arm 在同一 horizon 下必须共享相同训练日期、evaluation keys、universe、模型参数、sample-weight policy、缺失值策略、portfolio construction 与成本。
- 使用 `trade_date <= 2026-08-30` 的输出必须固定 `eligible_as_new_oos_evidence=false`、`evidence_class=retrospective_diagnostic`。
- prospective evidence 的机器起点为 `max(2026-08-31, policy_frozen_at 后第一个未观察交易日)`，禁止倒填 OOS 身份。
- fund history 缺少完整 vintage ladder 时必须记录 `revision_safe=false`，`VQG_F` 永远不得因为该历史回放获得 production eligibility。
- 任何 family/PIT/evaluation-key/horizon/receipt 门禁失败必须 fail closed，并写 blocked receipt；不得静默跳过。
- Provider PR 必须先于 consumer PR 合并；consumer 仓 pin 只指向已合并 owner commit；workspace gitlink 只同步已合并 commit。

---

## File / PR map

### PR A1 — `market-data-platform`: valuation research input

- Modify: `src/market_data_platform/research_views/daily_watch20_data.py`
- Create: `tests/test_daily_watch20_research_view.py`

### PR A2 — `alpha-research`: fundamental family contract

- Create: `src/alpha_research/daily_watch20_fundamental_families.py`
- Create: `tests/test_daily_watch20_fundamental_families.py`
- Modify: `tests/test_daily_watch20_pit_features.py`
- Modify: `pyproject.toml`, `uv.lock`

### PR B — `strategy-research`: V/Q/G 20d primary + 5d diagnostic

- Create: `experiments/fundamental_family_shadow/__init__.py`
- Create: `experiments/fundamental_family_shadow/experiment.yml`
- Create: `experiments/fundamental_family_shadow/contract.py`
- Create: `experiments/fundamental_family_shadow/evidence.py`
- Create: `experiments/fundamental_family_shadow/run_family_shadow.py`
- Create: `experiments/fundamental_family_shadow/README.md`
- Create focused tests under `tests/test_fundamental_family_shadow_*.py`
- Modify dependency pins only after owner PRs merge.

### PR C — `strategy-research`: 60d + fund auxiliary

- Extend the same experiment, keeping `VQG_F` auxiliary-only.

### Conditional provider PR — `portfolio-backtester`

Only if a focused probe proves current public `backtest_topk(...)` cannot express horizon-aligned equal-weight Top-K replay with explicit `rebalance_dates` and cost stress. Expected path: no extra PR.

### PR D — `research-workspace`: integration

Update only merged owner gitlinks, roadmap/navigation, governance evidence; no production preset change.

---

### Task 1: Expose `ps_ttm` through the DailyWatch20 data owner

**PR:** A1 (`market-data-platform`)

**Files:**
- Modify: `src/market_data_platform/research_views/daily_watch20_data.py`
- Create: `tests/test_daily_watch20_research_view.py`

**Interfaces:**
- Consumes: existing `DailyWatch20Assets` and `load_daily_watch20_daily(...)`.
- Produces: unchanged function signature; returned frame additionally guarantees `ps_ttm` alongside `pb` and `pe_ttm`, with unique `(trade_date, symbol)` keys and dates inside the requested inclusive range.

- [ ] **Step 1: Write the failing loader-contract test**

Create a temporary `daily/data/part.parquet` with the existing required columns plus `ps_ttm`. Assert an inclusive date query returns `pb`, `pe_ttm`, `ps_ttm` and unique keys.

```python
def test_daily_watch20_loader_exposes_all_three_valuation_inputs(tmp_path: Path) -> None:
    assets = _assets(tmp_path, _rows())
    loaded = load_daily_watch20_daily(assets, start_date="20260828", end_date="20260828")
    assert list(loaded["trade_date"]) == ["20260828"]
    assert loaded.loc[0, ["pb", "pe_ttm", "ps_ttm"]].to_dict() == {
        "pb": 1.5, "pe_ttm": 12.0, "ps_ttm": 2.4,
    }
    assert not loaded.duplicated(["trade_date", "symbol"]).any()
```

- [ ] **Step 2: Run it and verify failure**

```bash
uv run --extra dev python -m pytest tests/test_daily_watch20_research_view.py -q
```

Expected: FAIL because the current query does not select `ps_ttm`.

- [ ] **Step 3: Add `ps_ttm` and explicit result validation**

Add `ps_ttm` to the SQL projection. Add a private validator that requires `trade_date/symbol/pb/pe_ttm/ps_ttm`, rejects duplicate stock-date rows, and rejects any returned date outside `[start_date, end_date]`.

```python
def _validate_daily_watch20_daily_result(frame: pd.DataFrame, *, start_date: str, end_date: str) -> pd.DataFrame:
    required = {"trade_date", "symbol", "pb", "pe_ttm", "ps_ttm"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"DailyWatch20 daily result is missing columns: {missing}")
    if frame.duplicated(["trade_date", "symbol"]).any():
        raise ValueError("DailyWatch20 daily result contains duplicate stock-date rows")
    dates = frame["trade_date"].astype(str)
    if dates.lt(start_date).any() or dates.gt(end_date).any():
        raise ValueError("DailyWatch20 daily result escaped the requested date range")
    return frame
```

- [ ] **Step 4: Add duplicate-key fail-closed coverage**

```python
def test_daily_watch20_loader_rejects_duplicate_stock_date_rows(tmp_path: Path) -> None:
    duplicated = pd.concat([_rows().iloc[[0]], _rows().iloc[[0]]], ignore_index=True)
    assets = _assets(tmp_path, duplicated)
    with pytest.raises(ValueError, match="duplicate stock-date"):
        load_daily_watch20_daily(assets, start_date="20260828", end_date="20260828")
```

- [ ] **Step 5: Run A1 gates**

```bash
uv run --extra dev python -m pytest tests/test_daily_watch20_research_view.py -q
uv run --extra dev ruff check src/market_data_platform/research_views/daily_watch20_data.py tests/test_daily_watch20_research_view.py
uv run --extra dev ty check
```

- [ ] **Step 6: Commit**

```bash
git add src/market_data_platform/research_views/daily_watch20_data.py tests/test_daily_watch20_research_view.py
git commit -m "feat: expose DailyWatch20 sales valuation input"
```

---

### Task 2: Define the canonical family registry and Value feature panel

**PR:** A2 (`alpha-research`) after A1 merges.

**Files:**
- Create: `src/alpha_research/daily_watch20_fundamental_families.py`
- Create: `tests/test_daily_watch20_fundamental_families.py`
- Modify: `tests/test_daily_watch20_pit_features.py`

**Interfaces:**
- Consumes: `QUALITY_FEATURES`, `GROWTH_FEATURES` from the existing PIT owner module.
- Produces: `FUNDAMENTAL_FAMILY_SCHEMA`, `VALUE_FEATURES`, `STYLE_CONTROL_FEATURES`, `FUND_CONTEXT_FEATURES`, `ValueFeaturePanel`, `fundamental_family_registry()`, `build_value_feature_panel()`.

- [ ] **Step 1: Write the failing registry test**

```python
def test_family_registry_reuses_canonical_qg_and_has_no_overlap() -> None:
    registry = fundamental_family_registry()
    assert FUNDAMENTAL_FAMILY_SCHEMA == "daily_watch20.fundamental_families.research.v1"
    assert registry["quality"] == QUALITY_FEATURES
    assert registry["growth"] == GROWTH_FEATURES
    assert registry["value"] == VALUE_FEATURES
    names = [name for family in ("value", "quality", "growth") for name in registry[family]]
    assert len(names) == len(set(names))
```

- [ ] **Step 2: Run and verify import failure**

```bash
uv run --extra dev python -m pytest tests/test_daily_watch20_fundamental_families.py -q
```

- [ ] **Step 3: Implement registry definitions without duplicating Q/G**

```python
FUNDAMENTAL_FAMILY_SCHEMA = "daily_watch20.fundamental_families.research.v1"
VALUE_FEATURES = (
    "value_book_yield_pct",
    "value_earnings_yield_pct",
    "value_sales_yield_pct",
)
STYLE_CONTROL_FEATURES = ("size_pct", "liquidity_pct", "low_volatility_pct")
FUND_CONTEXT_FEATURES = (
    "fund_crowding_level", "fund_ownership_change", "fund_holder_count_change",
    "fund_low_crowding_accumulation", "fund_top10_concentration",
    "fund_accumulation_without_crowding",
)
```

`fundamental_family_registry()` returns Q/G constants imported from `daily_watch20_pit_features`, never copied strings.

- [ ] **Step 4: Add failing Value transform tests**

Test PB/PE/PS positive finite denominators, same-date percentile ranks, null for `<=0/inf/nan`, required columns, and receipt fields `forward_fill=False`, `status=research_only`.

- [ ] **Step 5: Implement `build_value_feature_panel`**

Use source map `{book: pb, earnings: pe_ttm, sales: ps_ttm}`. Convert numeric, replace infinities with null, require positive denominator, invert, then same-date percentile rank. Return coverage by date and a research-only receipt.

- [ ] **Step 6: Pin Q/G parity**

Extend `tests/test_daily_watch20_pit_features.py` so registry Q/G members are exactly the existing constants.

- [ ] **Step 7: Run focused tests**

```bash
uv run --extra dev python -m pytest tests/test_daily_watch20_fundamental_families.py tests/test_daily_watch20_pit_features.py -q
```

---

### Task 3: Add P0/T0 arm builder and frozen horizon profiles

**PR:** A2 (`alpha-research`)

**Interfaces:**
- Produces `family_ablation_feature_sets(production_features)` and `fundamental_horizon_profiles()`.

- [ ] **Step 1: Write P0/T0/arm tests**

```python
def test_ablation_baseline_removes_existing_value_features_without_mutating_p0() -> None:
    production = ("mom_20", "value_yield", "earnings_yield", "size_pct")
    sets = family_ablation_feature_sets(production)
    assert sets["P0"] == production
    assert sets["T0"] == ("mom_20", "size_pct")
    assert set(sets) == {"P0", "T0", "V", "Q", "G", "VQ", "VG", "QG", "VQG"}
```

- [ ] **Step 2: Implement arm construction**

Remove only frozen anchor features `{value_yield, earnings_yield}` from T0; append family tuples in deterministic order; reject duplicates in every arm.

- [ ] **Step 3: Write 5/20/60 profile tests**

Each profile must have role diagnostic/primary/slow_challenger, `label_horizon_weights=((h,1.0),)`, `forward_days=h`, `embargo_trade_days=h`, `rebalance_trade_days=h`.

- [ ] **Step 4: Implement `FundamentalHorizonProfile` and profiles**

Training purging remains based on `forward_label_end_date`; embargo is not a replacement for label maturity.

- [ ] **Step 5: Prove `DailyWatch20FeatureConfig` accepts all three single horizons**

Assert label columns become `forward_rank_5d/20d/60d` and returns match.

- [ ] **Step 6: Update A1 dependency pin and run A2 full gates**

```bash
uv lock
uv run --extra dev python -m pytest tests/test_daily_watch20_fundamental_families.py tests/test_daily_watch20_pit_features.py tests/test_daily_watch20_features.py tests/test_daily_watch20.py -q
uv run --extra dev ruff check src tests
uv run --extra dev ty check
```

- [ ] **Step 7: Commit**

```bash
git add src/alpha_research/daily_watch20_fundamental_families.py tests pyproject.toml uv.lock
git commit -m "feat: define DailyWatch20 fundamental families"
```

---

### Task 4: Freeze the strategy-research contract before results exist

**PR:** B (`strategy-research`)

**Files:** create experiment package, `experiment.yml`, `contract.py`, config tests.

- [ ] **Step 1: Write frozen config tests**

Assert experiment id, lifecycle `research_shadow`, production false, arms exactly nine, horizons 20/5/60, new OOS floor `2026-08-31`, and no VQG_F among main arms.

- [ ] **Step 2: Run and verify import failure**

```bash
uv run --extra dev python -m pytest tests/test_fundamental_family_shadow_config.py -q
```

- [ ] **Step 3: Create frozen YAML**

```yaml
schema_version: fundamental_family_shadow.v1
experiment_id: fundamental_family_shadow_v1
lifecycle: research_shadow
production_eligible: false
automatic_promotion_allowed: false
main_arms: [P0, T0, V, Q, G, VQ, VG, QG, VQG]
primary_horizon: 20
diagnostic_horizon: 5
slow_horizon: 60
new_oos_floor: "2026-08-31"
portfolio:
  top_k: 20
  weighting: equal
  cost_stress_bps: [10, 20, 30, 50]
statistics:
  multiple_testing: holm
  alpha: 0.10
  overlapping_return_inference: hac_or_block_bootstrap
```

- [ ] **Step 4: Resolve P0 through the public strategy-app fundamental contract**

Use `fundamental_shadow_feature_sets()["Q0"]`, then pass that tuple into alpha’s `family_ablation_feature_sets()`. This preserves dependency direction.

- [ ] **Step 5: Commit the frozen contract before running history**

```bash
git commit -m "research: freeze fundamental family shadow contract"
```

---

### Task 5: Pin the public portfolio replay boundary

**PR:** B.

- [ ] **Step 1: Write a public `portfolio_backtester.backtest_topk` smoke test**

Use explicit `rebalance_dates=list(dates[::20])`, `top_k=2`, `weighting="equal"`, `cost_bps=30` on synthetic prices/scores and assert non-null result.

- [ ] **Step 2: Run probe**

```bash
uv run --extra dev python -m pytest tests/test_fundamental_family_shadow_portfolio_api.py -q
```

- [ ] **Step 3: Decision gate**

If it passes, no portfolio PR. If it fails due missing public capability, stop B and add only that missing capability in a provider-first portfolio PR. Never implement generic replay in research.

- [ ] **Step 4: Commit the boundary test**

---

### Task 6: Implement evidence identity and blocked receipts

**PR:** B.

**Files:** `evidence.py`, evidence tests.

- [ ] **Step 1: Test retrospective identity**

Any evaluation date <= 2026-08-30 must yield `retrospective_diagnostic` and `eligible_as_new_oos_evidence=False`.

- [ ] **Step 2: Test policy-freeze-derived OOS start**

`new_oos_start` must be at least 2026-08-31 and strictly after `observed_through` at freeze.

- [ ] **Step 3: Implement immutable `EvidenceIdentity`**

Store evidence class, eligibility, new OOS start, policy frozen timestamp.

- [ ] **Step 4: Implement blocked receipt**

Always set `status=blocked`, production/default false, automatic promotion false, new OOS false, plus reason and lineage.

- [ ] **Step 5: Implement content-addressed run directories**

Hash sorted frozen config + lineage + identity. Refuse overwrite.

- [ ] **Step 6: Run tests and commit**

---

### Task 7: Compose features and score nine main arms on common keys

**PR:** B.

- [ ] **Step 1: Test joins by `(trade_date, symbol)`, not row position**

Shuffle Value rows and assert correct symbol mapping after merge.

- [ ] **Step 2: Implement one-to-one keyed composition**

Reject duplicate keys and overlapping non-key columns.

- [ ] **Step 3: Test common finite intersection**

A NaN score in any compared arm must remove that key from the main paired comparison set.

- [ ] **Step 4: Implement arm scoring using public `DailyWatch20Ranker`**

Within one horizon, configs may differ only by `features`. Use same model params, labels, sample weights and dates.

- [ ] **Step 5: Add monkeypatch config-parity test**

Record constructed ranker configs and assert equality of all fields except features.

- [ ] **Step 6: Run tests and commit**

---

### Task 8: Add 20d primary + 5d diagnostic evaluation

**PR:** B.

- [ ] **Step 1: Freeze horizon role checks**

Primary mode rejects horizon !=20; diagnostic mode is 5 only.

- [ ] **Step 2: Derive rebalance dates from observed trade-date positions**

No calendar-day arithmetic.

- [ ] **Step 3: Compute common-key Rank IC, Top20 return, matched equal-weight benchmark and active return**

All paired comparisons use the same key set.

- [ ] **Step 4: Call owner `backtest_topk` under 10/20/30/50 bps stress**

Do not reimplement turnover/execution accounting locally.

- [ ] **Step 5: Add paired HAC inference and Holm correction**

Use `statsmodels` HAC with `maxlags=horizon`; apply Holm only to the frozen main-arm family.

- [ ] **Step 6: Write mandatory artifacts and receipt**

`experiment.yml`, `frozen_config.json`, `family_registry.json`, `feature_coverage.parquet`, `scores.parquet`, `portfolio_daily.parquet`, `paired_metrics.parquet`, `window_metrics.parquet`, `regime_metrics.parquet`, `lineage.json`, `receipt.json`.

- [ ] **Step 7: Assert production constants are unchanged**

Snapshot `tuple(DAILY_WATCH20_FEATURES)` before/after test runner and assert exact equality; receipt production flags false.

- [ ] **Step 8: Document exact CLI examples and run PR B gates**

```bash
uv run --extra dev python -m pytest tests/test_fundamental_family_shadow_config.py tests/test_fundamental_family_shadow_evidence.py tests/test_fundamental_family_shadow_portfolio_api.py tests/test_fundamental_family_shadow_runner.py -q
uv run --extra dev ruff check experiments/fundamental_family_shadow tests
uv run --extra dev ty check
```

- [ ] **Step 9: Update merged owner pins, commit and open PR B**

---

### Task 9: Add preregistered 60d slow-fundamental support

**PR:** C.

- [ ] **Step 1: Freeze distinct policy ids for 5d/20d/60d before running 60d**
- [ ] **Step 2: Add synthetic leakage test proving rows whose `forward_label_end_date` reaches the evaluation period never enter 60d training**
- [ ] **Step 3: Reuse the same `run_horizon` implementation; only the profile changes**
- [ ] **Step 4: Assert 60d remains slow challenger and cannot replace 20d primary by config accident**
- [ ] **Step 5: Run focused tests and commit `research: preregister 60d fundamental challenger`**

---

### Task 10: Add fund context only as `VQG_F`

**PR:** C.

- [ ] **Step 1: Freeze `auxiliary_arms: [VQG_F]` and keep it outside `main_arms`**
- [ ] **Step 2: Implement only pure disclosed-date feature composition from current-main owner inputs**

Require `available_date <= trade_date`, no forward fill, unique stock/date, six registered outputs. Do not cherry-pick the closed PR wholesale.

- [ ] **Step 3: Test non-revision-safe fund history forces `exploratory_only` and production false**
- [ ] **Step 4: Compare VQG_F to VQG only on identical common keys; report coverage loss**
- [ ] **Step 5: Keep auxiliary p-values outside the primary Holm family**
- [ ] **Step 6: Add a guard proving runtime code has no branch/SHA dependency on closed PR #251**
- [ ] **Step 7: Run C gates and commit**

---

### Task 11: Add prospective-mode guardrails without claiming evidence exists

**PR:** C.

- [ ] **Step 1: Test prospective mode rejects any pre-start date**
- [ ] **Step 2: Make prospective runs all-or-nothing; no mixed retrospective/prospective run**
- [ ] **Step 3: Record `policy_frozen_at`, `observed_through_at_freeze`, `new_oos_start`, eligibility in receipt**
- [ ] **Step 4: Document that code readiness is not prospective evidence**
- [ ] **Step 5: Run evidence tests and commit**

---

### Task 12: Run retrospective smoke campaigns without changing thresholds

**After PR B/C code is final.**

- [ ] **Step 1: Run 20d retrospective**

```bash
PYTHONPATH=. uv run --extra dev python -m experiments.fundamental_family_shadow.run_family_shadow --data-root "$DATA_PLATFORM_ROOT" --horizon 20 --evidence-mode retrospective --output-root /tmp/fundamental-family-shadow-20d
```

- [ ] **Step 2: Run 5d diagnostic**
- [ ] **Step 3: Run 60d retrospective slow challenger**
- [ ] **Step 4: Inspect governance fields before performance fields**

For all three: evidence retrospective, new OOS false, production false, promotion false.

- [ ] **Step 5: Do not edit thresholds/arms in response to results**

A changed arm/threshold/horizon requires a new experiment version.

---

### Task 13: Integrate merged owner commits into research-workspace

**PR:** D, only after A1/A2/B/C merge.

- [ ] **Step 1: Verify each candidate SHA is reachable from owner `main`**
- [ ] **Step 2: Update gitlinks in dependency order: MDP → alpha → strategy-research**
- [ ] **Step 3: Update roadmap with separate tooling/evidence/prospective/production statuses**
- [ ] **Step 4: Register experiment in existing navigation/catalog schema**
- [ ] **Step 5: Run docs/catalog/governance/boundary gates**

```bash
uv run python -m pytest tests/test_docs_links.py tests/test_strategy_research_catalog.py tests/test_research_spec_check.py -q
python scripts/decision_governance_check.py
```

Also run current-main cross-repo private-import boundary command.

- [ ] **Step 6: Verify `configs/presets/a_share.yml` has no diff and gitlinks are default-branch-reachable**
- [ ] **Step 7: Commit `research: integrate fundamental family shadow` and open PR D**

---

### Task 14: Final verification before declaring completion

- [ ] **Step 1: A1 green and merged; capture merge SHA**
- [ ] **Step 2: A2 green and merged; pins point to merged A1**
- [ ] **Step 3: B/C green and merged; pins point to merged A1/A2; no PR #251 runtime dependency**
- [ ] **Step 4: D gitlinks point only to merged owner commits**
- [ ] **Step 5: Verify production invariants**

```text
configs/presets/a_share.yml unchanged
DAILY_WATCH20_FEATURES unchanged
production_default_changed=false
automatic_promotion_allowed=false
```

- [ ] **Step 6: Verify evidence semantics**

Any run covering dates <=2026-08-30 remains retrospective; no PR/report calls it new/final OOS.

- [ ] **Step 7: Report four statuses separately**

1. code/tooling completion;
2. retrospective findings;
3. prospective OOS status;
4. production eligibility.
