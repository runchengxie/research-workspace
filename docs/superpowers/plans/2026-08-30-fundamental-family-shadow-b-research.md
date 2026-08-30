# Fundamental Family Shadow PR B Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `strategy-research` 新增冻结的 `fundamental_family_shadow_v1`，完整比较 P0/T0/V/Q/G/VQ/VG/QG/VQG，运行 20 日 primary 与 5 日 diagnostic 的 retrospective research，并输出 common-key、成本、统计与 lineage 产物；不加入 fund auxiliary，也不修改生产默认。

**Architecture:** `strategy-research` 只负责研究编排。P0 从 `strategy-app` 的公开 fundamental-shadow contract 读取；V/Q/G family 与 horizon profile 从 A2 `alpha-research` 读取；训练用公开 `DailyWatch20Ranker`；组合回放用公开 `portfolio_backtester.backtest_topk`。Research 代码只实现冻结配置、key-safe composition、evaluation-date orchestration、研究统计、evidence identity 与 artifact writing，不复制 alpha/portfolio owner 逻辑。

**Tech Stack:** Python >=3.12、pandas、numpy、statsmodels、PyYAML、pytest、ruff、ty、uv；owner packages: alpha-research、market-data-platform、portfolio-backtester、strategy-app。

**Spec:** `docs/superpowers/specs/2026-08-30-fundamental-family-shadow-design.md`

## Global Constraints

- PR B main arms exactly `P0,T0,V,Q,G,VQ,VG,QG,VQG`.
- `VQG_F` does not exist in PR B runtime/config.
- 20d is primary; 5d diagnostic only; 60d remains declared future slow horizon but is not executable until PR C freezes its policy id.
- Historical output through 2026-08-30 is `retrospective_diagnostic`, never new/final OOS.
- Every arm in one horizon uses the same evaluation dates, common finite keys, model params, sample weights, label policy and portfolio settings.
- P0 must be resolved from `strategy_app.daily_watch20.daily_watch20_fundamental_shadow.fundamental_shadow_feature_sets()["Q0"]`.
- Feature families must come from A2 public alpha API.
- Q/G feature values must come from existing strict PIT `FundamentalFeaturePanel` owner API.
- Generic portfolio accounting must go through `portfolio_backtester.backtest_topk`; no local backtest engine.
- All successful/blocked receipts set `production_default_changed=false`, `automatic_promotion_allowed=false`.
- Output directories are content-addressed and immutable.

---

### Task 1: Freeze experiment config and exact arm semantics

**Files:**
- Create: `experiments/fundamental_family_shadow/__init__.py`
- Create: `experiments/fundamental_family_shadow/experiment.yml`
- Create: `experiments/fundamental_family_shadow/contract.py`
- Create: `tests/test_fundamental_family_shadow_config.py`

**Interfaces:**
- Produces:
  - `EXPERIMENT_ID = "fundamental_family_shadow_v1"`
  - `load_config(path: str | Path | None = None) -> dict[str, Any]`
  - `resolve_arm_feature_sets() -> dict[str, tuple[str, ...]]`
  - `resolve_horizon_profile(horizon: int) -> FundamentalHorizonProfile`

- [ ] **Step 1: Write failing config test**

```python
from experiments.fundamental_family_shadow.contract import (
    load_config,
    resolve_arm_feature_sets,
)


def test_fundamental_family_shadow_config_is_frozen_and_non_production() -> None:
    config = load_config()
    assert config["experiment_id"] == "fundamental_family_shadow_v1"
    assert config["lifecycle"] == "research_shadow"
    assert config["production_eligible"] is False
    assert config["automatic_promotion_allowed"] is False
    assert config["main_arms"] == ["P0", "T0", "V", "Q", "G", "VQ", "VG", "QG", "VQG"]
    assert config["primary_horizon"] == 20
    assert config["diagnostic_horizon"] == 5
    assert config["slow_horizon"] == 60
    assert config["new_oos_floor"] == "2026-08-31"
    assert "auxiliary_arms" not in config
    assert set(resolve_arm_feature_sets()) == set(config["main_arms"])
```

- [ ] **Step 2: Run and prove import failure**

```bash
uv run --extra dev python -m pytest \
  tests/test_fundamental_family_shadow_config.py::test_fundamental_family_shadow_config_is_frozen_and_non_production -q
```

Expected: FAIL because experiment package does not exist.

- [ ] **Step 3: Create package identity**

`__init__.py`:

```python
EXPERIMENT_ID = "fundamental_family_shadow_v1"

__all__ = ["EXPERIMENT_ID"]
```

