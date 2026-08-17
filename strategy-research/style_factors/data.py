"""Data loading — daily + daily_basic + local tushare datasets from market-data-platform parquet.

The dataset-specific loaders (moneyflow_ths, holder_structure, ths_member/ths_index,
margin, limit_list_ths, sw_industry membership) live in the ``loaders`` subpackage
and are re-exported here so the public API of ``data`` is unchanged.  They require
NO tushare network traffic.  Several datasets (express/hk_hold/sw_index,
industry-constituent mappings, etc.) are intentionally NOT pulled here — they would
require changes to the market-data-platform ingest scripts and are out of scope for
this integration.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .loaders import (
    load_holder_structure,
    load_limit_list,
    load_margin,
    load_moneyflow_ths,
    load_sw_industry_membership,
    load_ths_member,
)

__all__ = [
    "load_cashflow",
    "load_data",
    "load_fina_indicator",
    "load_holder_structure",
    "load_limit_list",
    "load_margin",
    "load_moneyflow_ths",
    "load_sw_industry_membership",
    "load_ths_member",
]


def _coerce_date(value: str | pd.Timestamp | None) -> pd.Timestamp | None:
    if value is None:
        return None
    return pd.to_datetime(value)


def load_data(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
    basics_rebalance_only: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load daily and daily_basic parquet files into memory."""
    daily_cols = ["trade_date", "symbol", "close", "pct_chg", "amount"]
    basic_cols = [
        "trade_date",
        "symbol",
        "total_mv",
        "pb",
        "pe_ttm",
        "turnover_rate",
        "dv_ttm",
        "ps_ttm",
    ]
    daily_dir = data_root / "assets/tushare/a_share/daily/a_share_all_daily_latest/data"
    basic_dir = data_root / "assets/tushare/a_share/daily_basic/a_share_all_daily_basic_latest/data"

    daily_parts = [
        p for p in sorted(daily_dir.glob("trade_date=*")) if _in_window(p, start_date, end_date)
    ]
    basic_parts = [
        p for p in sorted(basic_dir.glob("trade_date=*")) if _in_window(p, start_date, end_date)
    ]
    if basics_rebalance_only:
        dated_parts = [(_partition_date(path), path) for path in daily_parts]
        dated_parts = [(date, path) for date, path in dated_parts if pd.notna(date)]
        month_end_dates = {
            max(group) for _period, group in _group_partition_dates_by_month(dated_parts).items()
        }
        basic_parts = [path for path in basic_parts if _partition_date(path) in month_end_dates]

    print(f"[load] daily: {len(daily_parts)} partitions, basic: {len(basic_parts)} partitions")

    daily = _read_daily(daily_parts, label="daily")
    basics = _read_daily(basic_parts, label="daily_basic")

    daily = daily.drop_duplicates(["trade_date", "symbol"]).copy()
    basics = basics.drop_duplicates(["trade_date", "symbol"]).copy()
    daily = daily[daily_cols].copy()
    basics = basics[basic_cols].copy()

    print(f"[load] daily: {len(daily)} rows, {daily['symbol'].nunique()} stocks")
    print(f"[load] basic: {len(basics)} rows, {basics['symbol'].nunique()} stocks")
    return daily, basics


def _group_partition_dates_by_month(
    dated_parts: list[tuple[pd.Timestamp, Path]],
) -> dict[pd.Period, list[pd.Timestamp]]:
    grouped: dict[pd.Period, list[pd.Timestamp]] = {}
    for date, _path in dated_parts:
        grouped.setdefault(date.to_period("M"), []).append(date)
    return grouped


def _partition_date(path: Path) -> pd.Timestamp | None:
    if not path.name.startswith("trade_date="):
        return None
    raw = path.name.split("=", 1)[1]
    return pd.to_datetime(raw, format="%Y%m%d", errors="coerce")


def _in_window(
    path: Path,
    start_date: str | pd.Timestamp | None,
    end_date: str | pd.Timestamp | None,
) -> bool:
    date = _partition_date(path)
    if date is None or pd.isna(date):
        return True
    start = _coerce_date(start_date)
    end = _coerce_date(end_date)
    if start is not None and date < start:
        return False
    return not (end is not None and date > end)


