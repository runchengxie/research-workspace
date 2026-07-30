"""Holder-structure loader — chip-concentration features by stock-day.

No tushare network traffic; reads locally-landed parquet.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ._common import _filter_partition_paths, _latest_data_dir, _read_partitioned_parquet

COLUMNS = [
    "symbol",
    "trade_date",
    "top10_concentration",
    "top10_float_concentration",
    "top10_inst_hold_ratio",
    "top10_inst_float_hold_ratio",
    "top10_hold_change",
]


def load_holder_structure(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Load holder-structure chip-concentration features by stock-day.

    Picks the Top-10 concentration / institutional-holding columns only (the
    table has 32 columns).  Keyed by ``symbol`` + ``trade_date``.
    """
    data_dir = _latest_data_dir(
        data_root,
        "holder_structure_features",
        legacy_sub="a_share_all_holder_structure_features_latest/data",
    )
    if data_dir is None:
        print("[load] holder_structure_features: no data found")
        return pd.DataFrame()

    parts = _filter_partition_paths(
        sorted(data_dir.glob("trade_date=*")),
        start_date=start_date,
        end_date=end_date,
    )
    if not parts:
        return pd.DataFrame()
    df = _read_partitioned_parquet(parts, label="holder_structure_features")
    df = df[[c for c in COLUMNS if c in df.columns]].copy()
    df = df.drop_duplicates(["trade_date", "symbol"])
    print(
        f"[load] holder_structure_features: {len(df)} rows, "
        f"{df['symbol'].nunique()} stocks, "
        f"{df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}"
    )
    return df
