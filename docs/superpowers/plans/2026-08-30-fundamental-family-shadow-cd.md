# Fundamental Family Shadow PR C + D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 PR B 的九臂基本面 family shadow 基础上，预注册并启用 60 日慢基本面 challenger、仅作为辅助的 `VQG_F` fund-context arm、机器可检查的 prospective evidence gate；随后在所有 owner PR 合并后同步 `research-workspace` gitlinks 和研究治理文档。

**Architecture:** PR C 继续复用 PR B 的 runner 和 evidence 模块，不复制 20d 逻辑。60d 只新增冻结 policy identity 并通过 A2 horizon profile 驱动同一执行路径。Fund context 在 `strategy-research` 只做披露后可见状态的纯 feature composition，数据 provenance/read contracts 必须来自已合并 owner API；`VQG_F` 与 VQG 在相同 keys 上做辅助比较，并完全退出主 Holm/promotion family。PR D 只同步已经合并且可从默认分支到达的 owner SHAs。

**Tech Stack:** Python >=3.12、pandas、numpy、statsmodels、PyYAML、pytest、ruff、ty、uv、Git submodules；owner packages 同 PR B。

**Spec:** `docs/superpowers/specs/2026-08-30-fundamental-family-shadow-design.md`

## Global Constraints

- PR C 不得改变 PR B 的九个 `main_arms`。
- `VQG_F` 固定只出现在 `auxiliary_arms`。
- 60d policy id 必须在任何 60d 结果被读取前提交并冻结。
- 60d 通过 A2 `FundamentalHorizonProfile` 驱动相同 runner，`forward_days=60`、single horizon label、`embargo_trade_days=60`、`rebalance_trade_days=60`。
- 60d 永远是 `slow_challenger`，20d 仍是 primary。
- Fund features 必须满足 `available_date <= trade_date`，无 forward fill，stock/date 唯一。
- Fund source 缺完整 vintage ladder 时 `revision_safe=false`，fund evidence 只能 `exploratory_only`。
- `VQG_F` 只与 `VQG` 在完全相同 common keys 上比较，不能和 T0 使用另一套样本。
- Auxiliary p-values 不进入 PR B 的主 Holm family。
- Runtime 源代码不得依赖 closed PR #251 branch 名或该 branch-only SHA。
- Prospective run 必须 all-or-nothing；混合 retrospective/prospective 日期直接拒绝。
- `new_oos_start=max(2026-08-31, observed_through_at_freeze 后第一个未观察交易日)`。
- 实现 runner 并不等于产生 prospective evidence。
- PR D 只能指向 owner 默认分支可达的 merge SHAs；不得同步 PR-head-only SHA。
- 生产 preset、生产 feature tuple、自动晋级状态保持不变。

---

## PR C — `strategy-research`: 60d + fund auxiliary + prospective guard

### Task 1: Freeze the 60d policy identity before any 60d execution

**Files:**
- Modify: `experiments/fundamental_family_shadow/experiment.yml`
- Modify: `experiments/fundamental_family_shadow/contract.py`
- Modify: `tests/test_fundamental_family_shadow_config.py`

**Interfaces:**
- Existing: `resolve_horizon_profile(60)` from PR B contract, backed by A2 alpha profile.
- Produces config policy key: `policies.slow_60d = fundamental_family_shadow.60d.v1`.

- [ ] **Step 1: Write the failing 60d policy test**

```python
def test_slow_60d_policy_is_frozen_without_changing_primary_horizon() -> None:
    config = load_config()
    assert config["primary_horizon"] == 20
    assert config["slow_horizon"] == 60
    assert config["policies"]["primary_20d"] == "fundamental_family_shadow.20d.v1"
    assert config["policies"]["diagnostic_5d"] == "fundamental_family_shadow.5d.v1"
    assert config["policies"]["slow_60d"] == "fundamental_family_shadow.60d.v1"
    assert resolve_horizon_profile(60).role == "slow_challenger"
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
uv run --extra dev python -m pytest \
  tests/test_fundamental_family_shadow_config.py::test_slow_60d_policy_is_frozen_without_changing_primary_horizon -q
```

Expected: FAIL because PR B config intentionally has no `slow_60d` policy key.

- [ ] **Step 3: Add the frozen policy id to YAML**

Change:

```yaml
policies:
  primary_20d: fundamental_family_shadow.20d.v1
  diagnostic_5d: fundamental_family_shadow.5d.v1
```