- [ ] **Step 4: Create frozen `experiment.yml`**

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
policies:
  primary_20d: fundamental_family_shadow.20d.v1
  diagnostic_5d: fundamental_family_shadow.5d.v1
portfolio:
  top_k: 20
  weighting: equal
  trading_days_per_year: 252
  cost_stress_bps: [10, 20, 30, 50]
coverage:
  minimum_common_date_ratio: 0.95
  minimum_common_row_ratio: 0.80
statistics:
  multiple_testing: holm
  alpha: 0.10
  overlapping_return_inference: hac
```

Do not add a `slow_60d` policy id until PR C.

- [ ] **Step 5: Implement config validation**

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from alpha_research.daily_watch20_fundamental_families import (
    FundamentalHorizonProfile,
    family_ablation_feature_sets,
    fundamental_horizon_profiles,
)
from strategy_app.daily_watch20.daily_watch20_fundamental_shadow import (
    fundamental_shadow_feature_sets,
)

from . import EXPERIMENT_ID

_MAIN_ARMS = ("P0", "T0", "V", "Q", "G", "VQ", "VG", "QG", "VQG")


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else Path(__file__).with_name("experiment.yml")
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("fundamental family shadow config must be a mapping")
    if payload.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("invalid fundamental family shadow experiment_id")
    if tuple(payload.get("main_arms", ())) != _MAIN_ARMS:
        raise ValueError("fundamental family shadow main arms are not frozen")
    if payload.get("primary_horizon") != 20 or payload.get("diagnostic_horizon") != 5:
        raise ValueError("fundamental family shadow primary/diagnostic horizons are not frozen")
    if payload.get("slow_horizon") != 60:
        raise ValueError("fundamental family shadow slow horizon is not frozen")
    if payload.get("production_eligible") is not False:
        raise ValueError("fundamental family shadow cannot be production eligible")
    if payload.get("automatic_promotion_allowed") is not False:
        raise ValueError("fundamental family shadow cannot auto-promote")
    return payload


def resolve_arm_feature_sets() -> dict[str, tuple[str, ...]]:
    production = tuple(fundamental_shadow_feature_sets()["Q0"])
    return family_ablation_feature_sets(production)


def resolve_horizon_profile(horizon: int) -> FundamentalHorizonProfile:
    profiles = fundamental_horizon_profiles()
    if horizon not in profiles:
        raise ValueError(f"unsupported fundamental family horizon: {horizon}")
    return profiles[horizon]
```

- [ ] **Step 6: Add P0/T0 semantics test**

```python
def test_p0_and_t0_have_distinct_value_semantics() -> None:
    sets = resolve_arm_feature_sets()
    assert "value_yield" in sets["P0"]
    assert "earnings_yield" in sets["P0"]
    assert "value_yield" not in sets["T0"]
    assert "earnings_yield" not in sets["T0"]
```

- [ ] **Step 7: Run config tests**

```bash
uv run --extra dev python -m pytest tests/test_fundamental_family_shadow_config.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit the frozen contract before any historical run**

```bash
git add experiments/fundamental_family_shadow/__init__.py \
  experiments/fundamental_family_shadow/experiment.yml \
  experiments/fundamental_family_shadow/contract.py \
  tests/test_fundamental_family_shadow_config.py
git commit -m "research: freeze fundamental family shadow contract"
```

---

### Task 2: Prove the public portfolio API is sufficient

**Files:**
- Create: `tests/test_fundamental_family_shadow_portfolio_api.py`

**Interfaces:**
- Consumes: `portfolio_backtester.backtest_topk(...)`.
- Produces: a boundary test; no new portfolio code on expected path.

- [ ] **Step 1: Write public API smoke test**

```python
import pandas as pd

from portfolio_backtester import backtest_topk


def test_public_topk_api_accepts_explicit_low_frequency_rebalance_dates() -> None:
    dates = pd.bdate_range("2026-01-02", periods=45)
    rows: list[dict[str, object]] = []
    for date_number, date in enumerate(dates):
        for symbol_number, symbol in enumerate(("A", "B", "C")):
            rows.append(
                {
                    "trade_date": date,
                    "symbol": symbol,
                    "score": float(3 - symbol_number),
                    "close": 10.0 + date_number + symbol_number,
                }
            )
    frame = pd.DataFrame(rows)

    result = backtest_topk(
        frame,
        pred_col="score",
        price_col="close",
        rebalance_dates=list(dates[::20]),
        top_k=2,
        shift_days=1,
        cost_bps=30.0,
        trading_days_per_year=252,
        weighting="equal",
    )

    assert result is not None
