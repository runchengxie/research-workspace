"""Version-pinned source adapters for the full-history robustness profile."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

EARLY_END = pd.Timestamp("2014-12-31")
CONSTRAINTS_VERSION = "tushare_constraints_20260802"
PIT_VINTAGE = "20260802"
PIT_FIELDS = ("roe", "roa", "debt_to_assets", "operating_cashflow", "net_profit")


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 for an immutable input file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _partition_files(asset_dir: Path, *, start: str, end: str) -> list[Path]:
    data_dir = asset_dir / "data"
    files = []
    for path in data_dir.glob("trade_date=*/part.parquet"):
        token = path.parent.name.removeprefix("trade_date=")
        if start <= token <= end:
            files.append(path)
    if not files:
        raise FileNotFoundError(f"No trade-date parquet parts in {asset_dir} for {start}..{end}")
    return sorted(files)


def _read_parts(asset_dir: Path, *, start: str, end: str, columns: list[str]) -> pd.DataFrame:
    files = _partition_files(asset_dir, start=start, end=end)
    return pq.read_table(files, columns=columns, partitioning=None).to_pandas()


def _normalize_dates(frame: pd.DataFrame, column: str = "trade_date") -> pd.DataFrame:
    out = frame.copy()
    out[column] = pd.to_datetime(out[column].astype("string"), format="%Y%m%d", errors="coerce")
    return out.dropna(subset=[column])


def _load_early_source_frames(
    data_root: Path,
    *,
    start: str,
    end: str,
) -> tuple[list[pd.DataFrame], Path, Path]:
    base = data_root / "assets/tushare/a_share"
    daily = _read_parts(
        base / "daily/a_share_all_daily_latest",
        start=start,
        end=end,
        columns=["trade_date", "symbol", "close", "pct_chg", "amount"],
    )
    basic = _read_parts(
        base / "daily_basic/a_share_all_daily_basic_latest",
        start=start,
        end=end,
        columns=[
            "trade_date",
            "symbol",
            "total_mv",
            "pb",
            "pe_ttm",
            "turnover_rate",
            "dv_ttm",
            "ps_ttm",
        ],
    )
    adj_asset = base / "adj_factor/a_share_all_20080101_20141231_adj_factor"
    adj = _read_parts(
        adj_asset,
        start=start,
        end=end,
        columns=["trade_date", "symbol", "adj_factor"],
    )
    limit_asset = base / "limit_status/a_share_limit_status_20080101_20141231"
    limits = _read_parts(
        limit_asset,
        start=start,
        end=end,
        columns=["trade_date", "symbol", "up_limit", "down_limit"],
    )
    frames = [_normalize_dates(frame) for frame in (daily, basic, adj, limits)]
    keys = ["trade_date", "symbol"]
    for label, frame in zip(
        ("daily", "daily_basic", "adj_factor", "limit_status"), frames, strict=True
    ):
        if frame.duplicated(keys).any():
            raise ValueError(f"early {label} has duplicate trade_date/symbol keys")
    return frames, adj_asset, limit_asset


def build_early_daily_clean(
    data_root: Path,
    instruments: pd.DataFrame,
    *,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build the 2008–2014 clean bridge from immutable raw overlays."""
    start = start_date.strftime("%Y%m%d")
    end = min(end_date, EARLY_END).strftime("%Y%m%d")
    frames, adj_asset, limit_asset = _load_early_source_frames(
        data_root,
        start=start,
        end=end,
    )
    daily, basic, adj, limits = frames
    keys = ["trade_date", "symbol"]
    out = daily.merge(basic, on=keys, how="left", validate="one_to_one")
    out = out.merge(adj, on=keys, how="left", validate="one_to_one")
    out = out.merge(limits, on=keys, how="left", validate="one_to_one")
    out["tr_close"] = out["close"] * out["adj_factor"]
    out["is_limit_up"] = out["close"].ge(out["up_limit"]) & out["up_limit"].notna()
    out["is_limit_down"] = out["close"].le(out["down_limit"]) & out["down_limit"].notna()
    out["is_suspended"] = False

    first_trade = out.groupby("symbol", sort=False)["trade_date"].min()
    listing = instruments.set_index("symbol")["list_date"]
    effective = pd.concat([listing, first_trade], axis=1).min(axis=1)
    list_dates = out["symbol"].map(effective)
    out["listed_days"] = (out["trade_date"] - list_dates).dt.days
    keep = [
        "trade_date",
        "symbol",
        "close",
        "tr_close",
        "adj_factor",
        "pct_chg",
        "amount",
        "total_mv",
        "pb",
        "pe_ttm",
        "turnover_rate",
        "dv_ttm",
        "ps_ttm",
        "is_limit_up",
        "is_limit_down",
        "is_suspended",
        "listed_days",
    ]
    stats = {
        "early_rows": int(len(out)),
        "early_symbols": int(out["symbol"].nunique()),
        "early_dates": int(out["trade_date"].nunique()),
        "early_daily_basic_join_rate": float(out["total_mv"].notna().mean()),
        "early_adj_factor_join_rate": float(out["adj_factor"].notna().mean()),
        "early_limit_status_join_rate": float(out["up_limit"].notna().mean()),
        "early_tr_close_coverage": float(out["tr_close"].notna().mean()),
        "early_adj_factor_asset": str(adj_asset),
        "early_limit_status_asset": str(limit_asset),
    }
    return out[keep].sort_values(keys).reset_index(drop=True), stats