to:

```yaml
policies:
  primary_20d: fundamental_family_shadow.20d.v1
  diagnostic_5d: fundamental_family_shadow.5d.v1
  slow_60d: fundamental_family_shadow.60d.v1
```

- [ ] **Step 4: Extend `load_config` validation**

Require exact policy mapping:

```python
_EXPECTED_POLICIES = {
    "primary_20d": "fundamental_family_shadow.20d.v1",
    "diagnostic_5d": "fundamental_family_shadow.5d.v1",
    "slow_60d": "fundamental_family_shadow.60d.v1",
}

if payload.get("policies") != _EXPECTED_POLICIES:
    raise ValueError("fundamental family shadow policy identities are not frozen")
```

- [ ] **Step 5: Run config tests**

```bash
uv run --extra dev python -m pytest tests/test_fundamental_family_shadow_config.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit before running 60d**

```bash
git add \
  experiments/fundamental_family_shadow/experiment.yml \
  experiments/fundamental_family_shadow/contract.py \
  tests/test_fundamental_family_shadow_config.py
git commit -m "research: preregister 60d fundamental challenger"
```

This commit SHA is part of `policy_frozen_at` lineage. Do not execute historical 60d before this commit exists.

---

### Task 2: Enable 60d through the same runner and prove horizon-aware leakage protection

**Files:**
- Modify: `experiments/fundamental_family_shadow/run_family_shadow.py`
- Modify: `tests/test_fundamental_family_shadow_runner.py`

**Interfaces:**
- Reuses PR B `run_horizon` / scoring/evaluation functions.
- Produces execution support for horizon 60; no forked `run_60d.py`.

- [ ] **Step 1: Replace PR B horizon rejection with exact allowed set**

The runner-level validator becomes:

```python
def _validate_executable_horizon(horizon: int, config: Mapping[str, Any]) -> None:
    allowed = {
        int(config["diagnostic_horizon"]),
        int(config["primary_horizon"]),
        int(config["slow_horizon"]),
    }
    if horizon not in allowed:
        raise ValueError(f"unsupported fundamental family horizon: {horizon}")
```

- [ ] **Step 2: Write a 60d ranker-config test**

```python
def test_60d_runner_uses_slow_profile_without_changing_shared_ranker_settings() -> None:
    profile = resolve_horizon_profile(60)
    config = build_ranker_config(
        resolve_arm_feature_sets()["VQG"],
        profile=profile,
        settings=RankerSettings(),
    )
    assert profile.role == "slow_challenger"
    assert config.forward_days == 60
    assert config.label_horizon_weights == ((60, 1.0),)
    assert config.label_col == "forward_rank_60d"
    assert config.forward_return_col == "forward_return_60d"
```

- [ ] **Step 3: Write a synthetic label-maturity purge test**

Use the real public `DailyWatch20Ranker.fit` behavior with `fit_model` monkeypatched to capture training rows. Build at least 75 observed dates. Add valid `forward_rank_60d` and explicit `forward_label_end_date` such that only rows whose label end is strictly before `as_of_date` can train.

```python
def test_60d_training_drops_rows_whose_label_end_reaches_as_of_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = pd.bdate_range("2026-01-02", periods=80)
    frame = _ranker_training_frame(dates, horizon=60)
    captured: dict[str, pd.DataFrame] = {}

    monkeypatch.setattr(daily_watch20, "build_model", lambda *_args: object())

    def capture_fit(model: object, _model_type: str, train_data: pd.DataFrame, **_kwargs: object) -> object:
        captured["train"] = train_data.copy()
        return model

    monkeypatch.setattr(daily_watch20, "fit_model", capture_fit)
    ranker = DailyWatch20Ranker(
        build_ranker_config(
            ("f1",),
            profile=resolve_horizon_profile(60),
            settings=RankerSettings(train_window_dates=None),
        )
    )

    as_of = dates[-1]
    ranker.fit(frame, as_of_date=as_of)

    assert (captured["train"]["forward_label_end_date"] < as_of).all()
```

Implement `_ranker_training_frame` in the test file with two symbols per date, a finite `f1`, `forward_rank_60d`, and `forward_label_end_date` shifted 60 observed dates.

- [ ] **Step 4: Run 60d focused runner tests**

```bash
uv run --extra dev python -m pytest \
  tests/test_fundamental_family_shadow_config.py \
  tests/test_fundamental_family_shadow_runner.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit 60d execution support**