```

- [ ] **Step 2: Run probe**

```bash
uv run --extra dev python -m pytest tests/test_fundamental_family_shadow_portfolio_api.py -q
```

Expected: PASS with current public API.

- [ ] **Step 3: Enforce provider-first fallback if probe fails**

If the failure is an API capability gap rather than bad synthetic fixture input, stop PR B. Create a separate `portfolio-backtester` provider PR containing exactly the missing public capability and owner tests. Resume B only after that PR is merged and the strategy-research pin is updated.

- [ ] **Step 4: Commit boundary test**

```bash
git add tests/test_fundamental_family_shadow_portfolio_api.py
git commit -m "test: pin fundamental shadow portfolio boundary"
```

---

### Task 3: Implement evidence identity, blocked receipts, and immutable run directories

**Files:**
- Create: `experiments/fundamental_family_shadow/evidence.py`
- Create: `tests/test_fundamental_family_shadow_evidence.py`

**Interfaces:**
- Produces:
  - `EvidenceIdentity`
  - `classify_evidence(evaluation_dates, *, policy_frozen_at, observed_through) -> EvidenceIdentity`
  - `blocked_receipt(reason, *, experiment_id, lineage) -> dict[str, Any]`
  - `run_directory(output_root, *, frozen_config, lineage, identity) -> Path`

- [ ] **Step 1: Write retrospective identity test**

```python
import pandas as pd

from experiments.fundamental_family_shadow.evidence import classify_evidence


def test_pre_freeze_history_is_never_new_oos() -> None:
    identity = classify_evidence(
        pd.DatetimeIndex([pd.Timestamp("2026-08-28")]),
        policy_frozen_at="2026-08-30T21:00:00+08:00",
        observed_through="2026-08-30",
    )
    assert identity.evidence_class == "retrospective_diagnostic"
    assert identity.eligible_as_new_oos_evidence is False
    assert identity.new_oos_start >= pd.Timestamp("2026-08-31")
```

- [ ] **Step 2: Write machine-safe OOS-start test**

```python
def test_new_oos_start_is_after_observed_through() -> None:
    identity = classify_evidence(
        pd.DatetimeIndex([pd.Timestamp("2026-09-02")]),
        policy_frozen_at="2026-08-31T23:00:00+08:00",
        observed_through="2026-09-01",
    )
    assert identity.new_oos_start == pd.Timestamp("2026-09-02")
```

- [ ] **Step 3: Implement EvidenceIdentity**

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

_NEW_OOS_FLOOR = pd.Timestamp("2026-08-31")


@dataclass(frozen=True)
class EvidenceIdentity:
    evidence_class: str
    eligible_as_new_oos_evidence: bool
    new_oos_start: pd.Timestamp
    policy_frozen_at: str


def classify_evidence(
    evaluation_dates: pd.DatetimeIndex,
    *,
    policy_frozen_at: str,
    observed_through: str,
) -> EvidenceIdentity:
    if evaluation_dates.empty:
        raise ValueError("fundamental family evidence requires evaluation dates")
    observed = pd.Timestamp(observed_through).normalize()
    new_oos_start = max(_NEW_OOS_FLOOR, observed + pd.offsets.BDay(1))
    all_prospective = bool((evaluation_dates.normalize() >= new_oos_start).all())
    return EvidenceIdentity(
        evidence_class="prospective_oos" if all_prospective else "retrospective_diagnostic",
        eligible_as_new_oos_evidence=all_prospective,
        new_oos_start=pd.Timestamp(new_oos_start).normalize(),
        policy_frozen_at=policy_frozen_at,
    )
```

- [ ] **Step 4: Add blocked receipt test**

```python
def test_blocked_receipt_is_always_non_promotable() -> None:
    receipt = blocked_receipt(
        "missing_family_column",
        experiment_id="fundamental_family_shadow_v1",
        lineage={"input": "x"},
    )
    assert receipt["status"] == "blocked"
    assert receipt["eligible_as_new_oos_evidence"] is False
    assert receipt["production_default_changed"] is False
    assert receipt["automatic_promotion_allowed"] is False
```

- [ ] **Step 5: Implement blocked receipt**

```python
def blocked_receipt(
    reason: str,
    *,
    experiment_id: str,
    lineage: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "experiment_id": experiment_id,
        "status": "blocked",
        "reason": reason,
        "lineage": dict(lineage),
        "evidence_class": "blocked",
        "eligible_as_new_oos_evidence": False,
        "production_default_changed": False,
        "automatic_promotion_allowed": False,
    }
```

