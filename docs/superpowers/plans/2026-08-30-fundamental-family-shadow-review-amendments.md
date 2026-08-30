# Fundamental Family Shadow Plan Review Amendments

> **Authority:** This file is part of the approved implementation-plan package. Where it conflicts with an earlier code snippet in the master/B/C-D plan files, this amendment is authoritative. It exists to remove two ambiguities found during plan self-review before implementation begins.

## Execution order

Use the plan package in this order:

1. `2026-08-30-fundamental-family-shadow-a1-data.md`
2. `2026-08-30-fundamental-family-shadow-a2-alpha.md`
3. `2026-08-30-fundamental-family-shadow-b-research.md`, with Amendment A below replacing Task 3 evidence-start calculation
4. `2026-08-30-fundamental-family-shadow-cd.md`, with Amendment B below replacing Task 3 Step 4 fund-context implementation snippet
5. retrospective smoke runs
6. workspace integration PR D

The master `2026-08-30-fundamental-family-shadow.md` is an overview/checklist. The child plans plus this amendment are the executable instructions.

---

## Amendment A: new-OOS start must come from the observed trading calendar

### Problem found in self-review

The PR B child plan showed `observed + pd.offsets.BDay(1)` as an example for `new_oos_start`. That is too weak for A-share evidence identity because `BDay` knows weekends but not exchange holidays or ad-hoc closures. The design requires the first **unobserved trading date**, not the next weekday.

### Replacement contract

Replace the earlier `classify_evidence(...)` signature and implementation with:

```python
from __future__ import annotations

from dataclasses import dataclass

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
    next_unobserved_trade_date: str | pd.Timestamp,
) -> EvidenceIdentity:
    dates = pd.DatetimeIndex(evaluation_dates).normalize()
    if dates.empty:
        raise ValueError("fundamental family evidence requires evaluation dates")

    observed = pd.Timestamp(observed_through).normalize()
    calendar_start = pd.Timestamp(next_unobserved_trade_date).normalize()
    if calendar_start <= observed:
        raise ValueError("next_unobserved_trade_date must be after observed_through")

    new_oos_start = max(_NEW_OOS_FLOOR, calendar_start)
    all_prospective = bool(dates.ge(new_oos_start).all())
    return EvidenceIdentity(
        evidence_class=(
            "prospective_oos" if all_prospective else "retrospective_diagnostic"
        ),
        eligible_as_new_oos_evidence=all_prospective,
        new_oos_start=new_oos_start,
        policy_frozen_at=policy_frozen_at,
    )
```

### Source of `next_unobserved_trade_date`

The runner must derive it from the market-data owner trading calendar already used by DailyWatch20. Given `observed_through_at_freeze`, choose the first open trade date strictly greater than that date. Do not use `BDay`, `timedelta(days=1)`, or weekday arithmetic.

If the published trading calendar does not extend beyond `observed_through_at_freeze`, fail closed with a blocked receipt. Do not guess the next trading day.

### Replacement tests

Use an explicit holiday-sensitive date to prove the contract does not infer weekdays:

```python
def test_new_oos_start_uses_supplied_next_open_trade_date() -> None:
    identity = classify_evidence(
        pd.DatetimeIndex(pd.to_datetime(["2026-10-09"])),
        policy_frozen_at="2026-09-30T21:00:00+08:00",
        observed_through="2026-09-30",
        next_unobserved_trade_date="2026-10-09",
    )
    assert identity.new_oos_start == pd.Timestamp("2026-10-09")
```

And reject an invalid calendar result:

```python
def test_new_oos_start_rejects_non_future_calendar_date() -> None:
    with pytest.raises(ValueError, match="after observed_through"):
        classify_evidence(
            pd.DatetimeIndex(pd.to_datetime(["2026-10-09"])),
            policy_frozen_at="2026-09-30T21:00:00+08:00",
            observed_through="2026-09-30",
            next_unobserved_trade_date="2026-09-30",
        )
```

All subsequent PR B/C tests and receipts must pass/store this calendar-derived `new_oos_start`.

---

## Amendment B: complete fund-context implementation, no placeholder body

### Problem found in self-review