```bash
git add \
  experiments/fundamental_family_shadow/run_family_shadow.py \
  tests/test_fundamental_family_shadow_runner.py
git commit -m "research: enable 60d fundamental shadow execution"
```

---

### Task 3: Add pure fund-context feature composition with disclosed-date guards

**Files:**
- Create: `experiments/fundamental_family_shadow/fund_context.py`
- Create: `tests/test_fundamental_family_shadow_fund_context.py`

**Interfaces:**
- Consumes a current-main owner-provided fund feature frame that already carries disclosed-state fields.
- Produces:
  - `build_fund_context_features(frame: pd.DataFrame, *, require_available_date: bool = True, quantile_count: int = 5) -> pd.DataFrame`
  - exactly six `FUND_CONTEXT_FEATURES` columns from A2.

- [ ] **Step 1: Write available-date failure test**

```python
import pandas as pd
import pytest

from experiments.fundamental_family_shadow.fund_context import build_fund_context_features


def test_fund_context_rejects_future_available_date() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-08-28"]),
            "available_date": pd.to_datetime(["2026-08-31"]),
            "symbol": ["A"],
            "fund_hold_mv_to_float_mv": [0.02],
        }
    )
    with pytest.raises(ValueError, match="available_date"):
        build_fund_context_features(frame)
```

- [ ] **Step 2: Write duplicate-key failure test**

```python
def test_fund_context_rejects_duplicate_stock_date_rows() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-08-28", "2026-08-28"]),
            "available_date": pd.to_datetime(["2026-08-28", "2026-08-28"]),
            "symbol": ["A", "A"],
            "fund_hold_mv_to_float_mv": [0.02, 0.02],
        }
    )
    with pytest.raises(ValueError, match="duplicate stock-date"):
        build_fund_context_features(frame)
```

- [ ] **Step 3: Write exact output-feature test**

Use five symbols on one date with `fund_hold_mv_to_float_mv`, `fund_hold_mv_to_float_mv_qoq_change`, `fund_count_holding_stock_qoq_change`, and `fund_top10_hold_mv_to_float_mv`. Assert the result contains all and only the six registered fund-context output columns in addition to input columns, and no forward-filled dates are created.

- [ ] **Step 4: Implement guarded composition**

```python
from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from alpha_research.daily_watch20_fundamental_families import FUND_CONTEXT_FEATURES


def build_fund_context_features(
    frame: pd.DataFrame,
    *,
    require_available_date: bool = True,
    quantile_count: int = 5,
) -> pd.DataFrame:
    required = {"trade_date", "symbol", "fund_hold_mv_to_float_mv"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"fund context frame missing columns: {missing}")
    out = frame.copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="raise").dt.normalize()
    if out.duplicated(["trade_date", "symbol"]).any():
        raise ValueError("fund context frame contains duplicate stock-date rows")
    if require_available_date:
        if "available_date" not in out.columns:
            raise ValueError("fund context frame requires available_date")
        available = pd.to_datetime(out["available_date"], errors="coerce").dt.normalize()
        if available.isna().any() or available.gt(out["trade_date"]).any():
            raise ValueError("fund context available_date must be present and not after trade_date")
    if quantile_count < 2:
        raise ValueError("quantile_count must be at least 2")
    # compute the six frozen columns below; do not forward-fill rows across dates
    ...
```

Replace the final comment/ellipsis during implementation with the exact formulas below:

```python
crowd = pd.to_numeric(out["fund_hold_mv_to_float_mv"], errors="coerce")
out["fund_crowding_level"] = crowd
out["fund_ownership_change"] = pd.to_numeric(
    out.get("fund_hold_mv_to_float_mv_qoq_change"), errors="coerce"
)
out["fund_holder_count_change"] = pd.to_numeric(
    out.get("fund_count_holding_stock_qoq_change"), errors="coerce"
)
```

For absent optional source columns, explicitly assign `float("nan")` rather than passing `None` to `pd.to_numeric`.

Use a private `_safe_ntile(values, frame, quantile_count)` that ranks within `trade_date` with `method="first", pct=True`, maps to integer tiles 1..quantile_count, and preserves nulls. Then:

```python
crowd_q = _safe_ntile(crowd, out, quantile_count)
ownership_q = _safe_ntile(out["fund_ownership_change"], out, quantile_count)
low = crowd_q.le(2)
increasing = ownership_q.ge(quantile_count - 1)
out["fund_low_crowding_accumulation"] = (low & increasing).astype(float)
```

