# Fundamental Family Shadow A2 Alpha Owner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `alpha-research` 建立唯一的 Value / Quality / Growth family contract、Value 特征构造、P0/T0 ablation helper 与 5/20/60 horizon profile，同时保持既有 PIT Quality/Growth 和 production feature tuple 不变。

**Architecture:** 新建一个聚焦的 public module `daily_watch20_fundamental_families.py`。Q/G 只引用现有 `daily_watch20_pit_features` 常量与 builder；Value 由日频可见的 PB/PE_TTM/PS_TTM 构造同日 percentile rank；P0/T0 helper 接收 consumer 提供的 production feature tuple，避免 alpha 反向依赖 strategy-app；horizon profile 只表达 label/embargo/rebalance 语义，训练 purging 继续由 `forward_label_end_date` 完成。

**Tech Stack:** Python >=3.12、pandas、numpy、pytest、ruff、ty、uv。

**Spec:** `docs/superpowers/specs/2026-08-30-fundamental-family-shadow-design.md`

## Global Constraints

- `QUALITY_FEATURES` / `GROWTH_FEATURES` 必须从 `daily_watch20_pit_features` 导入，禁止复制字符串定义。
- 不修改 `DAILY_WATCH20_FEATURES`。
- 不修改既有 `value_yield` / `earnings_yield` production semantics。
- Value family 研究输出固定为 PB/PE/PS 三个尺度的 same-date percentile ranks。
- 非有限或 `<=0` 的 valuation denominator 必须为 null。
- 不做 forward fill。
- `family_ablation_feature_sets(...)` 必须保持传入 P0 tuple 原顺序不变，并只从 T0 移除 `value_yield`、`earnings_yield`。
- 5/20/60 horizon 分别是 diagnostic / primary / slow_challenger；single-horizon label weights 固定 `((h,1.0),)`。
- 训练 purging 以 `forward_label_end_date` 为准；`embargo_trade_days=h` 只是评估协议的一部分。
- A2 只能在 A1 merge 后更新 market-data pin。

---

### Task 1: Create the canonical family registry contract

**Files:**
- Create: `src/alpha_research/daily_watch20_fundamental_families.py`
- Create: `tests/test_daily_watch20_fundamental_families.py`

**Interfaces:**
- Produces:
  - `FUNDAMENTAL_FAMILY_SCHEMA: str`
  - `VALUE_FEATURES: tuple[str, ...]`
  - `STYLE_CONTROL_FEATURES: tuple[str, ...]`
  - `FUND_CONTEXT_FEATURES: tuple[str, ...]`
  - `fundamental_family_registry() -> dict[str, tuple[str, ...]]`

- [ ] **Step 1: Write the failing registry test**

```python
from alpha_research.daily_watch20_fundamental_families import (
    FUNDAMENTAL_FAMILY_SCHEMA,
    FUND_CONTEXT_FEATURES,
    STYLE_CONTROL_FEATURES,
    VALUE_FEATURES,
    fundamental_family_registry,
)
from alpha_research.daily_watch20_pit_features import GROWTH_FEATURES, QUALITY_FEATURES


def test_family_registry_reuses_canonical_qg_and_has_no_overlap() -> None:
    registry = fundamental_family_registry()
    assert FUNDAMENTAL_FAMILY_SCHEMA == "daily_watch20.fundamental_families.research.v1"
    assert registry["value"] == VALUE_FEATURES
    assert registry["quality"] == QUALITY_FEATURES
    assert registry["growth"] == GROWTH_FEATURES
    assert registry["style_controls"] == STYLE_CONTROL_FEATURES
    assert registry["fund_context"] == FUND_CONTEXT_FEATURES

    primary_names = [
        name
        for family in ("value", "quality", "growth")
        for name in registry[family]
    ]
    assert len(primary_names) == len(set(primary_names))
```

- [ ] **Step 2: Run and confirm import failure**

```bash
uv run --extra dev python -m pytest \
  tests/test_daily_watch20_fundamental_families.py::test_family_registry_reuses_canonical_qg_and_has_no_overlap -q
```

Expected: FAIL because the module is absent.

- [ ] **Step 3: Implement the constants and registry**

```python
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .daily_watch20_pit_features import GROWTH_FEATURES, QUALITY_FEATURES

FUNDAMENTAL_FAMILY_SCHEMA = "daily_watch20.fundamental_families.research.v1"
VALUE_FEATURES = (
    "value_book_yield_pct",
    "value_earnings_yield_pct",
    "value_sales_yield_pct",
)
STYLE_CONTROL_FEATURES = (
    "size_pct",
    "liquidity_pct",
    "low_volatility_pct",
)
FUND_CONTEXT_FEATURES = (
    "fund_crowding_level",
    "fund_ownership_change",
    "fund_holder_count_change",
    "fund_low_crowding_accumulation",
    "fund_top10_concentration",
    "fund_accumulation_without_crowding",
)


def fundamental_family_registry() -> dict[str, tuple[str, ...]]:
    return {
        "value": VALUE_FEATURES,
        "quality": QUALITY_FEATURES,
        "growth": GROWTH_FEATURES,
        "style_controls": STYLE_CONTROL_FEATURES,
        "fund_context": FUND_CONTEXT_FEATURES,
    }
```