- [ ] **Step 6: Add content-addressed run-directory test**

```python
def test_run_directory_is_content_addressed_and_refuses_overwrite(tmp_path: Path) -> None:
    identity = classify_evidence(
        pd.DatetimeIndex([pd.Timestamp("2026-08-28")]),
        policy_frozen_at="2026-08-30T21:00:00+08:00",
        observed_through="2026-08-30",
    )
    path = run_directory(
        tmp_path,
        frozen_config={"experiment_id": "x"},
        lineage={"sha": "abc"},
        identity=identity,
    )
    path.mkdir()
    with pytest.raises(FileExistsError):
        run_directory(
            tmp_path,
            frozen_config={"experiment_id": "x"},
            lineage={"sha": "abc"},
            identity=identity,
        )
```

- [ ] **Step 7: Implement deterministic hash**

```python
def run_directory(
    output_root: str | Path,
    *,
    frozen_config: Mapping[str, Any],
    lineage: Mapping[str, Any],
    identity: EvidenceIdentity,
) -> Path:
    payload = {
        "config": dict(frozen_config),
        "lineage": dict(lineage),
        "identity": {
            "evidence_class": identity.evidence_class,
            "eligible_as_new_oos_evidence": identity.eligible_as_new_oos_evidence,
            "new_oos_start": identity.new_oos_start.strftime("%Y%m%d"),
            "policy_frozen_at": identity.policy_frozen_at,
        },
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    path = Path(output_root) / digest
    if path.exists():
        raise FileExistsError(f"fundamental family run already exists: {path}")
    return path
```

- [ ] **Step 8: Run evidence tests and commit**

```bash
uv run --extra dev python -m pytest tests/test_fundamental_family_shadow_evidence.py -q
git add experiments/fundamental_family_shadow/evidence.py tests/test_fundamental_family_shadow_evidence.py
git commit -m "research: enforce fundamental shadow evidence identity"
```

---

### Task 4: Compose base/Value/PIT feature frames by keys and define one common evaluation intersection

**Files:**
- Create: `experiments/fundamental_family_shadow/run_family_shadow.py`
- Create: `tests/test_fundamental_family_shadow_runner.py`

**Interfaces:**
- Produces:
  - `compose_family_feature_frame(base_frame, *, value_frame, pit_frame) -> pd.DataFrame`
  - `common_evaluation_keys(scored_by_arm, *, arm_codes, label_col) -> pd.MultiIndex`

- [ ] **Step 1: Write keyed-join test**

```python
import pandas as pd

from experiments.fundamental_family_shadow.run_family_shadow import (
    compose_family_feature_frame,
)


def test_feature_composition_joins_by_stock_date_not_row_position() -> None:
    base = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-08-28", "2026-08-28"]),
            "symbol": ["A", "B"],
            "mom_20": [1.0, 2.0],
        }
    )
    value = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-08-28", "2026-08-28"]),
            "symbol": ["B", "A"],
            "value_book_yield_pct": [0.5, 1.0],
        }
    )

    joined = compose_family_feature_frame(base, value_frame=value, pit_frame=None)

    assert joined.set_index("symbol").loc["A", "value_book_yield_pct"] == 1.0
```

- [ ] **Step 2: Implement one-to-one merge helper**

```python
_KEY_COLUMNS = ("trade_date", "symbol")


def _validated_extra(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    missing = sorted(set(_KEY_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} frame missing keys: {missing}")
    out = frame.copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="raise").dt.normalize()
    if out.duplicated(list(_KEY_COLUMNS)).any():
        raise ValueError(f"{label} frame contains duplicate stock-date rows")
    return out


def compose_family_feature_frame(
    base_frame: pd.DataFrame,
    *,
    value_frame: pd.DataFrame,
    pit_frame: pd.DataFrame | None,
) -> pd.DataFrame:
    out = _validated_extra(base_frame, label="base")
    for label, extra in (("value", value_frame), ("pit", pit_frame)):
        if extra is None:
            continue
        right = _validated_extra(extra, label=label)
        overlap = (set(out.columns) & set(right.columns)) - set(_KEY_COLUMNS)
        if overlap:
            raise ValueError(f"{label} frame overlaps existing columns: {sorted(overlap)}")
        out = out.merge(right, on=list(_KEY_COLUMNS), how="left", validate="one_to_one")
    return out.sort_values(list(_KEY_COLUMNS), kind="mergesort").reset_index(drop=True)
```

- [ ] **Step 3: Add duplicate/overlap failure tests**