If `fund_top10_hold_mv_to_float_mv` is present:

```python
top10 = pd.to_numeric(out["fund_top10_hold_mv_to_float_mv"], errors="coerce")
out["fund_top10_concentration"] = top10.div(crowd.where(crowd > 0)).clip(0.0, 1.0)
```

Else assign NaN. Finally:

```python
out["fund_accumulation_without_crowding"] = (
    low
    & increasing
    & out["fund_top10_concentration"].notna()
    & out["fund_top10_concentration"].le(0.8)
).astype(float)
```

Assert internally that every name in `FUND_CONTEXT_FEATURES` exists before returning.

- [ ] **Step 5: Run fund composition tests**

```bash
uv run --extra dev python -m pytest tests/test_fundamental_family_shadow_fund_context.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add \
  experiments/fundamental_family_shadow/fund_context.py \
  tests/test_fundamental_family_shadow_fund_context.py
git commit -m "research: add disclosed fund context features"
```

---

### Task 4: Freeze `VQG_F` as an auxiliary-only arm

**Files:**
- Modify: `experiments/fundamental_family_shadow/experiment.yml`
- Modify: `experiments/fundamental_family_shadow/contract.py`
- Modify: `tests/test_fundamental_family_shadow_config.py`

**Interfaces:**
- Produces config `auxiliary_arms: [VQG_F]` and `resolve_auxiliary_feature_sets()`.

- [ ] **Step 1: Write auxiliary-only config test**

```python
def test_fund_context_is_auxiliary_only() -> None:
    config = load_config()
    assert config["main_arms"] == ["P0", "T0", "V", "Q", "G", "VQ", "VG", "QG", "VQG"]
    assert config["auxiliary_arms"] == ["VQG_F"]
    assert config["fund_context"]["production_eligible"] is False
    assert config["fund_context"]["primary_holm_family"] is False
```

- [ ] **Step 2: Extend YAML**

```yaml
auxiliary_arms: [VQG_F]
fund_context:
  production_eligible: false
  primary_holm_family: false
  require_available_date: true
  require_revision_safe_for_promotion: true
```

- [ ] **Step 3: Implement auxiliary feature-set resolution**

```python
from alpha_research.daily_watch20_fundamental_families import FUND_CONTEXT_FEATURES


def resolve_auxiliary_feature_sets() -> dict[str, tuple[str, ...]]:
    main = resolve_arm_feature_sets()
    return {"VQG_F": (*main["VQG"], *FUND_CONTEXT_FEATURES)}
```

Reject duplicate features.

- [ ] **Step 4: Run config tests**

```bash
uv run --extra dev python -m pytest tests/test_fundamental_family_shadow_config.py -q
```

- [ ] **Step 5: Commit**

```bash
git add \
  experiments/fundamental_family_shadow/experiment.yml \
  experiments/fundamental_family_shadow/contract.py \
  tests/test_fundamental_family_shadow_config.py
git commit -m "research: freeze fund context as auxiliary arm"
```

---

### Task 5: Classify fund provenance and keep `VQG_F` outside primary statistics

**Files:**
- Modify: `experiments/fundamental_family_shadow/evidence.py`
- Modify: `experiments/fundamental_family_shadow/run_family_shadow.py`
- Modify: `tests/test_fundamental_family_shadow_fund_context.py`
- Modify: `tests/test_fundamental_family_shadow_runner.py`

**Interfaces:**
- Produces:
  - `classify_fund_context_evidence(audit: Mapping[str, Any]) -> dict[str, Any]`
  - `auxiliary_common_keys(scored_vqg, scored_vqg_f, *, label_col) -> pd.MultiIndex`
  - `auxiliary_paired_metrics(...) -> pd.DataFrame`

- [ ] **Step 1: Write non-revision-safe classification test**

```python
from experiments.fundamental_family_shadow.evidence import classify_fund_context_evidence


def test_non_revision_safe_fund_history_is_exploratory_only() -> None:
    receipt = classify_fund_context_evidence(
        {
            "revision_safe": False,
            "pit_status": "publication_date_pit",
        }
    )
    assert receipt["evidence_class"] == "exploratory_only"
    assert receipt["production_eligible"] is False
    assert receipt["primary_holm_family"] is False
```

- [ ] **Step 2: Implement fund evidence classifier**