def build_early_universe(daily: pd.DataFrame, *, before: pd.Timestamp) -> pd.DataFrame:
    """Reproduce the full-market 60-day trailing-median universe contract."""
    early = daily.loc[daily["trade_date"] < before, ["trade_date", "symbol", "amount"]].copy()
    early = early.sort_values(["symbol", "trade_date"])
    lagged = early.groupby("symbol", sort=False)["amount"].shift(1)
    early["liq_metric"] = lagged.groupby(early["symbol"], sort=False).transform(
        lambda values: values.rolling(60, min_periods=30).median()
    )
    dates = pd.DatetimeIndex(early["trade_date"].unique()).sort_values()
    month_ends = pd.Series(dates, index=dates).groupby(dates.to_period("M")).max().tolist()
    universe = early.loc[
        early["trade_date"].isin(month_ends) & early["liq_metric"].notna(),
        ["trade_date", "symbol"],
    ]
    return universe.sort_values(["trade_date", "symbol"]).reset_index(drop=True)


def expand_st_intervals(
    constraints_dir: Path,
    formation_dates: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Expand reconstructed ST name intervals only onto monthly formation dates."""
    interval_path = constraints_dir / "st_intervals_reconstructed.parquet"
    receipt_path = constraints_dir / "st_history_reconstructed.receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    actual_hash = sha256_file(interval_path)
    if actual_hash != receipt["intervals_sha256"]:
        raise ValueError("ST interval hash does not match its receipt")
    intervals = pd.read_parquet(
        interval_path,
        columns=["ts_code", "interval_start", "interval_end", "pit_class"],
    )
    intervals["interval_start"] = pd.to_datetime(intervals["interval_start"], format="%Y%m%d")
    intervals["interval_end"] = pd.to_datetime(intervals["interval_end"], format="%Y%m%d")
    rows: list[pd.DataFrame] = []
    dates = pd.DatetimeIndex(formation_dates).normalize()
    for row in intervals.itertuples(index=False):
        active = dates[(dates >= row.interval_start) & (dates <= row.interval_end)]
        if len(active):
            rows.append(pd.DataFrame({"trade_date": active, "symbol": row.ts_code}))
    history = (
        pd.concat(rows, ignore_index=True).drop_duplicates()
        if rows
        else pd.DataFrame(columns=["trade_date", "symbol"])
    )
    return history, {
        "st_interval_rows": int(len(intervals)),
        "st_formation_rows": int(len(history)),
        "st_symbols": int(history["symbol"].nunique()) if not history.empty else 0,
        "st_pit_class": receipt["pit_class"],
        "st_revision_safe": bool(receipt["revision_safe"]),
        "st_cross_validation": receipt["cross_validation"],
        "st_intervals_sha256": actual_hash,
    }


def load_margin_formation_eligibility(
    constraints_dir: Path,
    formation_dates: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read margin qualification rows in batches and retain formation dates only."""
    path = constraints_dir / "margin_secs.parquet"
    receipt_path = constraints_dir / "margin_secs.receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    actual_hash = sha256_file(path)
    if actual_hash != receipt["sha256"]:
        raise ValueError("margin_secs hash does not match its receipt")
    tokens = set(pd.DatetimeIndex(formation_dates).strftime("%Y%m%d"))
    pieces: list[pd.DataFrame] = []
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(columns=["trade_date", "ts_code"], batch_size=262_144):
        piece = batch.to_pandas()
        piece = piece[piece["trade_date"].isin(tokens)]
        if not piece.empty:
            pieces.append(piece)
    frame = pd.concat(pieces, ignore_index=True).rename(columns={"ts_code": "symbol"})
    frame = _normalize_dates(frame).drop_duplicates(["trade_date", "symbol"])
    return frame, {
        "margin_formation_rows": int(len(frame)),
        "margin_formation_dates": int(frame["trade_date"].nunique()),
        "margin_symbols": int(frame["symbol"].nunique()),
        "margin_sha256": actual_hash,
        "margin_semantics": receipt["semantics"],
    }


def _update_pit_state(
    state: dict[str, dict[str, tuple[tuple[str, str, str, str], float]]],
    record: dict[str, Any],
) -> None:
    symbol = str(record["symbol"])
    priority = (
        str(record["report_period"]),
        str(record["available_date"]),
        str(record["disclosure_date"]),
        str(record["_source_retrieved_at"]),
    )
    fields = state.setdefault(symbol, {})
    for field in PIT_FIELDS:
        value = record[field]
        if pd.notna(value) and (field not in fields or priority > fields[field][0]):
            fields[field] = (priority, float(value))


def _pit_formation_frame(
    date: pd.Timestamp,
    symbols: list[str],
    state: dict[str, dict[str, tuple[tuple[str, str, str, str], float]]],
) -> pd.DataFrame:
    rows: dict[str, Any] = {"trade_date": [date] * len(symbols), "symbol": symbols}
    for field in PIT_FIELDS:
        rows[field] = [state.get(symbol, {}).get(field, (None, np.nan))[1] for symbol in symbols]
    return pd.DataFrame(rows)


def load_reconstructed_pit_panel(
    vintage_dir: Path,
    universe: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Materialize reconstructed PIT v2 fields at formation dates from sealed events."""
    seal = json.loads((vintage_dir / "SEALED.json").read_text(encoding="utf-8"))
    manifest_path = vintage_dir / seal["manifest"]
    if sha256_file(manifest_path) != seal["manifest_sha256"]:
        raise ValueError("PIT vintage top-level manifest hash does not match SEALED.json")
    pit_manifest = (vintage_dir / "pit/manifest.yml").read_text(encoding="utf-8")
    if "tushare.a_share.fundamentals.pit.v2" not in pit_manifest:
        raise ValueError("PIT asset is not schema v2")
    event_columns = [
        "symbol",
        "available_date",
        "report_period",
        "disclosure_date",
        "_source_retrieved_at",
        *PIT_FIELDS,
    ]
    events = pd.read_parquet(vintage_dir / "pit/data", columns=event_columns)
    for column in ("available_date", "report_period", "disclosure_date"):
        events[column] = events[column].astype("string").fillna("").str.replace("-", "")
    events = events.sort_values(
        ["available_date", "_source_retrieved_at", "symbol", "report_period", "disclosure_date"],
        kind="mergesort",
    ).reset_index(drop=True)
    dates = sorted(pd.DatetimeIndex(universe["trade_date"].unique()).normalize())
    symbols_by_date = {
        pd.Timestamp(date): group["symbol"].astype(str).tolist()
        for date, group in universe.groupby("trade_date", sort=True)
    }
    state: dict[str, dict[str, tuple[tuple[str, str, str, str], float]]] = {}
    records = events.to_dict(orient="records")
    cursor = 0
    output: list[pd.DataFrame] = []
    for date in dates:
        token = date.strftime("%Y%m%d")
        while cursor < len(records) and records[cursor]["available_date"] <= token:
            _update_pit_state(state, records[cursor])
            cursor += 1
        symbols = symbols_by_date[pd.Timestamp(date)]
        output.append(_pit_formation_frame(pd.Timestamp(date), symbols, state))
    panel = pd.concat(output, ignore_index=True)
    panel = panel.rename(columns={"operating_cashflow": "n_cashflow_act"})
    return panel, {
        "pit_vintage": PIT_VINTAGE,
        "pit_schema": "tushare.a_share.fundamentals.pit.v2",
        "pit_panel_rows": int(len(panel)),
        "pit_event_rows": int(len(events)),
        "pit_panel_dates": int(panel["trade_date"].nunique()),
        "pit_panel_symbols": int(panel["symbol"].nunique()),
        "pit_field_coverage": {
            column: float(panel[column].notna().mean())
            for column in ("roe", "roa", "debt_to_assets", "n_cashflow_act", "net_profit")
        },
        "pit_class": "reconstructed_pit_before_20260802",
        "revision_safe_from": PIT_VINTAGE,
        "historical_revision_safe": False,
        "vintage_manifest_sha256": seal["manifest_sha256"],
    }