The PR C-D child plan included a code block ending in `...`, followed by the formulas in prose. That is readable for design discussion but too ambiguous for a TDD implementation plan. The following function and helper replace that whole Task 3 Step 4 code block.

### Complete replacement implementation

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_research.daily_watch20_fundamental_families import FUND_CONTEXT_FEATURES


def _numeric_or_nan(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )


def _safe_ntile(
    values: pd.Series,
    frame: pd.DataFrame,
    quantile_count: int,
) -> pd.Series:
    tiles = pd.Series(np.nan, index=frame.index, dtype=float)
    valid = values.notna()
    if not valid.any():
        return tiles
    percentile = (
        frame.loc[valid]
        .assign(_value=values.loc[valid])
        .groupby("trade_date", sort=False, dropna=False)["_value"]
        .rank(method="first", pct=True)
    )
    tiles.loc[valid] = (
        percentile.mul(quantile_count)
        .clip(lower=1, upper=quantile_count)
        .apply(lambda value: int(value) if pd.notna(value) else value)
    )
    return tiles


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
    if quantile_count < 2:
        raise ValueError("quantile_count must be at least 2")

    out = frame.copy()
    out["trade_date"] = pd.to_datetime(
        out["trade_date"], errors="raise"
    ).dt.normalize()
    symbols = out["symbol"].astype("string").str.strip()
    if symbols.isna().any() or symbols.eq("").any():
        raise ValueError("fund context frame contains empty symbols")
    out["symbol"] = symbols.astype(str)
    if out.duplicated(["trade_date", "symbol"]).any():
        raise ValueError("fund context frame contains duplicate stock-date rows")

    if require_available_date:
        if "available_date" not in out.columns:
            raise ValueError("fund context frame requires available_date")
        available = pd.to_datetime(
            out["available_date"], errors="coerce"
        ).dt.normalize()
        if available.isna().any() or available.gt(out["trade_date"]).any():
            raise ValueError(
                "fund context available_date must be present and not after trade_date"
            )

    crowd = _numeric_or_nan(out, "fund_hold_mv_to_float_mv")
    ownership_change = _numeric_or_nan(
        out, "fund_hold_mv_to_float_mv_qoq_change"
    )
    holder_count_change = _numeric_or_nan(
        out, "fund_count_holding_stock_qoq_change"
    )

    out["fund_crowding_level"] = crowd
    out["fund_ownership_change"] = ownership_change
    out["fund_holder_count_change"] = holder_count_change

    crowd_q = _safe_ntile(crowd, out, quantile_count)
    ownership_q = _safe_ntile(ownership_change, out, quantile_count)
    low = crowd_q.le(2)
    increasing = ownership_q.ge(quantile_count - 1)
    out["fund_low_crowding_accumulation"] = (low & increasing).astype(float)

    top10 = _numeric_or_nan(out, "fund_top10_hold_mv_to_float_mv")
    out["fund_top10_concentration"] = top10.div(
        crowd.where(crowd > 0)
    ).clip(lower=0.0, upper=1.0)
    out["fund_accumulation_without_crowding"] = (
        low
        & increasing
        & out["fund_top10_concentration"].notna()
        & out["fund_top10_concentration"].le(0.8)
    ).astype(float)

    missing_outputs = sorted(set(FUND_CONTEXT_FEATURES) - set(out.columns))
    if missing_outputs:
        raise RuntimeError(f"fund context outputs missing: {missing_outputs}")
    return out
```

### Additional test for absent optional fields

```python
def test_fund_context_keeps_optional_missing_sources_as_null() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-08-28"]),
            "available_date": pd.to_datetime(["2026-08-28"]),
            "symbol": ["A"],
            "fund_hold_mv_to_float_mv": [0.02],
        }
    )
    out = build_fund_context_features(frame)
    assert pd.isna(out.loc[0, "fund_ownership_change"])
    assert pd.isna(out.loc[0, "fund_holder_count_change"])
    assert pd.isna(out.loc[0, "fund_top10_concentration"])
    assert out.loc[0, "fund_accumulation_without_crowding"] == 0.0
```

This implementation performs no as-of join and creates no new dates. The caller must supply disclosed-state rows already visible on each scoring date.