Create one test for duplicate value keys and one for overlapping non-key column `mom_20`; both must raise `ValueError`.

- [ ] **Step 4: Write common-intersection test**

```python
def test_main_arms_use_one_common_finite_key_set() -> None:
    scored = {
        "T0": pd.DataFrame(
            {
                "trade_date": pd.to_datetime(["2026-08-28", "2026-08-28"]),
                "symbol": ["A", "B"],
                "score": [0.1, 0.2],
                "forward_rank_20d": [0.5, 1.0],
            }
        ),
        "V": pd.DataFrame(
            {
                "trade_date": pd.to_datetime(["2026-08-28", "2026-08-28"]),
                "symbol": ["A", "B"],
                "score": [0.3, float("nan")],
                "forward_rank_20d": [0.5, 1.0],
            }
        ),
    }

    keys = common_evaluation_keys(
        scored,
        arm_codes=("T0", "V"),
        label_col="forward_rank_20d",
    )

    assert list(keys) == [(pd.Timestamp("2026-08-28"), "A")]
```

- [ ] **Step 5: Implement common finite keys**

Normalize dates first. For each arm keep rows where both `score` and `label_col` are finite, build a MultiIndex, intersect all indexes, sort, and reject empty intersection.

- [ ] **Step 6: Run composition tests**

```bash
uv run --extra dev python -m pytest \
  tests/test_fundamental_family_shadow_runner.py -q
```

- [ ] **Step 7: Commit**

```bash
git add experiments/fundamental_family_shadow/run_family_shadow.py tests/test_fundamental_family_shadow_runner.py
git commit -m "research: compose fundamental family feature frames"
```

---

### Task 5: Score every main arm with identical non-feature ranker settings

**Files:**
- Modify: `experiments/fundamental_family_shadow/run_family_shadow.py`
- Modify: `tests/test_fundamental_family_shadow_runner.py`

**Interfaces:**
- Produces:
  - `RankerSettings`
  - `build_ranker_config(features, *, profile, settings) -> DailyWatch20Config`
  - `score_family_arms(frame, *, evaluation_dates, feature_sets, profile, settings, ranker_factory=DailyWatch20Ranker) -> dict[str, pd.DataFrame]`

- [ ] **Step 1: Define frozen shared ranker settings**

```python
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RankerSettings:
    train_window_dates: int = 504
    sample_weight_mode: str = "date_equal"
    model_params: Mapping[str, Any] = None

    def resolved_model_params(self) -> dict[str, Any]:
        if self.model_params is not None:
            return dict(self.model_params)
        return {
            "n_estimators": 300,
            "learning_rate": 0.05,
            "max_depth": 3,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 2.0,
            "objective": "rank:pairwise",
            "tree_method": "hist",
            "n_jobs": 3,
            "random_state": 42,
        }
```

When implementing, use `field(default_factory=dict)` rather than mutable/None typing if ty requires it; preserve the exact resolved defaults above.

- [ ] **Step 2: Build ranker config from one horizon profile**

```python
from alpha_research.daily_watch20 import DailyWatch20Config


def build_ranker_config(
    features: tuple[str, ...],
    *,
    profile: FundamentalHorizonProfile,
    settings: RankerSettings,
) -> DailyWatch20Config:
    return DailyWatch20Config(
        features=features,
        forward_days=profile.forward_days,
        label_horizon_weights=profile.label_horizon_weights,
        feature_policy_id="fundamental_family_shadow.features.v1",
        label_policy_id=f"fundamental_family_shadow.{profile.horizon_days}d.v1",
        train_window_dates=settings.train_window_dates,
        sample_weight_mode=settings.sample_weight_mode,
        model_params=settings.resolved_model_params(),
        eligible_for_backtest=True,
        eligible_for_live=False,
    )
```

- [ ] **Step 3: Write config parity test**

```python
def test_arm_ranker_configs_differ_only_by_features() -> None:
    profile = resolve_horizon_profile(20)
    settings = RankerSettings()
    sets = resolve_arm_feature_sets()
    configs = {code: build_ranker_config(features, profile=profile, settings=settings) for code, features in sets.items()}

    reference = configs["T0"]
    for code, config in configs.items():
        assert config.forward_days == reference.forward_days
        assert config.label_horizon_weights == reference.label_horizon_weights
        assert config.label_policy_id == reference.label_policy_id
        assert config.feature_policy_id == reference.feature_policy_id
        assert config.train_window_dates == reference.train_window_dates
        assert config.sample_weight_mode == reference.sample_weight_mode
        assert config.model_params == reference.model_params
        if code != "T0":
            assert config.features != reference.features
```