```python
def classify_fund_context_evidence(audit: Mapping[str, Any]) -> dict[str, Any]:
    revision_safe = audit.get("revision_safe") is True
    return {
        "revision_safe": revision_safe,
        "pit_status": audit.get("pit_status"),
        "evidence_class": "research_auxiliary" if revision_safe else "exploratory_only",
        "production_eligible": False,
        "primary_holm_family": False,
    }
```

Even revision-safe future fund data remains non-production within this experiment version.

- [ ] **Step 3: Write common-key auxiliary comparison test**

Create VQG scores for A/B/C and VQG_F scores only for A/B. Assert auxiliary common keys are A/B only and the receipt records `coverage_loss_rows=1`.

- [ ] **Step 4: Implement exact VQG-vs-VQG_F intersection**

Reuse PR B’s `common_evaluation_keys` with arm codes `(VQG, VQG_F)` only. Do not reuse the nine-arm main key set because fund coverage may be lower. Save coverage loss versus raw VQG keys as an auxiliary diagnostic.

- [ ] **Step 5: Write Holm-family exclusion test**

Inject a fake `multipletests` into main paired metric computation and run one auxiliary comparison. Assert the fake receives only main-family raw p-values. Auxiliary output may contain raw HAC p-values but no `pvalue_holm_primary` field.

- [ ] **Step 6: Implement separate auxiliary paired metrics artifact section**

Use HAC with the same horizon maxlags for VQG_F minus VQG. Label every row `comparison_family="auxiliary_fund_context"`. Never append those p-values to the primary Holm correction input.

- [ ] **Step 7: Run evidence/runner/fund tests**

```bash
uv run --extra dev python -m pytest \
  tests/test_fundamental_family_shadow_evidence.py \
  tests/test_fundamental_family_shadow_runner.py \
  tests/test_fundamental_family_shadow_fund_context.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add experiments/fundamental_family_shadow tests
git commit -m "research: isolate fund auxiliary evidence"
```

---

### Task 6: Prove the closed fund-crowding branch is not a runtime dependency

**Files:**
- Modify: `tests/test_fundamental_family_shadow_fund_context.py`

- [ ] **Step 1: Add source-scan guard**

```python
from pathlib import Path


def test_runtime_has_no_closed_fund_branch_dependency() -> None:
    root = Path(__file__).parents[1] / "experiments/fundamental_family_shadow"
    runtime = "\n".join(
        path.read_text(encoding="utf-8")
        for path in root.glob("*.py")
    )
    assert "feat/fund-crowding-context-shadow" not in runtime
    assert "fa485b30cfc97893c9f379fce23cc5b9e613d8f1" not in runtime
```

Documentation may cite PR #251 historically; Python runtime may not.

- [ ] **Step 2: Run guard**

```bash
uv run --extra dev python -m pytest \
  tests/test_fundamental_family_shadow_fund_context.py::test_runtime_has_no_closed_fund_branch_dependency -q
```

Expected: PASS.

- [ ] **Step 3: Commit with nearby fund tests if not already committed**

No separate source change is required if the guard passes.

---

### Task 7: Add all-or-nothing prospective evidence mode

**Files:**
- Modify: `experiments/fundamental_family_shadow/evidence.py`
- Modify: `experiments/fundamental_family_shadow/run_family_shadow.py`
- Modify: `tests/test_fundamental_family_shadow_evidence.py`
- Modify: `experiments/fundamental_family_shadow/README.md`

**Interfaces:**
- Produces:
  - `require_prospective_dates(evaluation_dates, *, new_oos_start) -> None`
  - CLI support `--evidence-mode retrospective|prospective`.

- [ ] **Step 1: Write prospective rejection test**

```python
def test_prospective_mode_rejects_any_pre_start_date() -> None:
    with pytest.raises(ValueError, match="predates machine-safe new_oos_start"):
        require_prospective_dates(
            pd.DatetimeIndex(pd.to_datetime(["2026-08-28", "2026-09-01"])),
            new_oos_start=pd.Timestamp("2026-09-01"),
        )
```

- [ ] **Step 2: Implement all-or-nothing date gate**

```python
def require_prospective_dates(
    evaluation_dates: pd.DatetimeIndex,
    *,
    new_oos_start: pd.Timestamp,
) -> None:
    dates = pd.DatetimeIndex(evaluation_dates).normalize()
    if dates.empty:
        raise ValueError("prospective evidence requires evaluation dates")
    if dates.lt(pd.Timestamp(new_oos_start).normalize()).any():
        raise ValueError("prospective evaluation predates machine-safe new_oos_start")
```