def _read_daily(parts: list[Path], *, label: str) -> pd.DataFrame:
    if not parts:
        return pd.DataFrame()
    frames = []
    for path in parts:
        df = pd.read_parquet(path)
        if "trade_date" not in df.columns:
            dt = _partition_date(path)
            if dt is not None and not pd.isna(dt):
                df = df.assign(trade_date=dt)
        if "trade_date" in df.columns:
            df["trade_date"] = pd.to_datetime(df["trade_date"])
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _symbol_from_ts_code(series: pd.Series) -> pd.Series:
    return (
        series.str.replace(".SH", "", regex=False)
        .str.replace(".SZ", "", regex=False)
        .str.replace(".BJ", "", regex=False)
    )


def _fina_indicator_dir(data_root: Path) -> Path | None:
    """Resolve the fina_indicator parquet directory.

    Backward compatible: try the legacy ``fundamentals_raw/data/fina_indicator``
    path first; if it has no data, fall back to the top800_union dataset which is
    the one actually populated on the data platform.
    """
    legacy = data_root / "assets/tushare/a_share/fundamentals_raw/data/fina_indicator"
    if sorted(legacy.glob("*.parquet")):
        return legacy
    fallback = (
        data_root
        / "assets/tushare/a_share/fundamentals_raw"
        / "a_share_top800_union_20150227_20260529_fina_indicator"
        / "data"
        / "fina_indicator"
    )
    if sorted(fallback.glob("*.parquet")):
        print(
            "[load] WARNING: legacy fina_indicator path empty — "
            "falling back to a_share_top800_union fina_indicator"
        )
        return fallback
    return None


def load_fina_indicator(
    data_root: Path,
    *,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Load fina_indicator quarterly data (roe, roa, growth, leverage)."""
    fina_dir = _fina_indicator_dir(data_root)
    if fina_dir is None:
        print("[load] fina_indicator: no data found — Growth/Leverage disabled")
        return pd.DataFrame()

    parts = sorted(fina_dir.glob("*.parquet"))
    df = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    df = df.drop_duplicates(["ts_code", "end_date", "ann_date"])
    # Keep only the latest ann_date per (symbol, end_date)
    df["symbol"] = _symbol_from_ts_code(df["ts_code"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    df["ann_date"] = pd.to_datetime(df["ann_date"], errors="coerce")
    end = _coerce_date(end_date)
    if end is not None:
        df = df[df["ann_date"].isna() | (df["ann_date"] <= end)].copy()
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


def load_cashflow(
    data_root: Path,
    *,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Load cashflow quarterly data for cashflow-quality (OCF / net profit).

    Returns a frame with ``symbol, end_date, ann_date, n_cashflow_act,
    net_profit`` so it can be merged into the fina panel by announcement date.
    """
    cf_dir = (
        data_root
        / "assets/tushare/a_share/fundamentals_raw"
        / "a_share_top800_union_20150227_20260529_cashflow"
        / "data"
        / "cashflow"
    )
    parts = sorted(cf_dir.glob("*.parquet"))
    if not parts:
        print("[load] cashflow: no data found — cashflow-quality disabled")
        return pd.DataFrame()

    df = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    df = df.drop_duplicates(["ts_code", "end_date", "ann_date"])
    df["symbol"] = _symbol_from_ts_code(df["ts_code"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    df["ann_date"] = pd.to_datetime(df["ann_date"], errors="coerce")
    end = _coerce_date(end_date)
    if end is not None:
        df = df[df["ann_date"].isna() | (df["ann_date"] <= end)].copy()
    df = df.sort_values(["symbol", "end_date", "ann_date"])
    df = df.drop_duplicates(["symbol", "end_date"], keep="last")

    cols = ["symbol", "end_date", "ann_date", "n_cashflow_act", "net_profit"]
    cashflow = df[[c for c in cols if c in df.columns]].copy()
    print(
        f"[load] cashflow: {len(cashflow)} rows, "
        f"{cashflow['symbol'].nunique()} stocks, "
        f"{cashflow['end_date'].min().date()} ~ {cashflow['end_date'].max().date()}"
    )
    return cashflow