- [ ] **Step 4: Implement date-by-date scoring**

For each arm and each evaluation date:

```python
ranker = ranker_factory(build_ranker_config(features, profile=profile, settings=settings))
ranker.fit(frame, as_of_date=evaluation_date)
prediction = frame.loc[frame["trade_date"].eq(evaluation_date)]
relative = ranker.predict_relative(prediction).rename(columns={"relative_percentile": "score"})
```

Merge the current horizon label/return columns and required exposure passthrough columns from `prediction` by keys. Add `arm` and `horizon` columns. Never call `fit` without `as_of_date` in this runner.

- [ ] **Step 5: Add fake-ranker orchestration test**

Use a test fake with `fit(frame, as_of_date)` recording date and `predict_relative` returning deterministic percentiles. Assert every arm scores the exact same evaluation dates and `fit` is called with those dates.

- [ ] **Step 6: Run scoring tests and commit**

```bash
uv run --extra dev python -m pytest tests/test_fundamental_family_shadow_runner.py -q
git add experiments/fundamental_family_shadow/run_family_shadow.py tests/test_fundamental_family_shadow_runner.py
git commit -m "research: score fundamental family arms"
```

---

### Task 6: Implement 20d primary and 5d diagnostic evaluation metrics

**Files:**
- Modify: `experiments/fundamental_family_shadow/run_family_shadow.py`
- Modify: `tests/test_fundamental_family_shadow_runner.py`

**Interfaces:**
- Produces:
  - `rebalance_dates_for_horizon(trade_dates, *, horizon, anchor=None) -> pd.DatetimeIndex`
  - `cross_section_metrics(scored_by_arm, *, common_keys, label_col, return_col) -> pd.DataFrame`
  - `paired_hac_metrics(metrics, *, baseline="T0", maxlags) -> pd.DataFrame`

- [ ] **Step 1: Write rebalance-date test**

```python
def test_rebalance_dates_use_observed_trade_positions() -> None:
    dates = pd.DatetimeIndex(pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-07", "2026-01-08", "2026-01-12"]))
    selected = rebalance_dates_for_horizon(dates, horizon=2)
    assert list(selected) == [dates[0], dates[2], dates[4]]
```

- [ ] **Step 2: Implement position-based rebalance dates**

```python
def rebalance_dates_for_horizon(
    trade_dates: pd.DatetimeIndex,
    *,
    horizon: int,
) -> pd.DatetimeIndex:
    if horizon <= 0:
        raise ValueError("rebalance horizon must be positive")
    ordered = pd.DatetimeIndex(trade_dates).normalize().unique().sort_values()
    return ordered[::horizon]
```

- [ ] **Step 3: Write Rank IC / Top20 / benchmark metric test**

Create one synthetic date with 25 names and scores aligned to returns. Assert:

```python
assert row["rank_ic"] > 0.99
assert row["top20_return"] > row["benchmark_return"]
assert row["active_return"] == pytest.approx(row["top20_return"] - row["benchmark_return"])
```

- [ ] **Step 4: Implement cross-sectional metrics on common keys only**

For each arm/date:

```python
rank_ic = group["score"].corr(group[label_col], method="spearman")
top = group.nlargest(20, "score")
top20_return = top[return_col].mean()
benchmark_return = group[return_col].mean()
active_return = top20_return - benchmark_return
```

Also record rows used, symbols selected and `one_way_name_turnover` if previous selected set exists. Portfolio owner outputs remain authoritative for cost/accounting; this simple name-turnover is a diagnostic only and must be labeled as such.

- [ ] **Step 5: Implement HAC paired mean test**

```python
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests


def _hac_mean(values: pd.Series, *, maxlags: int) -> tuple[float, float, float]:
    clean = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if len(clean) <= maxlags + 2:
        return float(clean.mean()), float("nan"), float("nan")
    model = sm.OLS(clean.to_numpy(), np.ones((len(clean), 1))).fit(
        cov_type="HAC",
        cov_kwds={"maxlags": maxlags},
    )
    return float(clean.mean()), float(model.tvalues[0]), float(model.pvalues[0])
```

For each challenger vs T0, pair by trade date and compute deltas for `rank_ic`, `active_return`, and later cost-adjusted portfolio return. Apply Holm to the frozen family of raw p-values and save `pvalue_holm`.

- [ ] **Step 6: Add metric tests for paired dates and Holm column**

Assert mismatched dates raise before inference; assert output contains raw and Holm-adjusted p-values and all main arm codes except baseline.