- [ ] **Step 4: Run the registry test**

```bash
uv run --extra dev python -m pytest \
  tests/test_daily_watch20_fundamental_families.py::test_family_registry_reuses_canonical_qg_and_has_no_overlap -q
```

Expected: PASS.

---

### Task 2: Implement the Value feature panel with coverage and receipt

**Files:**
- Modify: `src/alpha_research/daily_watch20_fundamental_families.py`
- Modify: `tests/test_daily_watch20_fundamental_families.py`

**Interfaces:**
- Produces:
  - `ValueFeaturePanel(frame: pd.DataFrame, coverage_daily: pd.DataFrame, receipt: dict[str, object])`
  - `build_value_feature_panel(frame: pd.DataFrame) -> ValueFeaturePanel`

- [ ] **Step 1: Add the failing transform test**

```python
import numpy as np
import pandas as pd
import pytest


def test_value_panel_uses_positive_finite_denominators_and_same_date_ranks() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-08-28"] * 4),
            "symbol": ["A", "B", "C", "D"],
            "pb": [1.0, 2.0, 0.0, np.inf],
            "pe_ttm": [10.0, 20.0, -5.0, 40.0],
            "ps_ttm": [2.0, 4.0, 8.0, np.nan],
        }
    )

    panel = build_value_feature_panel(frame)
    out = panel.frame.set_index("symbol")

    assert out.loc["A", "value_book_yield_pct"] == pytest.approx(1.0)
    assert out.loc["B", "value_book_yield_pct"] == pytest.approx(0.5)
    assert pd.isna(out.loc["C", "value_book_yield_pct"])
    assert pd.isna(out.loc["D", "value_book_yield_pct"])
    assert out.loc["A", "value_sales_yield_pct"] == pytest.approx(1.0)
    assert panel.receipt["cross_section_transform"] == "same-date percentile rank"
    assert panel.receipt["forward_fill"] is False
```

- [ ] **Step 2: Add missing-column failure test**

```python
def test_value_panel_requires_all_owner_input_columns() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-08-28"]),
            "symbol": ["A"],
            "pb": [1.0],
        }
    )
    with pytest.raises(ValueError, match="pe_ttm.*ps_ttm"):
        build_value_feature_panel(frame)
```

- [ ] **Step 3: Add duplicate-key failure test**

```python
def test_value_panel_rejects_duplicate_stock_date_rows() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-08-28", "2026-08-28"]),
            "symbol": ["A", "A"],
            "pb": [1.0, 1.0],
            "pe_ttm": [10.0, 10.0],
            "ps_ttm": [2.0, 2.0],
        }
    )
    with pytest.raises(ValueError, match="duplicate stock-date"):
        build_value_feature_panel(frame)
```

- [ ] **Step 4: Implement the dataclass and source map**

```python
@dataclass(frozen=True)
class ValueFeaturePanel:
    frame: pd.DataFrame
    coverage_daily: pd.DataFrame
    receipt: dict[str, object]


_VALUE_SOURCE_COLUMNS = {
    "value_book_yield_pct": "pb",
    "value_earnings_yield_pct": "pe_ttm",
    "value_sales_yield_pct": "ps_ttm",
}
```

- [ ] **Step 5: Implement validated same-date ranks**

```python
def build_value_feature_panel(frame: pd.DataFrame) -> ValueFeaturePanel:
    required = {"trade_date", "symbol", *_VALUE_SOURCE_COLUMNS.values()}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"value feature frame missing columns: {missing}")

    out = frame.loc[:, ["trade_date", "symbol", *_VALUE_SOURCE_COLUMNS.values()]].copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="raise").dt.normalize()
    if out.duplicated(["trade_date", "symbol"]).any():
        raise ValueError("value feature frame contains duplicate stock-date rows")

    observed_columns: list[str] = []
    for target, source in _VALUE_SOURCE_COLUMNS.items():
        denominator = pd.to_numeric(out[source], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
        raw_yield = 1.0 / denominator.where(denominator > 0)
        out[target] = raw_yield.groupby(out["trade_date"], sort=False).rank(pct=True)
        observed = f"{target}__observed"
        out[observed] = raw_yield.notna()
        observed_columns.append(observed)

    coverage = (
        out.groupby("trade_date", sort=True)[observed_columns]
        .mean()
        .reset_index()
    )
    receipt: dict[str, object] = {
        "schema_version": FUNDAMENTAL_FAMILY_SCHEMA,
        "status": "research_only",
        "source_columns": list(_VALUE_SOURCE_COLUMNS.values()),
        "value_features": list(VALUE_FEATURES),
        "cross_section_transform": "same-date percentile rank",
        "forward_fill": False,
        "production_feature_schema_changed": False,
    }
    return ValueFeaturePanel(out, coverage, receipt)
```

