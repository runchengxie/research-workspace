# Fundamental Family Shadow A1 Data Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `market-data-platform` 的 DailyWatch20 公共 research view 稳定暴露 `ps_ttm`，并对返回数据的日期范围与 stock/date 唯一性 fail closed，为后续 Value family 提供 owner-controlled 输入。

**Architecture:** 只修改数据 owner 的 research view，不修改 published asset schema、provider 拉取逻辑或生产策略。`load_daily_watch20_daily(...)` 维持原签名，SQL projection 增加 `ps_ttm`，返回前执行轻量结果契约校验。

**Tech Stack:** Python >=3.11、pandas、DuckDB、PyArrow、pytest、ruff、ty、uv。

**Spec:** `docs/superpowers/specs/2026-08-30-fundamental-family-shadow-design.md`

## Global Constraints

- 不修改 published A-share asset schema 或 current-contract 经济语义。
- 不修改 `strategy-pipeline` / production preset。
- `ps_ttm` 仅作为 additive research-view column。
- `load_daily_watch20_daily` 的调用签名和现有列行为保持兼容。
- 重复 `(trade_date, symbol)` 必须 fail closed。
- 返回日期必须处于请求的 `[start_date, end_date]` inclusive 范围。

---

### Task 1: Add a realistic research-view fixture and failing `ps_ttm` contract test

**Files:**
- Create: `tests/test_daily_watch20_research_view.py`

**Interfaces:**
- Consumes: `market_data_platform.research_views.daily_watch20_data.DailyWatch20Assets`
- Consumes: `load_daily_watch20_daily(assets, *, start_date, end_date, memory_limit="12GB", threads=3) -> pd.DataFrame`
- Produces: test-only `_assets(tmp_path, frame)` and `_rows()` fixtures.

- [ ] **Step 1: Create the test fixture helpers**

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from market_data_platform.research_views.daily_watch20_data import (
    DailyWatch20Assets,
    load_daily_watch20_daily,
)


def _rows() -> pd.DataFrame:
    base = {
        "open": 10.0,
        "adj_open": 10.0,
        "up_limit": 11.0,
        "down_limit": 9.0,
        "tr_close": 10.1,
        "high": 10.2,
        "low": 9.9,
        "close": 10.1,
        "amount": 1_000_000.0,
        "turnover_rate": 1.2,
        "volume_ratio": 1.1,
        "total_mv": 100_000_000.0,
        "pb": 1.5,
        "pe_ttm": 12.0,
        "ps_ttm": 2.4,
        "listed_days": 300,
        "board": "main",
        "is_st": False,
        "is_suspended": False,
        "is_limit_up": False,
        "is_limit_down": False,
    }
    return pd.DataFrame(
        [
            {**base, "trade_date": "20260828", "symbol": "000001.SZ"},
            {
                **base,
                "trade_date": "20260831",
                "symbol": "000001.SZ",
                "pb": 1.6,
                "pe_ttm": 12.5,
                "ps_ttm": 2.5,
            },
        ]
    )


def _assets(tmp_path: Path, frame: pd.DataFrame) -> DailyWatch20Assets:
    daily = tmp_path / "daily"
    (daily / "data").mkdir(parents=True)
    frame.to_parquet(daily / "data/part.parquet", index=False)
    marker = tmp_path / "marker"
    marker.write_text("x", encoding="utf-8")
    return DailyWatch20Assets(
        data_root=tmp_path,
        current_contract=marker,
        daily_clean=daily,
        instruments=marker,
        trade_cal=marker,
        minute_current=tmp_path,
        minute_coverage=None,
        daily_as_of="20260831",
        minute_date_min=None,
        minute_date_max=None,
    )
```

- [ ] **Step 2: Add the failing valuation-input test**

```python
def test_daily_watch20_loader_exposes_all_three_valuation_inputs(tmp_path: Path) -> None:
    assets = _assets(tmp_path, _rows())

    loaded = load_daily_watch20_daily(
        assets,
        start_date="20260828",
        end_date="20260828",
        threads=1,
    )

    assert list(loaded["trade_date"].astype(str)) == ["20260828"]
    assert loaded.loc[0, ["pb", "pe_ttm", "ps_ttm"]].to_dict() == {
        "pb": 1.5,
        "pe_ttm": 12.0,
        "ps_ttm": 2.4,
    }
    assert not loaded.duplicated(["trade_date", "symbol"]).any()
```

- [ ] **Step 3: Run the test to prove current code fails**

Run:

```bash
uv run --extra dev python -m pytest \
  tests/test_daily_watch20_research_view.py::test_daily_watch20_loader_exposes_all_three_valuation_inputs -q