- [ ] **Step 7: Run metric tests and commit**

```bash
uv run --extra dev python -m pytest tests/test_fundamental_family_shadow_runner.py -q
git add experiments/fundamental_family_shadow/run_family_shadow.py tests/test_fundamental_family_shadow_runner.py
git commit -m "research: evaluate fundamental family cross sections"
```

---

### Task 7: Use portfolio owner API for cost stress and persist mandatory artifacts

**Files:**
- Modify: `experiments/fundamental_family_shadow/run_family_shadow.py`
- Modify: `experiments/fundamental_family_shadow/evidence.py`
- Modify: `tests/test_fundamental_family_shadow_runner.py`

**Interfaces:**
- Produces:
  - `portfolio_cost_stress(...) -> tuple[pd.DataFrame, dict[str, Any]]`
  - `write_run_artifacts(...) -> Path`

- [ ] **Step 1: Add fake owner-backtest test**

Inject `backtest_fn` into `portfolio_cost_stress`. The fake records `rebalance_dates`, `top_k`, `weighting`, `cost_bps`. Assert calls occur once per arm per cost in `[10,20,30,50]`, with identical dates and `top_k=20`, `weighting="equal"`.

- [ ] **Step 2: Implement owner backtest call**

Build a daily input containing keys, selected `score`, and `tr_close` renamed or passed as configured `price_col`. Call:

```python
result = backtest_fn(
    data,
    pred_col="score",
    price_col="tr_close",
    rebalance_dates=list(rebalance_dates),
    top_k=20,
    shift_days=1,
    cost_bps=float(cost_bps),
    trading_days_per_year=252,
    weighting="equal",
)
```

Normalize only documented scalar stats into a long table with `arm`, `cost_bps`, `metric`, `value`. Preserve the raw serializable stats dict in the receipt lineage section. Do not recompute owner turnover/cost results.

- [ ] **Step 3: Add mandatory artifact test**

After `write_run_artifacts`, assert these exact files exist:

```python
required = {
    "experiment.yml",
    "frozen_config.json",
    "family_registry.json",
    "feature_coverage.parquet",
    "scores.parquet",
    "portfolio_daily.parquet",
    "paired_metrics.parquet",
    "window_metrics.parquet",
    "regime_metrics.parquet",
    "lineage.json",
    "receipt.json",
}
assert required == {path.name for path in run_dir.iterdir()}
```

- [ ] **Step 4: Implement artifact writer**

Use `run_directory(...)` first, create the directory once, copy frozen YAML bytes, write JSON with `sort_keys=True, indent=2`, and parquet with `index=False`. `window_metrics.parquet` may use four chronological non-overlap groups from the evaluation-date list. `regime_metrics.parquet` must use only already-present market regime columns; if unavailable, write an empty table with the fixed schema and record limitation `regime_columns_unavailable` in receipt rather than inventing macro data.

- [ ] **Step 5: Freeze receipt production flags and evidence identity**

Receipt must include:

```python
{
    "status": "research_only",
    "experiment_id": EXPERIMENT_ID,
    "production_default_changed": False,
    "automatic_promotion_allowed": False,
    "evidence_class": identity.evidence_class,
    "eligible_as_new_oos_evidence": identity.eligible_as_new_oos_evidence,
    "new_oos_start": identity.new_oos_start.strftime("%Y%m%d"),
    "policy_frozen_at": identity.policy_frozen_at,
}
```

- [ ] **Step 6: Add production-constant immutability test**

```python
def test_runner_does_not_mutate_production_feature_constant() -> None:
    from alpha_research.daily_watch20_features import DAILY_WATCH20_FEATURES

    before = tuple(DAILY_WATCH20_FEATURES)
    _run_small_synthetic_shadow()
    assert tuple(DAILY_WATCH20_FEATURES) == before
```

- [ ] **Step 7: Run artifact/portfolio tests and commit**

```bash
uv run --extra dev python -m pytest \
  tests/test_fundamental_family_shadow_portfolio_api.py \
  tests/test_fundamental_family_shadow_runner.py \
  tests/test_fundamental_family_shadow_evidence.py -q
git add experiments/fundamental_family_shadow tests
git commit -m "research: add fundamental family portfolio evidence"
```

---

### Task 8: Wire the 20d/5d CLI with fail-closed PIT and coverage checks

**Files:**
- Modify: `experiments/fundamental_family_shadow/run_family_shadow.py`
- Modify: `tests/test_fundamental_family_shadow_runner.py`

