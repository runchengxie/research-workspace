"""Data loading — daily + daily_basic + local tushare datasets from market-data-platform parquet.

The new loaders (moneyflow_ths, holder_structure_features, ths_member/ths_index,
margin, limit_list_ths) consume datasets that market-data-platform has already
landed locally.  They require NO tushare network traffic.  Several of them
(express/hk_hold/sw_index, industry-constituent mappings, etc.) are intentionally
NOT pulled here — they would require changes to the market-data-platform ingest
scripts and are out of scope for this integration.
"""

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
    frames = []
    for path in parts:
        df = pd.read_parquet(path)
        if "trade_date" not in df.columns:
            # Hive-partitioned dir without an in-file trade_date column:
            # recover it from the trade_date=YYYYMMDD directory name.
            dt = _partition_date(path)
            if dt is not None and not pd.isna(dt):
                df = df.assign(trade_date=dt)
        if "trade_date" in df.columns:
            df["trade_date"] = pd.to_datetime(df["trade_date"])
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def load_data(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
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


def _latest_data_dir(data_root: Path, dataset: str, legacy_sub: str | None = None) -> Path | None:
    """Resolve the ``data`` directory of a ``*_latest`` dataset under a_share.

    Accepts the several on-disk layouts seen on the data platform:
    ``<dataset>/a_share_all_<dataset>_latest/data``,
    ``<dataset>/<dataset>_latest/data``, ``<dataset>/data``, and an explicit
    ``legacy_sub`` path.  A directory qualifies if it contains either parquet
    files or ``trade_date=`` hive partitions.  Returns ``None`` otherwise.
    """
    base = data_root / "assets/tushare/a_share" / dataset
    candidates = []
    if legacy_sub is not None:
        candidates.append(base / legacy_sub)
    candidates.extend(
        [
            base / f"a_share_all_{dataset}_latest" / "data",
            base / f"{dataset}_latest" / "data",
            base / "data",
        ]
    )
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        if sorted(candidate.glob("*.parquet")) or sorted(candidate.glob("trade_date=*")):
            return candidate
    return None


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
    cols = [
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
    df = df[[c for c in cols if c in df.columns]].copy()
    df = df.drop_duplicates(["trade_date", "symbol"])
    print(
        f"[load] moneyflow_ths: {len(df)} rows, "
        f"{df['symbol'].nunique()} stocks, "
        f"{df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}"
    )
    return df


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
    cols = [
        "symbol",
        "trade_date",
        "top10_concentration",
        "top10_float_concentration",
        "top10_inst_hold_ratio",
        "top10_inst_float_hold_ratio",
        "top10_hold_change",
    ]
    df = df[[c for c in cols if c in df.columns]].copy()
    df = df.drop_duplicates(["trade_date", "symbol"])
    print(
        f"[load] holder_structure_features: {len(df)} rows, "
        f"{df['symbol'].nunique()} stocks, "
        f"{df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}"
    )
    return df


def load_sw_industry_membership(data_root: Path) -> pd.DataFrame:
    """Build a PIT (point-in-time) SW industry membership long table.

    Source: locally-landed tushare Shenwan (申万) industry datasets under
    ``assets/tushare/a_share/``:

    - ``sw_industry_member`` — constituent rows ``[index_code, con_code,
      in_date, out_date, is_new, industry_code, industry_name]``.  ``con_code``
      is the tushare ts_code (e.g. ``'000019.SZ'``), identical to the panel
      ``symbol`` format.  ``in_date``/``out_date`` form a PIT validity window;
      ``out_date=None`` means the stock is still in that industry.
    - ``sw_industry`` — the industry dictionary; we keep only ``level=='L1'``
      so each stock maps to a single L1 sector name.

    Returns a long frame ``[symbol, in_date, out_date, industry_l1]`` where
    each row is a valid (symbol, industry) interval.  ``out_date=None`` denotes
    "currently active".  Consumers should asof/interval-merge by ``trade_date``.

    This is the authoritative industry input for NEUTRALIZATION.  It is PIT —
    a stock's L1 sector is the one whose window contains the trade_date, which
    avoids look-ahead and static-map drift.  Do NOT use ``ths_member`` (static)
    for neutralization.  No tushare network traffic.
    """
    member_dir = _latest_data_dir(
        data_root,
        "sw_industry_member",
        legacy_sub="a_share_all_sw_industry_member_latest/data",
    )
    dict_dir = _latest_data_dir(
        data_root,
        "sw_industry",
        legacy_sub="a_share_all_sw_industry_latest/data",
    )
    if member_dir is None:
        print("[load] sw_industry_member: no data found — PIT industry neutralization disabled")
        return pd.DataFrame(columns=["symbol", "in_date", "out_date", "industry_l1"])

    member_files = sorted(member_dir.glob("*.parquet")) or sorted(
        member_dir.glob("trade_date=*/*.parquet")
    )
    if not member_files:
        print("[load] sw_industry_member: no parquet files")
        return pd.DataFrame(columns=["symbol", "in_date", "out_date", "industry_l1"])
    member = pd.concat([pd.read_parquet(p) for p in member_files], ignore_index=True)

    if "con_code" not in member.columns:
        print("[load] sw_industry_member: missing con_code column")
        return pd.DataFrame(columns=["symbol", "in_date", "out_date", "industry_l1"])

    if dict_dir is not None:
        dict_files = sorted(dict_dir.glob("*.parquet")) or sorted(
            dict_dir.glob("trade_date=*/part.parquet")
        )
        if dict_files:
            industry_dict = pd.concat(
                [pd.read_parquet(p) for p in dict_files], ignore_index=True
            )
            l1 = industry_dict[industry_dict.get("level", "") == "L1"]
            if not l1.empty and {"industry_code", "industry_name"} <= set(l1.columns):
                l1_map = dict(
                    zip(l1["industry_code"].astype(str), l1["industry_name"].astype(str))
                )
                # member.industry_code may already carry the L1 code; map to name.
                member = member.copy()
                member["industry_l1"] = (
                    member["industry_code"].astype(str).map(l1_map)
                )
                # Fallback: if industry_name present and l1_map empty, trust name.
                if member["industry_l1"].isna().any() and "industry_name" in member.columns:
                    member["industry_l1"] = member["industry_l1"].fillna(
                        member["industry_name"].astype(str)
                    )
            elif "industry_name" in member.columns:
                member = member.copy()
                member["industry_l1"] = member["industry_name"].astype(str)
        elif "industry_name" in member.columns:
            member = member.copy()
            member["industry_l1"] = member["industry_name"].astype(str)
    elif "industry_name" in member.columns:
        member = member.copy()
        member["industry_l1"] = member["industry_name"].astype(str)

    member["symbol"] = member["con_code"].astype(str)
    member["in_date"] = pd.to_datetime(member["in_date"], errors="coerce")
    member["out_date"] = pd.to_datetime(member["out_date"], errors="coerce")

    out = member[["symbol", "in_date", "out_date", "industry_l1"]].dropna(
        subset=["symbol", "industry_l1"]
    )
    if out.empty:
        print("[load] sw_industry_member: no usable L1 rows")
        return out
    print(
        f"[load] sw_industry_member(PIT): {len(out)} membership rows, "
        f"{out['symbol'].nunique()} stocks, "
        f"{out['industry_l1'].nunique()} L1 industries"
    )
    return out.reset_index(drop=True)


def load_ths_member(data_root: Path) -> dict[str, str]:
    """Build a ``symbol -> industry`` classification map from ths_member/ths_index.

    NOTE (data gap): the landed ``ths_member`` table only maps constituents to the
    two all-A indices (``700001.TI`` / ``700002.TI``, ``type=BB``).  The 1077
    ths industry indices (``type=I``) have NO constituent table landed, and
    ``sw_industry`` is empty.  So a real per-stock industry map is NOT available
    locally yet.  This loader returns what the data supports — all mapped stocks
    are labelled ``"全A"`` — and exists so the rest of the pipeline can consume a
    symbol->industry dict once market-data-platform lands an industry-constituent
    dataset (e.g. sw_industry_member or a ths industry-member table).  Do NOT treat
    the returned map as a working industry neutralization input.
    """
    member_dir = _latest_data_dir(data_root, "ths_member")
    index_dir = _latest_data_dir(data_root, "ths_index")
    if member_dir is None:
        print("[load] ths_member: no data found — industry neutralization disabled")
        return {}

    member = pd.read_parquet(sorted(member_dir.glob("*.parquet"))[0])
    if "con_code" not in member.columns:
        return {}
    mapping = dict.fromkeys(member["con_code"].astype(str).unique().tolist(), "全A")
    print(
        f"[load] ths_member: {len(mapping)} symbols mapped "
        f"(placeholder '全A'; real industry map not landed)"
    )
    if index_dir is not None:
        idx = pd.read_parquet(sorted(index_dir.glob("*.parquet"))[0])
        n_industry = int((idx["type"] == "I").sum()) if "type" in idx.columns else 0
        if n_industry:
            print(
                f"[load] ths_index: {n_industry} industry indices available "
                f"but no constituent table landed — neutralization pending"
            )
    return mapping


def load_margin(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Load market-level margin (two-financing) balance, aggregated by trade_date.

    The raw table is market-level (one row per exchange per day).  We sum across
    exchanges to a single market series per ``trade_date`` — it is a cross-sectional
    market variable, NOT mergeable per symbol.  No tushare traffic.
    """
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
    agg = (
        df.groupby("trade_date", as_index=False)[
            ["rzye", "rzmre", "rzche", "rqye", "rqmcl", "rzrqye", "rqyl"]
        ]
        .sum()
    )
    agg["rzye_yoy"] = agg["rzye"].astype(float).pct_change()
    agg["rzrqye_yoy"] = agg["rzrqye"].astype(float).pct_change()
    print(
        f"[load] margin: {len(agg)} market-days, "
        f"{agg['trade_date'].min().date()} ~ {agg['trade_date'].max().date()}"
    )
    return agg


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
    combined = df[text_cols].fillna("").agg(" ".join, axis=1).str.lower() if text_cols else df["symbol"]
    is_up = combined.str.contains("涨停") | combined.str.contains("首板") | combined.str.contains("limit_up")
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