- [ ] **Step 3: Freeze receipt lineage fields**

Every successful receipt adds:

```python
{
    "policy_frozen_at": identity.policy_frozen_at,
    "observed_through_at_freeze": observed_through_at_freeze,
    "new_oos_start": identity.new_oos_start.strftime("%Y%m%d"),
    "eligible_as_new_oos_evidence": identity.eligible_as_new_oos_evidence,
}
```

- [ ] **Step 4: Make CLI modes explicit**

If `--evidence-mode prospective`, call `require_prospective_dates` before training/evaluation. If retrospective, explicitly force receipt evidence class to `retrospective_diagnostic` even if all requested dates happen to be after the floor, because the caller selected retrospective mode.

- [ ] **Step 5: Add no-mixing test**

Build one run request containing a date before and after `new_oos_start`, use prospective mode, assert the run blocks before model fitting and writes a blocked receipt.

- [ ] **Step 6: Document non-claim**

README text must state:

```text
Prospective mode only enforces evidence identity. Merging this code does not create prospective OOS evidence. Evidence exists only after unseen post-freeze trading dates are actually scored and evaluated.
```

- [ ] **Step 7: Run evidence tests and commit**

```bash
uv run --extra dev python -m pytest tests/test_fundamental_family_shadow_evidence.py -q
git add \
  experiments/fundamental_family_shadow/evidence.py \
  experiments/fundamental_family_shadow/run_family_shadow.py \
  experiments/fundamental_family_shadow/README.md \
  tests/test_fundamental_family_shadow_evidence.py
git commit -m "research: guard prospective fundamental evidence"
```

---

### Task 8: Run PR C repository gates and open the PR

**Files:**
- No new files beyond Tasks 1-7.

- [ ] **Step 1: Run focused tests**

```bash
uv run --extra dev python -m pytest \
  tests/test_fundamental_family_shadow_config.py \
  tests/test_fundamental_family_shadow_evidence.py \
  tests/test_fundamental_family_shadow_portfolio_api.py \
  tests/test_fundamental_family_shadow_runner.py \
  tests/test_fundamental_family_shadow_fund_context.py -q
```

Expected: PASS.

- [ ] **Step 2: Run lint and type checking**

```bash
uv run --extra dev ruff check experiments/fundamental_family_shadow tests
uv run --extra dev ty check
```

Expected: PASS.

- [ ] **Step 3: Verify main-arm config did not change**

```bash
python - <<'PY'
from experiments.fundamental_family_shadow.contract import load_config
config = load_config()
assert config["main_arms"] == ["P0", "T0", "V", "Q", "G", "VQ", "VG", "QG", "VQG"]
assert config["auxiliary_arms"] == ["VQG_F"]
assert config["primary_horizon"] == 20
assert config["slow_horizon"] == 60
assert config["production_eligible"] is False
PY
```

- [ ] **Step 4: Verify production tuple/preset invariants**

```bash
git diff -- ../strategy-pipeline/configs/presets/a_share.yml || true
python - <<'PY'
from alpha_research.daily_watch20_features import DAILY_WATCH20_FEATURES
assert "value_sales_yield_pct" not in DAILY_WATCH20_FEATURES
assert "pit_quality_roa_pct" not in DAILY_WATCH20_FEATURES
PY
```

Expected: no production feature mutation.

- [ ] **Step 5: Open PR C**

Title:

```text
research: add slow fundamental horizon and fund auxiliary
```

Body must state:

```text
- Adds preregistered 60d slow-challenger execution through the existing runner.
- Keeps 20d as the only primary horizon.
- Adds VQG_F only as an auxiliary fund-context comparison.
- Keeps fund auxiliary outside the primary Holm/promotion family.
- Enforces all-or-nothing prospective evidence identity.
- Does not claim prospective evidence exists yet.
- Does not change production defaults or production feature schema.
```

---

## Retrospective smoke evidence — after PR C code is fixed

### Task 9: Run 20d, 5d, and 60d retrospective campaigns without threshold tuning

**Files:**
- No source changes unless a reproducibility bug is discovered.
- Large parquet artifacts remain outside Git unless current repository policy explicitly tracks them.

- [ ] **Step 1: Run 20d retrospective**