- [ ] **Step 6: Run Value tests**

```bash
uv run --extra dev python -m pytest \
  tests/test_daily_watch20_fundamental_families.py -q
```

Expected: PASS.

---

### Task 3: Pin Quality/Growth parity to the existing PIT owner

**Files:**
- Modify: `tests/test_daily_watch20_pit_features.py`

- [ ] **Step 1: Add the parity test**

```python
def test_family_registry_references_existing_quality_growth_contract() -> None:
    from alpha_research.daily_watch20_fundamental_families import (
        fundamental_family_registry,
    )

    registry = fundamental_family_registry()
    assert registry["quality"] == QUALITY_FEATURES
    assert registry["growth"] == GROWTH_FEATURES
```

- [ ] **Step 2: Run the existing PIT suite with the new parity test**

```bash
uv run --extra dev python -m pytest \
  tests/test_daily_watch20_pit_features.py -q
```

Expected: PASS with no production/PIT logic changes.

---

### Task 4: Implement P0/T0 and the nine frozen main family arms

**Files:**
- Modify: `src/alpha_research/daily_watch20_fundamental_families.py`
- Modify: `tests/test_daily_watch20_fundamental_families.py`

**Interfaces:**
- Produces: `family_ablation_feature_sets(production_features: tuple[str, ...]) -> dict[str, tuple[str, ...]]`

- [ ] **Step 1: Add P0/T0 behavior test**

```python
def test_ablation_baseline_removes_existing_value_features_without_mutating_p0() -> None:
    production = ("mom_20", "value_yield", "earnings_yield", "size_pct")

    sets = family_ablation_feature_sets(production)

    assert sets["P0"] == production
    assert sets["T0"] == ("mom_20", "size_pct")
    assert sets["V"] == ("mom_20", "size_pct", *VALUE_FEATURES)
    assert set(sets) == {"P0", "T0", "V", "Q", "G", "VQ", "VG", "QG", "VQG"}
    assert production == ("mom_20", "value_yield", "earnings_yield", "size_pct")
```

- [ ] **Step 2: Add missing-anchor rejection test**

```python
def test_ablation_builder_rejects_p0_without_current_value_anchor() -> None:
    with pytest.raises(ValueError, match="current value anchor"):
        family_ablation_feature_sets(("mom_20", "size_pct"))
```

- [ ] **Step 3: Implement deterministic arm builder**

```python
_CURRENT_VALUE_ANCHOR_FEATURES = frozenset({"value_yield", "earnings_yield"})


def family_ablation_feature_sets(
    production_features: tuple[str, ...],
) -> dict[str, tuple[str, ...]]:
    p0 = tuple(production_features)
    if not _CURRENT_VALUE_ANCHOR_FEATURES.issubset(p0):
        raise ValueError("P0 lacks the frozen current value anchor features")
    t0 = tuple(name for name in p0 if name not in _CURRENT_VALUE_ANCHOR_FEATURES)
    result = {
        "P0": p0,
        "T0": t0,
        "V": (*t0, *VALUE_FEATURES),
        "Q": (*t0, *QUALITY_FEATURES),
        "G": (*t0, *GROWTH_FEATURES),
        "VQ": (*t0, *VALUE_FEATURES, *QUALITY_FEATURES),
        "VG": (*t0, *VALUE_FEATURES, *GROWTH_FEATURES),
        "QG": (*t0, *QUALITY_FEATURES, *GROWTH_FEATURES),
        "VQG": (*t0, *VALUE_FEATURES, *QUALITY_FEATURES, *GROWTH_FEATURES),
    }
    for code, features in result.items():
        if len(features) != len(set(features)):
            raise ValueError(f"duplicate features in family arm {code}")
    return result
```

- [ ] **Step 4: Run arm tests**

```bash
uv run --extra dev python -m pytest \
  tests/test_daily_watch20_fundamental_families.py -q
```

Expected: PASS.

---

### Task 5: Implement frozen 5/20/60 horizon profiles

**Files:**
- Modify: `src/alpha_research/daily_watch20_fundamental_families.py`
- Modify: `tests/test_daily_watch20_fundamental_families.py`

