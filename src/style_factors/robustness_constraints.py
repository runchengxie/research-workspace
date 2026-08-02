"""Verified constraint-source adapters for robustness analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from .robustness_sources import _normalize_dates, sha256_file


def _verified_constraint_source(
    constraints_dir: Path,
    dataset: str,
) -> tuple[Path, dict[str, Any]]:
    path = constraints_dir / f"{dataset}.parquet"
    receipt_path = constraints_dir / f"{dataset}.receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("dataset", dataset) != dataset:
        raise ValueError(f"{dataset} receipt identifies a different dataset")
    if receipt.get("quality_status") != "complete":
        raise ValueError(f"{dataset} receipt is not quality_status=complete")
    if sha256_file(path) != receipt["sha256"]:
        raise ValueError(f"{dataset} hash does not match its receipt")
    return path, receipt


def load_margin_formation_eligibility(
    constraints_dir: Path,
    formation_dates: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Read margin qualification rows in batches and retain formation dates only."""
    path, receipt = _verified_constraint_source(constraints_dir, "margin_secs")
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
        "margin_sha256": receipt["sha256"],
        "margin_semantics": receipt["semantics"],
    }


def _positive_formation_activity(
    path: Path,
    *,
    tokens: set[str],
    value_columns: tuple[str, ...],
) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    columns = ["trade_date", "ts_code", *value_columns]
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(columns=columns, batch_size=262_144):
        piece = batch.to_pandas()
        piece["trade_date"] = piece["trade_date"].astype(str)
        piece = piece[piece["trade_date"].isin(tokens)]
        if piece.empty:
            continue
        positive = pd.concat(
            [
                pd.to_numeric(piece[column], errors="coerce").fillna(0).gt(0)
                for column in value_columns
            ],
            axis=1,
        ).any(axis=1)
        piece = piece.loc[positive, ["trade_date", "ts_code"]]
        if not piece.empty:
            pieces.append(piece)
    if not pieces:
        return pd.DataFrame(columns=["trade_date", "symbol"])
    frame = pd.concat(pieces, ignore_index=True).rename(columns={"ts_code": "symbol"})
    return _normalize_dates(frame).drop_duplicates(["trade_date", "symbol"])


def load_reported_borrow_activity_eligibility(
    constraints_dir: Path,
    formation_dates: pd.DatetimeIndex,
    margin_eligibility: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build a stricter short proxy from reported activity, never inventory claims."""
    tokens = set(pd.DatetimeIndex(formation_dates).strftime("%Y%m%d"))
    margin_path, margin_receipt = _verified_constraint_source(constraints_dir, "margin_detail")
    slb_path, slb_receipt = _verified_constraint_source(constraints_dir, "slb_sec_detail")
    margin_activity = _positive_formation_activity(
        margin_path, tokens=tokens, value_columns=("rqyl", "rqmcl")
    )
    slb_activity = _positive_formation_activity(
        slb_path, tokens=tokens, value_columns=("lent_qnt",)
    )
    activity = pd.concat([margin_activity, slb_activity], ignore_index=True).drop_duplicates(
        ["trade_date", "symbol"]
    )
    qualified = margin_eligibility[["trade_date", "symbol"]].drop_duplicates()
    proxy = activity.merge(
        qualified, on=["trade_date", "symbol"], how="inner", validate="one_to_one"
    ).sort_values(["trade_date", "symbol"])
    return proxy.reset_index(drop=True), {
        "reported_borrow_activity_rows": int(len(proxy)),
        "reported_borrow_activity_dates": int(proxy["trade_date"].nunique()),
        "reported_borrow_activity_symbols": int(proxy["symbol"].nunique()),
        "margin_detail_activity_rows": int(len(margin_activity)),
        "slb_sec_detail_activity_rows": int(len(slb_activity)),
        "margin_detail_sha256": margin_receipt["sha256"],
        "slb_sec_detail_sha256": slb_receipt["sha256"],
        "reported_borrow_activity_semantics": (
            "qualification intersect reported margin_detail/slb_sec_detail activity; "
            "not borrow inventory"
        ),
    }


def apply_explicit_suspensions(
    daily_clean: pd.DataFrame,
    constraints_dir: Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Overlay explicit suspend_d events onto rows that already carry market prices."""
    path, receipt = _verified_constraint_source(constraints_dir, "suspend_d")
    events = pd.read_parquet(path, columns=["trade_date", "ts_code"])
    events = _normalize_dates(events).rename(columns={"ts_code": "symbol"})
    events = events.drop_duplicates(["trade_date", "symbol"])
    out = daily_clean.copy()
    keys = ["trade_date", "symbol"]
    matched = out.set_index(keys).index.isin(events.set_index(keys).index)
    previously_flagged = out["is_suspended"].fillna(False).astype(bool)
    out["is_suspended"] = previously_flagged | matched
    return out, {
        "suspend_event_rows": int(len(events)),
        "suspend_event_symbols": int(events["symbol"].nunique()),
        "suspend_events_on_price_rows": int(matched.sum()),
        "suspend_events_without_price_rows": int(len(events) - matched.sum()),
        "suspend_newly_flagged_price_rows": int((matched & ~previously_flagged).sum()),
        "suspend_d_sha256": receipt["sha256"],
        "suspend_d_semantics": receipt["semantics"],
    }


def load_st_event_evidence(constraints_dir: Path) -> dict[str, Any]:
    """Validate and summarize provider ST changes as corroborating event evidence."""
    path, receipt = _verified_constraint_source(constraints_dir, "st")
    events = pd.read_parquet(path, columns=["ts_code", "imp_date", "st_type"])
    dates = pd.to_datetime(events["imp_date"].astype("string"), format="%Y%m%d", errors="coerce")
    return {
        "provider_st_event_rows": int(len(events)),
        "provider_st_event_symbols": int(events["ts_code"].nunique()),
        "provider_st_event_start": dates.min().date().isoformat(),
        "provider_st_event_end": dates.max().date().isoformat(),
        "provider_st_event_types": sorted(events["st_type"].dropna().astype(str).unique()),
        "provider_st_event_sha256": receipt["sha256"],
        "provider_st_event_semantics": receipt["semantics"],
    }