**Interfaces:**
- Produces CLI `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Add horizon-role CLI test**

Call `main(["--horizon", "60", ...])` using a temporary config/data fixture and assert return code 2 with a blocked receipt reason `slow_60d_policy_not_frozen_in_v1_pr_b`. The test must supply actual temp paths; no ellipsis literals in source.

- [ ] **Step 2: Add common coverage failure test**

Create synthetic arm scores where common-row ratio is 0.5. Assert run blocks before portfolio evaluation because config minimum is 0.80.

- [ ] **Step 3: Implement allowed PR B horizons**

```python
def _validate_pr_b_horizon(horizon: int, config: Mapping[str, Any]) -> None:
    allowed = {int(config["primary_horizon"]), int(config["diagnostic_horizon"])}
    if horizon not in allowed:
        raise ValueError("slow_60d_policy_not_frozen_in_v1_pr_b")
```

- [ ] **Step 4: Load owner inputs through public APIs**

Use existing market-data DailyWatch20 loader, existing minute loader if production P0 requires minute features, `build_daily_watch20_feature_frame` configured for the chosen single horizon, A2 `build_value_feature_panel`, and strict PIT `build_fundamental_feature_panel_from_pit_panel`. Do not read provider-private parquet paths in research code.

- [ ] **Step 5: Fail closed on Q/G PIT rejection**

Wrap owner PIT construction errors at the top-level CLI; write a blocked receipt with the exception type/message and return 2. Do not skip dates.

- [ ] **Step 6: Run full PR B focused suite**

```bash
uv run --extra dev python -m pytest \
  tests/test_fundamental_family_shadow_config.py \
  tests/test_fundamental_family_shadow_evidence.py \
  tests/test_fundamental_family_shadow_portfolio_api.py \
  tests/test_fundamental_family_shadow_runner.py -q
```

Expected: PASS.

---

### Task 9: Pin merged owner dependencies, document commands, and open PR B

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `experiments/fundamental_family_shadow/README.md`
- Modify: `experiments/README.md`

- [ ] **Step 1: Update alpha and market-data pins to merged A1/A2 commits**

Update both `[tool.uv.sources]` and `[tool.uv].override-dependencies` entries that carry those repositories. Do not pin to PR-head-only commits.

- [ ] **Step 2: Regenerate lock**

```bash
uv lock
```

- [ ] **Step 3: Document 20d retrospective command**

```bash
PYTHONPATH=. uv run --extra dev python -m experiments.fundamental_family_shadow.run_family_shadow \
  --data-root "$DATA_PLATFORM_ROOT" \
  --horizon 20 \
  --evidence-mode retrospective \
  --output-root artifacts/fundamental_family_shadow
```

- [ ] **Step 4: Document 5d diagnostic command**

```bash
PYTHONPATH=. uv run --extra dev python -m experiments.fundamental_family_shadow.run_family_shadow \
  --data-root "$DATA_PLATFORM_ROOT" \
  --horizon 5 \
  --evidence-mode retrospective \
  --output-root artifacts/fundamental_family_shadow
```

README must state that history through 2026-08-30 is retrospective and that PR B does not execute 60d or fund context.

- [ ] **Step 5: Register experiment in `experiments/README.md`**

Add one navigation row/link, no result claim.

- [ ] **Step 6: Run PR B gates**

```bash
uv run --extra dev python -m pytest \
  tests/test_fundamental_family_shadow_config.py \
  tests/test_fundamental_family_shadow_evidence.py \
  tests/test_fundamental_family_shadow_portfolio_api.py \
  tests/test_fundamental_family_shadow_runner.py -q
uv run --extra dev ruff check experiments/fundamental_family_shadow tests
uv run --extra dev ty check
```

Expected: PASS. Note that repo-wide ty excludes `experiments`; all experiment runtime behavior must therefore have focused pytest coverage.

- [ ] **Step 7: Commit final B slice**

```bash
git add experiments/fundamental_family_shadow experiments/README.md tests pyproject.toml uv.lock
git commit -m "research: add fundamental family ablation shadow"
```

- [ ] **Step 8: Open PR B**

Title:

```text
research: add fundamental family ablation shadow
```

Body must include:

```text
- Main arms are frozen at P0/T0/V/Q/G/VQ/VG/QG/VQG.
- 20d is primary; 5d is diagnostic; 60d is not executed in this PR.
- Historical runs are retrospective_diagnostic and not new OOS evidence.
- Portfolio cost/turnover accounting uses portfolio-backtester public API.
- Production defaults, production feature schema, and auto-promotion remain unchanged.
```
