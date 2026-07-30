"""Data loading — daily + daily_basic from market-data-platform parquet."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _coerce_date(value: str | pd.Timestamp | None) -> pd.Timestamp | None:
    if value is None:
        return None
    return pd.to_datetime(value)


def _partition_date(path: Path) -> pd.Timestamp | None:
    if not path.name.startswith("trade_date="):
        return None
    raw = path.name.split("=", 1)[1]
    return pd.to_datetime(raw, format="%Y%m%d", errors="coerce")


def _filter_partition_paths(
    parts: list[Path],
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> list[Path]:
    start = _coerce_date(start_date)
    end = _coerce_date(end_date)
    selected: list[Path] = []
    for path in parts:
        date = _partition_date(path)
        if date is None or pd.isna(date):
            selected.append(path)
            continue
        if start is not None and date < start:
            continue
        if end is not None and date > end:
            continue
        selected.append(path)
    return selected


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


def load_data(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load daily and daily_basic parquet files into memory."""
    daily_cols = ["trade_date", "symbol", "close", "pct_chg", "amount"]
    basic_cols = ["trade_date", "symbol", "total_mv", "pb", "pe_ttm", "turnover_rate"]
    daily_dir = data_root / "assets/tushare/a_share/daily/a_share_all_daily_latest/data"
    basic_dir = data_root / "assets/tushare/a_share/daily_basic/a_share_all_daily_basic_latest/data"

    daily_parts = _filter_partition_paths(
        sorted(daily_dir.glob("trade_date=*")),
        start_date=start_date,
        end_date=end_date,
    )
    basic_parts = _filter_partition_paths(
        sorted(basic_dir.glob("trade_date=*")),
        start_date=start_date,
        end_date=end_date,
    )

    print(f"[load] daily: {len(daily_parts)} partitions, basic: {len(basic_parts)} partitions")

    daily = _read_partitioned_parquet(daily_parts, label="daily")
    basics = _read_partitioned_parquet(basic_parts, label="daily_basic")

    daily = daily.drop_duplicates(["trade_date", "symbol"]).copy()
    basics = basics.drop_duplicates(["trade_date", "symbol"]).copy()
    daily = daily[daily_cols].copy()
    basics = basics[basic_cols].copy()

    print(f"[load] daily: {len(daily)} rows, {daily['symbol'].nunique()} stocks")
    print(f"[load] basic: {len(basics)} rows, {basics['symbol'].nunique()} stocks")
    return daily, basics


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
    df["symbol"] = (
        df["ts_code"]
        .str.replace(".SH", "", regex=False)
        .str.replace(".SZ", "", regex=False)
        .str.replace(".BJ", "", regex=False)
    )
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