```

Expected: FAIL because `load_daily_watch20_daily` currently projects `pb` and `pe_ttm` but not `ps_ttm`.

- [ ] **Step 4: Commit only after Task 2 is complete**

Do not commit a test-only red branch as the final PR state. Continue directly to Task 2.

---

### Task 2: Add `ps_ttm` to the owner projection and validate returned keys/range

**Files:**
- Modify: `src/market_data_platform/research_views/daily_watch20_data.py`
- Modify: `tests/test_daily_watch20_research_view.py`

**Interfaces:**
- Produces private helper:
  - `_validate_daily_watch20_daily_result(frame: pd.DataFrame, *, start_date: str, end_date: str) -> pd.DataFrame`
- Keeps `load_daily_watch20_daily(...)` public signature unchanged.

- [ ] **Step 1: Add `ps_ttm` to the SQL projection**

Change the projection fragment from:

```python
"turnover_rate, volume_ratio, total_mv, pb, pe_ttm, listed_days, board, "
```

to:

```python
"turnover_rate, volume_ratio, total_mv, pb, pe_ttm, ps_ttm, listed_days, board, "
```

- [ ] **Step 2: Add explicit result validation**

Place this helper near the loader:

```python
def _validate_daily_watch20_daily_result(
    frame: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
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

- [ ] **Step 3: Route the fetched frame through validation**

Replace:

```python
return conn.execute(query).fetch_df()
```

with:

```python
frame = conn.execute(query).fetch_df()
return _validate_daily_watch20_daily_result(
    frame,
    start_date=start_date,
    end_date=end_date,
)
```

- [ ] **Step 4: Run the valuation-input test**

```bash
uv run --extra dev python -m pytest \
  tests/test_daily_watch20_research_view.py::test_daily_watch20_loader_exposes_all_three_valuation_inputs -q
```

Expected: PASS.

---

### Task 3: Pin duplicate-key and inclusive date filtering behavior

**Files:**
- Modify: `tests/test_daily_watch20_research_view.py`

- [ ] **Step 1: Add duplicate-key failure test**

```python
def test_daily_watch20_loader_rejects_duplicate_stock_date_rows(tmp_path: Path) -> None:
    first = _rows().iloc[[0]].copy()
    duplicated = pd.concat([first, first], ignore_index=True)
    assets = _assets(tmp_path, duplicated)

    with pytest.raises(ValueError, match="duplicate stock-date"):
        load_daily_watch20_daily(
            assets,
            start_date="20260828",
            end_date="20260828",
            threads=1,
        )
```

- [ ] **Step 2: Add inclusive range test**

```python
def test_daily_watch20_loader_filters_to_requested_inclusive_dates(tmp_path: Path) -> None:
    assets = _assets(tmp_path, _rows())

    loaded = load_daily_watch20_daily(
        assets,
        start_date="20260831",
        end_date="20260831",
        threads=1,
    )

    assert loaded[["trade_date", "symbol"]].astype(str).to_dict("records") == [
        {"trade_date": "20260831", "symbol": "000001.SZ"}
    ]
```

- [ ] **Step 3: Run all A1 focused tests**

```bash
uv run --extra dev python -m pytest tests/test_daily_watch20_research_view.py -q
```

Expected: all pass.

---

### Task 4: Run repository gates and create PR A1

**Files:**
- No additional source files.

- [ ] **Step 1: Run Ruff**

```bash
uv run --extra dev ruff check \
  src/market_data_platform/research_views/daily_watch20_data.py \
  tests/test_daily_watch20_research_view.py
```

Expected: PASS.

- [ ] **Step 2: Run type checking**

```bash
uv run --extra dev ty check
```

Expected: PASS.

- [ ] **Step 3: Run the nearest existing research-data regression test**

```bash
uv run --extra dev python -m pytest \
  tests/test_a_share_research_data.py \
  tests/test_daily_watch20_research_view.py -q
```

Expected: PASS.

- [ ] **Step 4: Inspect diff for scope creep**

```bash
git diff -- src/market_data_platform/research_views/daily_watch20_data.py tests/test_daily_watch20_research_view.py
```

Expected: only projection + validation + tests; no provider/published schema changes.

- [ ] **Step 5: Commit**

```bash
git add \
  src/market_data_platform/research_views/daily_watch20_data.py \
  tests/test_daily_watch20_research_view.py
git commit -m "feat: expose DailyWatch20 sales valuation input"
```

- [ ] **Step 6: Open PR A1**

Title:

```text
feat: expose DailyWatch20 sales valuation input
```

Body must include these exact claims:

```text
- Adds ps_ttm to the existing DailyWatch20 research view.
- Preserves load_daily_watch20_daily public signature and existing columns.
- Fails closed on duplicate stock/date rows and escaped date ranges.
- Does not change published asset schema or any production strategy preset.
```