```bash
PYTHONPATH=. uv run --extra dev python -m experiments.fundamental_family_shadow.run_family_shadow \
  --data-root "$DATA_PLATFORM_ROOT" \
  --horizon 20 \
  --evidence-mode retrospective \
  --output-root /tmp/fundamental-family-shadow-20d
```

- [ ] **Step 2: Run 5d diagnostic retrospective**

```bash
PYTHONPATH=. uv run --extra dev python -m experiments.fundamental_family_shadow.run_family_shadow \
  --data-root "$DATA_PLATFORM_ROOT" \
  --horizon 5 \
  --evidence-mode retrospective \
  --output-root /tmp/fundamental-family-shadow-5d
```

- [ ] **Step 3: Run 60d slow-challenger retrospective**

```bash
PYTHONPATH=. uv run --extra dev python -m experiments.fundamental_family_shadow.run_family_shadow \
  --data-root "$DATA_PLATFORM_ROOT" \
  --horizon 60 \
  --evidence-mode retrospective \
  --output-root /tmp/fundamental-family-shadow-60d
```

- [ ] **Step 4: Verify governance fields before reading performance**

```bash
python - <<'PY'
import json
from pathlib import Path

for root in [
    Path("/tmp/fundamental-family-shadow-20d"),
    Path("/tmp/fundamental-family-shadow-5d"),
    Path("/tmp/fundamental-family-shadow-60d"),
]:
    receipts = list(root.glob("*/receipt.json"))
    assert len(receipts) == 1, (root, receipts)
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert receipt["evidence_class"] == "retrospective_diagnostic"
    assert receipt["eligible_as_new_oos_evidence"] is False
    assert receipt["production_default_changed"] is False
    assert receipt["automatic_promotion_allowed"] is False
print("governance identity OK")
PY
```

Only after these assertions pass may returns/IC be inspected.

- [ ] **Step 5: Record results without changing v1 thresholds**

Do not alter arms, cost grid, primary horizon, coverage thresholds or Holm family in response to historical results. Any such change requires `fundamental_family_shadow_v2` with a new frozen config commit.

---

## PR D — `research-workspace`: merge-only integration

### Task 10: Verify all owner SHAs are default-branch reachable before gitlink updates

**Files:**
- No changes yet.

**Interfaces:**
- Consumes merge SHAs for A1 (`market-data-platform`), A2 (`alpha-research`), B/C (`strategy-research`).

- [ ] **Step 1: Fetch each owner default branch**

```bash
git -C market-data-platform fetch origin main
git -C alpha-research fetch origin main
git -C strategy-research fetch origin main
```

- [ ] **Step 2: Prove A1 merge SHA is ancestor of MDP main**

```bash
git -C market-data-platform merge-base --is-ancestor "$A1_SHA" origin/main
```

Expected: exit 0.

- [ ] **Step 3: Prove A2 merge SHA is ancestor of alpha main**

```bash
git -C alpha-research merge-base --is-ancestor "$A2_SHA" origin/main
```

Expected: exit 0.

- [ ] **Step 4: Prove PR C merge SHA is ancestor of strategy-research main**

```bash
git -C strategy-research merge-base --is-ancestor "$C_SHA" origin/main
```

Expected: exit 0. PR C contains B because it is stacked/merged after B; if B and C are independent merge commits, verify both.

- [ ] **Step 5: Stop if any ancestry check fails**

Do not update workspace gitlinks to branch-only commits.

---

### Task 11: Update workspace gitlinks in provider-first dependency order

**Files:**
- Modify gitlink: `market-data-platform`
- Modify gitlink: `alpha-research`
- Modify gitlink: `strategy-research`

- [ ] **Step 1: Checkout A1 merge SHA in MDP submodule**

```bash
git -C market-data-platform checkout "$A1_SHA"
```

- [ ] **Step 2: Checkout A2 merge SHA in alpha submodule**

```bash
git -C alpha-research checkout "$A2_SHA"
```

- [ ] **Step 3: Checkout PR C merge SHA in strategy-research submodule**

```bash
git -C strategy-research checkout "$C_SHA"
```

- [ ] **Step 4: Inspect gitlink-only diff before docs changes**

```bash
git diff --submodule=log -- market-data-platform alpha-research strategy-research
```

Expected: only intended owner ranges.

---

### Task 12: Update roadmap and navigation with separate code/evidence statuses