**Interfaces:**
- Produces:
  - `FundamentalHorizonProfile`
  - `fundamental_horizon_profiles() -> dict[int, FundamentalHorizonProfile]`

- [ ] **Step 1: Add profile contract test**

```python
def test_fundamental_horizon_profiles_are_frozen_and_horizon_aware() -> None:
    profiles = fundamental_horizon_profiles()
    assert set(profiles) == {5, 20, 60}
    assert profiles[5].role == "diagnostic"
    assert profiles[20].role == "primary"
    assert profiles[60].role == "slow_challenger"
    for horizon, profile in profiles.items():
        assert profile.horizon_days == horizon
        assert profile.forward_days == horizon
        assert profile.label_horizon_weights == ((horizon, 1.0),)
        assert profile.embargo_trade_days == horizon
        assert profile.rebalance_trade_days == horizon
```

- [ ] **Step 2: Implement dataclass and profiles**

```python
@dataclass(frozen=True)
class FundamentalHorizonProfile:
    horizon_days: int
    role: str
    forward_days: int
    label_horizon_weights: tuple[tuple[int, float], ...]
    embargo_trade_days: int
    rebalance_trade_days: int


def fundamental_horizon_profiles() -> dict[int, FundamentalHorizonProfile]:
    roles = {5: "diagnostic", 20: "primary", 60: "slow_challenger"}
    return {
        horizon: FundamentalHorizonProfile(
            horizon_days=horizon,
            role=role,
            forward_days=horizon,
            label_horizon_weights=((horizon, 1.0),),
            embargo_trade_days=horizon,
            rebalance_trade_days=horizon,
        )
        for horizon, role in roles.items()
    }
```

- [ ] **Step 3: Add `DailyWatch20FeatureConfig` compatibility test**

```python
@pytest.mark.parametrize("horizon", [5, 20, 60])
def test_horizon_profile_builds_matching_daily_watch20_feature_config(horizon: int) -> None:
    from alpha_research.daily_watch20_features import DailyWatch20FeatureConfig

    profile = fundamental_horizon_profiles()[horizon]
    cfg = DailyWatch20FeatureConfig(
        forward_days=profile.forward_days,
        label_horizon_weights=profile.label_horizon_weights,
    )
    assert cfg.label_col == f"forward_rank_{horizon}d"
    assert cfg.forward_return_col == f"forward_return_{horizon}d"
```

- [ ] **Step 4: Run profile tests**

```bash
uv run --extra dev python -m pytest \
  tests/test_daily_watch20_fundamental_families.py -q
```

Expected: PASS.

---

### Task 6: Update A1 dependency pin and run alpha regression gates

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Update `market-data-platform` source rev to A1 merge SHA**

Edit only the existing `[tool.uv.sources].market-data-platform` rev. Do not point at the A1 PR head if it is not merged.

- [ ] **Step 2: Regenerate lock**

```bash
uv lock
```

Expected: lock succeeds and resolves the merged A1 commit.

- [ ] **Step 3: Run focused family/PIT/feature/ranker regression tests**

```bash
uv run --extra dev python -m pytest \
  tests/test_daily_watch20_fundamental_families.py \
  tests/test_daily_watch20_pit_features.py \
  tests/test_daily_watch20_features.py \
  tests/test_daily_watch20.py -q
```

Expected: PASS.

- [ ] **Step 4: Run lint and type checking**

```bash
uv run --extra dev ruff check src tests
uv run --extra dev ty check
```

Expected: PASS.

- [ ] **Step 5: Verify production feature tuple did not change**

```bash
python - <<'PY'
from alpha_research.daily_watch20_features import DAILY_WATCH20_FEATURES
assert "value_sales_yield_pct" not in DAILY_WATCH20_FEATURES
assert "pit_quality_roa_pct" not in DAILY_WATCH20_FEATURES
assert "pit_growth_revenue_yoy_pct" not in DAILY_WATCH20_FEATURES
print(len(DAILY_WATCH20_FEATURES))
PY
```

Expected: assertions pass.

- [ ] **Step 6: Commit and open PR A2**

```bash
git add \
  src/alpha_research/daily_watch20_fundamental_families.py \
  tests/test_daily_watch20_fundamental_families.py \
  tests/test_daily_watch20_pit_features.py \
  pyproject.toml uv.lock
git commit -m "feat: define DailyWatch20 fundamental families"
```

PR title:

```text
feat: define DailyWatch20 fundamental families
```

PR body must state:

```text
- Defines research-only Value/Quality/Growth family contracts.
- Reuses canonical PIT Quality/Growth definitions.
- Adds PB/PE/PS same-date Value ranks with no forward fill.
- Adds P0/T0 family ablation and 5/20/60 horizon profiles.
- DAILY_WATCH20_FEATURES and production defaults are unchanged.
```
