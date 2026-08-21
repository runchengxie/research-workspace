"""Fund-portfolio loader — public-fund ownership breadth features by stock-day.

No tushare network traffic; reads locally-landed parquet from the
``fund_portfolio_features`` asset built by market-data-platform.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ._common import _filter_partition_paths, _latest_data_dir, _read_partitioned_parquet

COLUMNS = [
    "symbol",
    "trade_date",
    "fund_count_holding_stock",
    "fund_count_holding_stock_qoq_change",
    "fund_hold_amount_to_float_share",
    "fund_hold_mv_to_float_mv",
]


def load_fund_portfolio_features(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Load public-fund ownership breadth features by stock-day.

    Picks the ownership-breadth columns only.  Keyed by ``symbol`` +
    ``trade_date``.  PIT availability and forward-fill are applied upstream in
    market-data-platform, so this loader is point-in-time safe.
    """
    data_dir = _latest_data_dir(
        data_root,
        "fund_portfolio_features",
        legacy_sub="a_share_all_fund_portfolio_features_latest/data",
    )
    if data_dir is None:
        print("[load] fund_portfolio_features: no data found")
        return pd.DataFrame()

    parts = _filter_partition_paths(
        sorted(data_dir.glob("trade_date=*")),
        start_date=start_date,
        end_date=end_date,
    )
    if not parts:
        return pd.DataFrame()
    df = _read_partitioned_parquet(parts, label="fund_portfolio_features")
    df = df[[c for c in COLUMNS if c in df.columns]].copy()
    df = df.drop_duplicates(["trade_date", "symbol"])
    print(
        f"[load] fund_portfolio_features: {len(df)} rows, "
        f"{df['symbol'].nunique()} stocks, "
        f"{df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}"
    )
    return df
