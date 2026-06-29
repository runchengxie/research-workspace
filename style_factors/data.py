"""Data loading — daily + daily_basic from market-data-platform parquet."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _read_partitioned_parquet(parts: list[Path], *, label: str) -> pd.DataFrame:
    if not parts:
        raise FileNotFoundError(f"No parquet partitions found for {label}")
    return pd.concat(
        [
            pd.read_parquet(path).assign(trade_date=lambda df: pd.to_datetime(df["trade_date"]))
            for path in parts
        ],
        ignore_index=True,
    )


def load_data(data_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load daily and daily_basic parquet files into memory."""
    daily_dir = data_root / "assets/tushare/a_share/daily/a_share_all_daily_latest/data"
    basic_dir = data_root / "assets/tushare/a_share/daily_basic/a_share_all_daily_basic_latest/data"

    daily_parts = sorted(daily_dir.glob("trade_date=*"))
    basic_parts = sorted(basic_dir.glob("trade_date=*"))

    print(f"[load] daily: {len(daily_parts)} partitions, basic: {len(basic_parts)} partitions")

    daily = _read_partitioned_parquet(daily_parts, label="daily")
    basics = _read_partitioned_parquet(basic_parts, label="daily_basic")

    daily = daily.drop_duplicates(["trade_date", "symbol"]).copy()
    basics = basics.drop_duplicates(["trade_date", "symbol"]).copy()

    print(f"[load] daily: {len(daily)} rows, {daily['symbol'].nunique()} stocks")
    print(f"[load] basic: {len(basics)} rows, {basics['symbol'].nunique()} stocks")
    return daily, basics


def load_fina_indicator(data_root: Path) -> pd.DataFrame:
    """Load fina_indicator quarterly data (roe, roa, growth, leverage)."""
    fina_dir = data_root / "assets/tushare/a_share/fundamentals_raw/data/fina_indicator"
    parts = sorted(fina_dir.glob("*.parquet"))
    if not parts:
        print("[load] fina_indicator: no data found — Growth/Leverage disabled")
        return pd.DataFrame()

    df = pd.concat(
        [pd.read_parquet(p) for p in parts],
        ignore_index=True,
    )
    df = df.drop_duplicates(["ts_code", "end_date", "ann_date"])
    # Keep only the latest ann_date per (symbol, end_date)
    df["symbol"] = (
        df["ts_code"]
        .str.replace(".SH", "", regex=False)
        .str.replace(".SZ", "", regex=False)
        .str.replace(".BJ", "", regex=False)
    )
    df["end_date"] = pd.to_datetime(df["end_date"])
    df["ann_date"] = pd.to_datetime(df["ann_date"], errors="coerce")
    df = df.sort_values(["symbol", "end_date", "ann_date"])
    df = df.drop_duplicates(["symbol", "end_date"], keep="last")

    cols = [
        "symbol",
        "end_date",
        "ann_date",
        "roe",
        "roa",
        "netprofit_yoy",
        "or_yoy",
        "debt_to_assets",
    ]
    fina = df[[c for c in cols if c in df.columns]].copy()
    print(
        f"[load] fina_indicator: {len(fina)} rows, "
        f"{fina['symbol'].nunique()} stocks, "
        f"{fina['end_date'].min().date()} ~ {fina['end_date'].max().date()}"
    )
    return fina
