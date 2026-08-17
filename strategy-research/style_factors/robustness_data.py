"""Load the bounded data contract used by constrained style-factor robustness runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .robustness_constraints import (
    apply_explicit_suspensions,
    load_margin_formation_eligibility,
    load_reported_borrow_activity_eligibility,
    load_st_event_evidence,
)
from .robustness_sources import (
    CONSTRAINTS_VERSION,
    PIT_VINTAGE,
    build_early_daily_clean,
    build_early_universe,
    expand_st_intervals,
    load_reconstructed_pit_panel,
)

DAILY_CLEAN_COLUMNS = [
    "trade_date",
    "symbol",
    "close",
    "tr_close",
    "adj_factor",
    "pct_chg",
    "amount",
    "total_mv",
    "pb",
    "pe_ttm",
    "turnover_rate",
    "dv_ttm",
    "ps_ttm",
    "is_limit_up",
    "is_limit_down",
    "is_suspended",
    "listed_days",
]


@dataclass(frozen=True)
class RobustnessMarketData:
    """Frames and provenance required by the robustness backtest."""

    daily_clean: pd.DataFrame
    universe: pd.DataFrame
    st_history: pd.DataFrame
    margin_eligibility: pd.DataFrame
    reported_borrow_activity: pd.DataFrame
    pit_fundamentals: pd.DataFrame
    instruments: pd.DataFrame
    metadata: dict[str, Any]


def _require_unique(frame: pd.DataFrame, keys: list[str], *, label: str) -> None:
    duplicates = frame.duplicated(keys, keep=False)
    if duplicates.any():
        sample = frame.loc[duplicates, keys].head(5).to_dict(orient="records")
        raise ValueError(f"{label} has duplicate {keys} keys; sample={sample}")


def _filter_date_window(
    frame: pd.DataFrame,
    *,
    start_date: str | pd.Timestamp | None,
    end_date: str | pd.Timestamp | None,
) -> pd.DataFrame:
    start = pd.to_datetime(start_date) if start_date is not None else None
    end = pd.to_datetime(end_date) if end_date is not None else None
    if start is not None:
        frame = frame[frame["trade_date"] >= start]
    if end is not None:
        frame = frame[frame["trade_date"] <= end]
    return frame.copy()


def _normalize_trade_dates(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    compact = (
        frame["trade_date"]
        .astype("string")
        .str.strip()
        .str.slice(0, 10)
        .str.replace("-", "", regex=False)
    )
    frame["trade_date"] = pd.to_datetime(
        compact,
        format="%Y%m%d",
        errors="coerce",
    )
    return frame.dropna(subset=["trade_date"])


def _load_late_daily_clean(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None,
    end_date: str | pd.Timestamp | None,
) -> pd.DataFrame:
    data_dir = data_root / "assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data"
    if not data_dir.is_dir():
        raise FileNotFoundError(f"daily_clean data directory not found: {data_dir}")
    frame = pd.read_parquet(data_dir, columns=DAILY_CLEAN_COLUMNS)
    frame = _normalize_trade_dates(frame)
    frame = _filter_date_window(frame, start_date=start_date, end_date=end_date)
    if frame.empty:
        raise ValueError("late daily_clean is empty in the requested robustness window")
    _require_unique(frame, ["trade_date", "symbol"], label="daily_clean")
    return frame.sort_values(["trade_date", "symbol"]).reset_index(drop=True)


def _load_late_universe(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None,
    end_date: str | pd.Timestamp | None,
) -> pd.DataFrame:
    path = data_root / "assets/universe/a_share_all_full_by_date.csv"
    if not path.is_file():
        raise FileNotFoundError(f"universe_by_date file not found: {path}")
    frame = pd.read_csv(path, usecols=["trade_date", "symbol", "selected"])
    frame = _normalize_trade_dates(frame)
    frame = _filter_date_window(frame, start_date=start_date, end_date=end_date)
    frame = frame[frame["selected"].eq(1)].drop(columns="selected")
    if frame.empty:
        raise ValueError("late universe_by_date is empty in the requested robustness window")
    _require_unique(frame, ["trade_date", "symbol"], label="universe_by_date")
    return frame.sort_values(["trade_date", "symbol"]).reset_index(drop=True)


def _load_instruments(data_root: Path) -> pd.DataFrame:
    path = data_root / "assets/tushare/a_share/instruments/a_share_all_instruments_latest.parquet"
    if not path.is_file():
        raise FileNotFoundError(f"instruments file not found: {path}")
    frame = pd.read_parquet(
        path,
        columns=["symbol", "list_status", "list_date", "delist_date"],
    )
    for column in ("list_date", "delist_date"):
        frame[column] = pd.to_datetime(
            frame[column].astype("string"),
            format="%Y%m%d",
            errors="coerce",
        )
    _require_unique(frame, ["symbol"], label="instruments")
    return frame.reset_index(drop=True)


def _adjustment_bridge_metadata(daily_clean: pd.DataFrame) -> dict[str, Any]:
    boundary = pd.Timestamp("2015-01-01")
    ordered = daily_clean.sort_values(["symbol", "trade_date"])
    before = ordered.loc[ordered["trade_date"] < boundary].groupby("symbol", sort=False).tail(1)
    after = ordered.loc[ordered["trade_date"] >= boundary].groupby("symbol", sort=False).head(1)
    paired = before[["symbol", "tr_close"]].merge(
        after[["symbol", "tr_close", "pct_chg"]],
        on="symbol",
        suffixes=("_before", "_after"),
        validate="one_to_one",
    )
    implied = (paired["tr_close_after"] / paired["tr_close_before"] - 1.0) * 100.0
    error = (implied - paired["pct_chg"]).abs().dropna()
    return {
        "adjustment_bridge_symbols": len(error),
        "adjustment_bridge_median_abs_error_pct": float(error.median()),
        "adjustment_bridge_p99_abs_error_pct": float(error.quantile(0.99)),
        "adjustment_bridge_max_abs_error_pct": float(error.max()),
        "adjustment_bridge_errors_over_0_10_pct": int(error.gt(0.10).sum()),
    }


def _coverage_metadata(
    daily_clean: pd.DataFrame,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    margin_eligibility: pd.DataFrame,
    reported_borrow_activity: pd.DataFrame,
    pit_fundamentals: pd.DataFrame,
    instruments: pd.DataFrame,
    source_metadata: dict[str, Any],
) -> dict[str, Any]:
    st_start = st_history["trade_date"].min() if not st_history.empty else None
    st_end = st_history["trade_date"].max() if not st_history.empty else None
    formation_match = universe.merge(
        daily_clean[["trade_date", "symbol"]],
        on=["trade_date", "symbol"],
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    return {
        "daily_clean_rows": len(daily_clean),
        "daily_clean_symbols": int(daily_clean["symbol"].nunique()),
        "daily_clean_start": daily_clean["trade_date"].min().date().isoformat(),
        "daily_clean_end": daily_clean["trade_date"].max().date().isoformat(),
        "price_limit_source": (
            "2008–2014 version-pinned stk_limit bridge; 2015+ daily_clean limit flags"
        ),
        "factor_price_source": "raw close × adj_factor (scale-invariant total-return price)",
        "universe_rows": len(universe),
        "universe_symbols": int(universe["symbol"].nunique()),
        "universe_rebalance_dates": int(universe["trade_date"].nunique()),
        "universe_start": universe["trade_date"].min().date().isoformat(),
        "universe_end": universe["trade_date"].max().date().isoformat(),
        "universe_daily_join_rate": float(formation_match["_merge"].eq("both").mean()),
        "st_rows": len(st_history),
        "st_symbols": int(st_history["symbol"].nunique()) if not st_history.empty else 0,
        "st_start": st_start.date().isoformat() if st_start is not None else None,
        "st_end": st_end.date().isoformat() if st_end is not None else None,
        "st_history_complete": True,
        "st_policy": "reconstructed namechange intervals expanded on formation dates only",
        "margin_formation_rows": len(margin_eligibility),
        "margin_start": (
            margin_eligibility["trade_date"].min().date().isoformat()
            if not margin_eligibility.empty
            else None
        ),
        "margin_end": (
            margin_eligibility["trade_date"].max().date().isoformat()
            if not margin_eligibility.empty
            else None
        ),
        "reported_borrow_activity_start": (
            reported_borrow_activity["trade_date"].min().date().isoformat()
            if not reported_borrow_activity.empty
            else None
        ),
        "reported_borrow_activity_end": (
            reported_borrow_activity["trade_date"].max().date().isoformat()
            if not reported_borrow_activity.empty
            else None
        ),
        "reported_borrow_activity_date_coverage": (
            reported_borrow_activity["trade_date"].nunique()
            / margin_eligibility["trade_date"].nunique()
            if not margin_eligibility.empty
            else 0.0
        ),
        "pit_panel_rows": len(pit_fundamentals),
        "delisted_instruments": int(instruments["delist_date"].notna().sum()),
        "duplicate_daily_keys": 0,
        "duplicate_universe_keys": 0,
        "duplicate_margin_keys": 0,
        "duplicate_reported_borrow_activity_keys": 0,
        "duplicate_pit_panel_keys": 0,
        **_adjustment_bridge_metadata(daily_clean),
        **source_metadata,
    }


def _assemble_daily_clean(
    data_root: Path,
    instruments: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    late_daily = _load_late_daily_clean(
        data_root,
        start_date=max(start, pd.Timestamp("2015-01-01")),
        end_date=end,
    )
    source_metadata: dict[str, Any] = {}
    daily_parts: list[pd.DataFrame] = []
    if start <= pd.Timestamp("2014-12-31"):
        early_daily, early_metadata = build_early_daily_clean(
            data_root,
            instruments,
            start_date=start,
            end_date=end,
        )
        daily_parts.append(early_daily)
        source_metadata.update(early_metadata)
    daily_parts.append(late_daily)
    daily_clean = pd.concat(daily_parts, ignore_index=True, sort=False)
    adjusted = daily_clean["close"] * daily_clean["adj_factor"]
    daily_clean["tr_close"] = adjusted.combine_first(daily_clean["tr_close"])
    daily_clean = _filter_date_window(daily_clean, start_date=start, end_date=end)
    _require_unique(daily_clean, ["trade_date", "symbol"], label="full daily_clean bridge")
    return daily_clean.sort_values(["trade_date", "symbol"]).reset_index(drop=True), source_metadata


def _assemble_universe(
    data_root: Path,
    daily_clean: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    late_universe = _load_late_universe(
        data_root,
        start_date=max(start, pd.Timestamp("2015-01-01")),
        end_date=end,
    )
    universe_parts: list[pd.DataFrame] = []
    if start <= pd.Timestamp("2014-12-31"):
        universe_parts.append(
            build_early_universe(daily_clean, before=late_universe["trade_date"].min())
        )
    universe_parts.append(late_universe)
    universe = pd.concat(universe_parts, ignore_index=True).drop_duplicates(
        ["trade_date", "symbol"]
    )
    universe = _filter_date_window(universe, start_date=start, end_date=end)
    universe = universe.sort_values(["trade_date", "symbol"]).reset_index(drop=True)
    _require_unique(universe, ["trade_date", "symbol"], label="full universe_by_date")
    return universe


def load_robustness_market_data(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None = "2008-01-01",
    end_date: str | pd.Timestamp | None = None,
    constraints_dir: Path | None = None,
    pit_vintage_dir: Path | None = None,
) -> RobustnessMarketData:
    """Load the version-pinned full-history constrained-research contract."""
    start = pd.to_datetime(start_date or "2008-01-01")
    end = pd.to_datetime(end_date or pd.Timestamp.today().normalize())
    instruments = _load_instruments(data_root)
    constraints = constraints_dir or data_root / "staging" / CONSTRAINTS_VERSION
    daily_clean, source_metadata = _assemble_daily_clean(
        data_root,
        instruments,
        start=start,
        end=end,
    )
    daily_clean, suspend_metadata = apply_explicit_suspensions(daily_clean, constraints)
    source_metadata.update(suspend_metadata)
    universe = _assemble_universe(data_root, daily_clean, start=start, end=end)

    vintage = pit_vintage_dir or (
        data_root / "assets/tushare/a_share/fundamentals_vintages" / f"vintage={PIT_VINTAGE}"
    )
    formation_dates = pd.DatetimeIndex(universe["trade_date"].unique()).normalize()
    st_history, st_metadata = expand_st_intervals(constraints, formation_dates)
    margin_eligibility, margin_metadata = load_margin_formation_eligibility(
        constraints,
        formation_dates,
    )
    reported_borrow_activity, borrow_activity_metadata = load_reported_borrow_activity_eligibility(
        constraints,
        formation_dates,
        margin_eligibility,
    )
    pit_fundamentals, pit_metadata = load_reconstructed_pit_panel(vintage, universe)
    source_metadata.update(
        st_metadata
        | load_st_event_evidence(constraints)
        | margin_metadata
        | borrow_activity_metadata
        | pit_metadata
    )
    metadata = _coverage_metadata(
        daily_clean,
        universe,
        st_history,
        margin_eligibility,
        reported_borrow_activity,
        pit_fundamentals,
        instruments,
        source_metadata,
    )
    return RobustnessMarketData(
        daily_clean=daily_clean,
        universe=universe,
        st_history=st_history,
        margin_eligibility=margin_eligibility,
        reported_borrow_activity=reported_borrow_activity,
        pit_fundamentals=pit_fundamentals,
        instruments=instruments,
        metadata=metadata,
    )
