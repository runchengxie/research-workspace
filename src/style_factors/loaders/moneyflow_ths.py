"""Moneyflow_ths loader — main/small/medium/large order net inflow by stock-day.

No tushare network traffic; reads locally-landed parquet.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ._common import _filter_partition_paths, _latest_data_dir, _read_partitioned_parquet

COLUMNS = [
    "symbol",
    "trade_date",
    "net_amount",
    "buy_lg_amount",
    "buy_lg_amount_rate",
    "buy_md_amount",
    "buy_md_amount_rate",
    "buy_sm_amount",
    "buy_sm_amount_rate",
]


def load_moneyflow_ths(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Load ths moneyflow (main/small/medium/large order net inflow) by stock-day.

    Returns a frame keyed by ``symbol`` + ``trade_date`` with main net-inflow and
    large/medium/small order net amounts and ratios.  No tushare traffic.
    """
    data_dir = _latest_data_dir(
        data_root,
        "moneyflow_ths",
        legacy_sub="a_share_all_moneyflow_ths_latest/data",
    )
    if data_dir is None:
        print("[load] moneyflow_ths: no data found")
        return pd.DataFrame()

    parts = _filter_partition_paths(
        sorted(data_dir.glob("trade_date=*")),
        start_date=start_date,
        end_date=end_date,
    )
    if not parts:
        return pd.DataFrame()
    df = _read_partitioned_parquet(parts, label="moneyflow_ths")
    df = df[[c for c in COLUMNS if c in df.columns]].copy()
    df = df.drop_duplicates(["trade_date", "symbol"])
    print(
        f"[load] moneyflow_ths: {len(df)} rows, "
        f"{df['symbol'].nunique()} stocks, "
        f"{df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}"
    )
    return df
