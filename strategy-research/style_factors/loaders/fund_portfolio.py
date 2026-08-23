"""PIT public-fund top-10 ownership state materialized to factor formation dates."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ._common import _filter_partition_paths, _latest_data_dir, _read_partitioned_parquet

STATE_COLUMNS = [
    "fund_top10_count_holding_stock",
    "fund_top10_stk_float_ratio_sum",
]
META_COLUMNS = [
    "report_period",
    "disclosure_date",
]


def materialize_fund_portfolio_state(
    events: pd.DataFrame,
    formation_panel: pd.DataFrame,
) -> pd.DataFrame:
    """Carry the latest PIT public-fund top-10 state to each formation date.

    ``fund_top10_portfolio_features`` is an event-state asset: a row is emitted
    when newly disclosed fund top-10 portfolios change the currently known
    aggregate state of a stock. Style-factor formation happens at month end, so
    an exact-date join would discard almost all observations. This function
    performs a backward as-of join by symbol and then computes changes between
    formation dates, never between asynchronous disclosure events.

    Stocks with no prior top-10 fund event are treated as zero ownership after
    the feature asset starts. This keeps never-held names in the cross-section
    instead of silently restricting the factor universe to stocks already held
    as public-fund top-10 positions.
    """
    if events.empty or formation_panel.empty:
        return pd.DataFrame()
    required = {"trade_date", "symbol", *STATE_COLUMNS}
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"fund_top10_portfolio_features missing columns: {sorted(missing)}")
    target_required = {"trade_date", "symbol"}
    target_missing = target_required - set(formation_panel.columns)
    if target_missing:
        raise ValueError(f"formation_panel missing columns: {sorted(target_missing)}")

    source_columns = [
        "trade_date",
        "symbol",
        *STATE_COLUMNS,
        *(column for column in META_COLUMNS if column in events.columns),
    ]
    source = events[source_columns].copy()
    source["trade_date"] = pd.to_datetime(source["trade_date"]).dt.normalize()
    source["symbol"] = source["symbol"].astype(str).str.strip()
    source = source.dropna(subset=["trade_date", "symbol"])
    source = source.drop_duplicates(["trade_date", "symbol"], keep="last")
    coverage_start = source["trade_date"].min()
    source = source.rename(columns={"trade_date": "fund_available_date"})

    target = formation_panel[["trade_date", "symbol"]].drop_duplicates().copy()
    target["trade_date"] = pd.to_datetime(target["trade_date"]).dt.normalize()
    target["symbol"] = target["symbol"].astype(str).str.strip()
    target = target.dropna(subset=["trade_date", "symbol"])

    merged = pd.merge_asof(
        target.sort_values(["trade_date", "symbol"]),
        source.sort_values(["fund_available_date", "symbol"]),
        left_on="trade_date",
        right_on="fund_available_date",
        by="symbol",
        direction="backward",
        allow_exact_matches=True,
    )
    eligible = merged["trade_date"] >= coverage_start
    merged["fund_state_observed"] = merged["fund_available_date"].notna()
    for column in STATE_COLUMNS:
        merged[column] = pd.to_numeric(merged[column], errors="coerce")
        merged.loc[eligible & merged[column].isna(), column] = 0.0

    merged = merged.sort_values(["symbol", "trade_date"]).reset_index(drop=True)
    merged["fund_top10_count_holding_stock_change"] = merged.groupby(
        "symbol", sort=False
    )["fund_top10_count_holding_stock"].diff()
    merged["fund_top10_stk_float_ratio_sum_change"] = merged.groupby(
        "symbol", sort=False
    )["fund_top10_stk_float_ratio_sum"].diff()
    merged["fund_state_age_days"] = (
        merged["trade_date"] - merged["fund_available_date"]
    ).dt.days
    return merged.sort_values(["trade_date", "symbol"]).reset_index(drop=True)


def load_fund_portfolio_features(
    data_root: Path,
    *,
    formation_panel: pd.DataFrame | None = None,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Load public-fund top-10 PIT ownership features, optionally at formation dates."""
    dataset = "fund_top10_portfolio_features"
    data_dir = _latest_data_dir(data_root, dataset)
    if data_dir is None:
        print(f"[load] {dataset}: no data found")
        return pd.DataFrame()

    parts = sorted(data_dir.glob("trade_date=*"))
    if formation_panel is None:
        parts = _filter_partition_paths(parts, start_date=start_date, end_date=end_date)
    else:
        formation_dates = pd.to_datetime(formation_panel["trade_date"], errors="coerce")
        max_date = formation_dates.max()
        if pd.notna(max_date):
            parts = _filter_partition_paths(parts, end_date=max_date)
    if not parts:
        return pd.DataFrame()

    events = _read_partitioned_parquet(parts, label=dataset)
    keep = [
        column
        for column in ["trade_date", "symbol", *STATE_COLUMNS, *META_COLUMNS]
        if column in events.columns
    ]
    events = events[keep].copy()
    if formation_panel is not None:
        output = materialize_fund_portfolio_state(events, formation_panel)
        start = pd.to_datetime(start_date) if start_date is not None else None
        end = pd.to_datetime(end_date) if end_date is not None else None
        if start is not None:
            output = output[output["trade_date"] >= start]
        if end is not None:
            output = output[output["trade_date"] <= end]
    else:
        output = events.drop_duplicates(["trade_date", "symbol"], keep="last")

    if output.empty:
        return output
    print(
        f"[load] {dataset}: {len(output)} rows, "
        f"{output['symbol'].nunique()} stocks, "
        f"{output['trade_date'].min().date()} ~ {output['trade_date'].max().date()}"
    )
    return output.reset_index(drop=True)
