"""Margin loader — market-level two-financing balance by trade_date.

No tushare network traffic; reads locally-landed parquet.  The raw table is
market-level (one row per exchange per day); we sum across exchanges to a single
market series per ``trade_date`` — a cross-sectional market variable, NOT
mergeable per symbol.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ._common import _filter_partition_paths, _latest_data_dir, _read_partitioned_parquet

AGG_COLUMNS = [
    "rzye",
    "rzmre",
    "rzche",
    "rqye",
    "rqmcl",
    "rzrqye",
    "rqyl",
]


def load_margin(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Load market-level margin (two-financing) balance, aggregated by trade_date."""
    data_dir = _latest_data_dir(
        data_root,
        "margin",
        legacy_sub="a_share_all_margin_latest/data",
    )
    if data_dir is None:
        print("[load] margin: no data found")
        return pd.DataFrame()

    parts = _filter_partition_paths(
        sorted(data_dir.glob("trade_date=*")),
        start_date=start_date,
        end_date=end_date,
    )
    if not parts:
        return pd.DataFrame()
    df = _read_partitioned_parquet(parts, label="margin")
    # Sum across exchanges (SSE + SZSE) into a single market-level row per date.
    agg = df.groupby("trade_date", as_index=False)[AGG_COLUMNS].sum()
    agg["rzye_yoy"] = agg["rzye"].astype(float).pct_change()
    agg["rzrqye_yoy"] = agg["rzrqye"].astype(float).pct_change()
    print(
        f"[load] margin: {len(agg)} market-days, "
        f"{agg['trade_date'].min().date()} ~ {agg['trade_date'].max().date()}"
    )
    return agg