**Files:**
- Modify: `docs/roadmap.md`
- Modify: `docs/README.md`
- Modify the existing strategy-research catalog/navigation file if current schema requires registration.

**Interfaces:**
- Produces workspace truth that distinguishes tooling completion, retrospective evidence, prospective evidence, and production eligibility.

- [ ] **Step 1: Add a roadmap entry or update the relevant current research line**

Use these four separate fields/statements:

```text
Fundamental family shadow tooling: complete
Historical V/Q/G evidence: retrospective only
Prospective OOS evidence: none yet / accumulating
Production eligibility: false
```

If retrospective smoke outputs were successfully generated, replace only “retrospective only” with their factual receipt status; do not convert to production-ready.

- [ ] **Step 2: Add docs navigation link**

Point to the strategy-research experiment README or workspace design/spec, following the current docs navigation pattern.

- [ ] **Step 3: Register in existing catalog schema only if required**

Use the current `strategy-research/catalog.json` schema and validator. Do not invent `fundamental-catalog.yml` or any parallel registry.

- [ ] **Step 4: Add no claims derived from a future run that has not happened**

If prospective OOS is not yet available, explicitly state that.

---

### Task 13: Run workspace governance and boundary gates

**Files:**
- No additional source unless a docs/catalog consistency issue is discovered.

- [ ] **Step 1: Run focused workspace tests**

```bash
uv run python -m pytest \
  tests/test_docs_links.py \
  tests/test_strategy_research_catalog.py \
  tests/test_research_spec_check.py -q
```

Expected: PASS.

- [ ] **Step 2: Run decision governance**

```bash
python scripts/decision_governance_check.py
```

Expected: PASS.

- [ ] **Step 3: Run current-main cross-repo boundary check**

Locate the command documented by current `docs/roadmap.md` / governance scripts and execute it. The acceptance condition is zero new private cross-repo imports involving the touched owner repos. Do not disable or exclude the new experiment to make it pass.

- [ ] **Step 4: Verify production preset unchanged**

```bash
git diff -- strategy-pipeline/configs/presets/a_share.yml
```

Expected: no diff.

- [ ] **Step 5: Verify workspace gitlinks point at default-branch reachable commits**

Repeat Task 10 ancestry checks against the SHAs currently checked out in each submodule.

---

### Task 14: Commit and open PR D

**Files:**
- Gitlinks + docs/catalog changes from Tasks 11-13.

- [ ] **Step 1: Inspect final workspace diff**

```bash
git diff --submodule=log
```

Expected: only three intended gitlinks plus research docs/catalog; no production config change.

- [ ] **Step 2: Commit**

```bash
git add market-data-platform alpha-research strategy-research docs
# Add catalog file explicitly if changed.
git commit -m "research: integrate fundamental family shadow"
```

- [ ] **Step 3: Open PR D**

Title:

```text
research: integrate fundamental family shadow
```

Body must include:

```text
- Advances only merged/default-branch-reachable owner commits.
- Registers the fundamental family research workflow and docs.
- Separates tooling status, retrospective evidence, prospective OOS status, and production eligibility.
- Does not change the A-share production preset or production feature schema.
```

---

## Final completion verification

### Task 15: Verify the full series before calling it complete

- [ ] **Step 1: A1 merge SHA is on `market-data-platform/main` and A1 tests/CI are green**
- [ ] **Step 2: A2 merge SHA is on `alpha-research/main`, references merged A1, and alpha tests/CI are green**
- [ ] **Step 3: B/C merge SHAs are on `strategy-research/main`, reference merged A1/A2, and focused tests/CI are green**
- [ ] **Step 4: Runtime contains no closed PR #251 branch/SHA dependency**
- [ ] **Step 5: Workspace gitlinks reference only default-branch-reachable owner commits**
- [ ] **Step 6: `strategy-pipeline/configs/presets/a_share.yml` is unchanged**
- [ ] **Step 7: `DAILY_WATCH20_FEATURES` contains no new Value/Q/G research features**
- [ ] **Step 8: All historical smoke receipts through 2026-08-30 are `retrospective_diagnostic` and new-OOS-ineligible**
- [ ] **Step 9: If no unseen post-freeze dates have actually been evaluated, prospective OOS status remains `none yet`**
- [ ] **Step 10: Production eligibility remains false regardless of retrospective performance**

Final reporting must separate:

```text
1. Code/tooling completion
2. Retrospective research findings
3. Prospective OOS evidence status
4. Production eligibility
```
