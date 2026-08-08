#!/usr/bin/env python3
"""Reconcile one-day label returns with zero-cost executed generation returns."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reconciliation_inputs(root: Path) -> tuple[pd.DataFrame, dict[str, Path]]:
    daily_path = root / "one_day_cost_independent.parquet"
    generations_path = root / "generations.parquet"
    orders_path = root / "orders.parquet"
    daily = pd.read_parquet(daily_path)
    generations = pd.read_parquet(generations_path)
    orders = pd.read_parquet(orders_path)
    generations = generations.loc[
        generations["horizon"].eq(1) & generations["single_side_cost_bps"].eq(0.0)
    ].copy()
    selected_orders = orders.loc[
        orders["horizon"].eq(1) & orders["single_side_cost_bps"].eq(0.0)
    ].copy()
    selected_orders["blocked"] = selected_orders["status"].astype(str).eq("blocked")
    blocked = (
        selected_orders.groupby(["variant", "generation_id"], sort=False)["blocked"]
        .sum()
        .rename("blocked_orders")
        .reset_index()
    )
    merged = generations.merge(
        blocked,
        on=["variant", "generation_id"],
        how="left",
        validate="one_to_one",
    ).merge(
        daily[
            [
                "variant",
                "trade_date",
                "gross_forward_return_proxy",
                "return_observation_complete",
            ]
        ],
        left_on=["variant", "signal_date"],
        right_on=["variant", "trade_date"],
        how="left",
        validate="one_to_one",
    )
    merged["blocked_orders"] = merged["blocked_orders"].fillna(0).astype(int)
    merged["difference"] = pd.to_numeric(merged["gross_return"], errors="coerce") - pd.to_numeric(
        merged["gross_forward_return_proxy"], errors="coerce"
    )
    return merged, {
        daily_path.name: daily_path,
        generations_path.name: generations_path,
        orders_path.name: orders_path,
    }


def _variant_reconciliation(group: pd.DataFrame, variant: object) -> tuple[dict[str, Any], bool]:
    clean = group.loc[
        group["blocked_orders"].eq(0)
        & group["return_observation_complete"].fillna(False).astype(bool)
    ]
    blocked_rows = group.loc[group["blocked_orders"].gt(0)]
    max_error = float(clean["difference"].abs().max()) if not clean.empty else np.nan
    passed = bool(not clean.empty and max_error <= 1e-12)
    return {
        "variant": str(variant),
        "generations": len(group),
        "clean_complete_generations": len(clean),
        "blocked_generations": len(blocked_rows),
        "blocked_order_count": int(blocked_rows["blocked_orders"].sum()),
        "clean_label_mean": float(clean["gross_forward_return_proxy"].mean()),
        "clean_execution_mean": float(clean["gross_return"].mean()),
        "clean_max_absolute_error": max_error,
        "blocked_execution_mean": (
            float(blocked_rows["gross_return"].mean()) if not blocked_rows.empty else None
        ),
        "clean_reconciliation_passed": passed,
    }, passed


def reconcile(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    merged, input_paths = _reconciliation_inputs(root)
    rows: list[dict[str, Any]] = []
    all_passed = True
    for variant, group in merged.groupby("variant", sort=True):
        row, passed = _variant_reconciliation(group, variant)
        all_passed &= passed
        rows.append(row)
    return {
        "schema_version": "daily_watch20.slow_volume_label_reconciliation.v1",
        "status": "passed" if all_passed else "failed",
        "generated_at": datetime.now(UTC).isoformat(),
        "campaign_receipt_sha256": _sha256(root / "receipt.json"),
        "inputs": {name: _sha256(path) for name, path in input_paths.items()},
        "scope": "horizon_1_zero_cost",
        "interpretation": (
            "clean complete generations must exactly equal stored one-day label returns; "
            "blocked generations are excluded from that equality and reported separately"
        ),
        "variants": rows,
    }


def _write(path: Path, payload: dict[str, Any]) -> None:
    path = path.expanduser().resolve()
    if path.exists():
        raise FileExistsError(f"reconciliation output exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.build-{uuid.uuid4().hex}")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    args = _parser().parse_args()
    payload = reconcile(args.campaign_dir)
    _write(args.output, payload)
    print(json.dumps({"output": str(args.output.resolve()), "status": payload["status"]}))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
