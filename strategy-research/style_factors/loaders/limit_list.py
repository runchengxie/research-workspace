"""Limit-list loader — limit-up / limit-down event flags by stock-day.

No tushare network traffic; reads locally-landed parquet.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ._common import _filter_partition_paths, _latest_data_dir, _read_partitioned_parquet


def load_limit_list(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Load limit-up / limit-down events by stock-day.

    Returns a frame keyed by ``symbol`` + ``trade_date`` with booleans
    ``is_limit_up`` / ``is_limit_down`` derived from ``limit_type`` / ``status`` /
    ``lu_desc``.  No tushare traffic.
    """
    data_dir = _latest_data_dir(
        data_root,
        "limit_list_ths",
        legacy_sub="a_share_all_limit_list_ths_latest/data",
    )
    if data_dir is None:
        print("[load] limit_list_ths: no data found")
        return pd.DataFrame()

    parts = _filter_partition_paths(
        sorted(data_dir.glob("trade_date=*")),
        start_date=start_date,
        end_date=end_date,
    )
    if not parts:
        return pd.DataFrame()
    df = _read_partitioned_parquet(parts, label="limit_list_ths")
    if "symbol" not in df.columns:
        return pd.DataFrame()

    text_cols = [c for c in ("limit_type", "status", "lu_desc", "tag") if c in df.columns]
    combined = (
        df[text_cols].fillna("").agg(" ".join, axis=1).str.lower() if text_cols else df["symbol"]
    )
    is_up = (
        combined.str.contains("涨停")
        | combined.str.contains("首板")
        | combined.str.contains("limit_up")
    )
    is_down = combined.str.contains("跌停") | combined.str.contains("limit_down")
    out = pd.DataFrame(
        {
            "symbol": df["symbol"].astype(str).values,
            "trade_date": df["trade_date"].values,
            "is_limit_up": is_up.values,
            "is_limit_down": is_down.values,
        }
    )
    out = out.drop_duplicates(["trade_date", "symbol"])
    print(
        f"[load] limit_list_ths: {len(out)} rows, "
        f"{out['symbol'].nunique()} stocks, "
        f"limit_up days={int(out['is_limit_up'].sum())}"
    )
    return out
