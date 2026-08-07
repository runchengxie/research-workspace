#!/usr/bin/env python3
"""Independently verify a published slow-volume campaign from stored artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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


def _close(left: float, right: float, *, atol: float = 1e-12) -> bool:
    return bool(math.isclose(float(left), float(right), abs_tol=atol, rel_tol=0.0))


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path = path.expanduser().resolve()
    if path.exists():
        raise FileExistsError(f"verification output exists: {path}")
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


def _receipt_checks(root: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    mismatches: list[str] = []
    for name, metadata in receipt["artifacts"].items():
        path = root / name
        if not path.is_file():
            mismatches.append(f"missing:{name}")
            continue
        if path.stat().st_size != int(metadata["size"]):
            mismatches.append(f"size:{name}")
        if _sha256(path) != str(metadata["sha256"]):
            mismatches.append(f"sha256:{name}")
    return {
        "artifact_count": len(receipt["artifacts"]),
        "mismatches": mismatches,
        "passed": not mismatches,
    }


def _score_checks(root: Path) -> dict[str, Any]:
    scores = pd.read_parquet(
        root / "scores.parquet",
        columns=["variant", "trade_date", "symbol", "available_at"],
    )
    variants = tuple(scores["variant"].drop_duplicates().astype(str))
    key_sets = {
        variant: pd.MultiIndex.from_frame(
            scores.loc[scores["variant"].eq(variant), ["trade_date", "symbol"]]
            .sort_values(["trade_date", "symbol"])
            .reset_index(drop=True)
        )
        for variant in variants
    }
    baseline = key_sets["D"]
    same_keys = all(index.equals(baseline) for index in key_sets.values())
    counts = scores.groupby(["variant", "trade_date"]).size()
    available = pd.to_datetime(scores["available_at"], errors="coerce", utc=True).dt.tz_convert(
        "Asia/Shanghai"
    )
    pit = (
        available.notna()
        & available.dt.hour.eq(15)
        & available.dt.minute.eq(1)
        & available.dt.second.eq(0)
    )
    return {
        "variants": list(variants),
        "rows": len(scores),
        "same_stock_date_keys": same_keys,
        "exact_top800_every_variant_date": bool(counts.eq(800).all()),
        "available_at_1501_all_rows": bool(pit.all()),
        "passed": bool(same_keys and counts.eq(800).all() and pit.all()),
    }


def _primary_recompute(root: Path, report: dict[str, Any]) -> dict[str, Any]:
    independent = pd.read_parquet(root / "one_day_cost_independent.parquet")
    daily = pd.read_parquet(root / "one_day_daily_metrics.parquet")
    blocks = pd.read_parquet(root / "block_metrics.parquet")
    ic = independent.pivot(index="trade_date", columns="variant", values="spearman_ic")
    ic_delta = float((ic["D_VD20"] - ic["D"]).mean())
    turnover = independent.groupby("variant")["name_turnover"].mean()
    turnover_delta = float(turnover["D_VD20"] - turnover["D"])
    cost10 = daily.loc[daily["single_side_cost_bps"].eq(10.0)]
    net = cost10.pivot(index="trade_date", columns="variant", values="net_forward_return_proxy")
    net_delta = float((net["D_VD20"] - net["D"]).dropna().mean())
    gross = independent.pivot(
        index="trade_date", columns="variant", values="top20_label_return_mean"
    )
    gross_delta = float((gross["D_VD20"] - gross["D"]).dropna().mean())
    positive_blocks = int(blocks["mean_ic_delta"].gt(0).sum())
    expected = report["decision"]
    comparisons = {
        "ic_delta": _close(ic_delta, expected["ic_delta"]),
        "name_turnover_delta": _close(turnover_delta, expected["name_turnover_delta"]),
        "net_10bps_delta": _close(net_delta, expected["net_10bps_delta"]),
        "top20_gross_delta": _close(gross_delta, expected["top20_gross_delta"]),
        "positive_ic_blocks": positive_blocks == int(expected["positive_ic_blocks"]),
    }
    return {
        "recomputed": {
            "ic_delta": ic_delta,
            "name_turnover_d": float(turnover["D"]),
            "name_turnover_d_vd20": float(turnover["D_VD20"]),
            "name_turnover_delta": turnover_delta,
            "net_10bps_delta": net_delta,
            "top20_gross_delta": gross_delta,
            "positive_ic_blocks": positive_blocks,
        },
        "report_matches": comparisons,
        "passed": all(comparisons.values()),
    }


def _ledger_checks(root: Path) -> dict[str, Any]:
    daily = pd.read_parquet(root / "execution_daily.parquet")
    orders = pd.read_parquet(root / "orders.parquet")
    metrics = pd.read_parquet(root / "execution_metrics.parquet")
    conservation_error = (
        pd.to_numeric(daily["cash"], errors="coerce")
        + pd.to_numeric(daily["positions_value"], errors="coerce")
        - pd.to_numeric(daily["net_nav"], errors="coerce")
    ).abs()
    cost_identity_error = (
        pd.to_numeric(daily["gross_nav_before_cost"], errors="coerce")
        - pd.to_numeric(daily["transaction_cost"], errors="coerce")
        - pd.to_numeric(daily["net_nav"], errors="coerce")
    ).abs()
    expected_order_cost = (
        pd.to_numeric(orders["filled_notional"], errors="coerce").fillna(0.0)
        * pd.to_numeric(orders["single_side_cost_bps"], errors="coerce").fillna(0.0)
        / 10_000.0
    )
    order_cost_error = (
        expected_order_cost - pd.to_numeric(orders["transaction_cost"], errors="coerce").fillna(0.0)
    ).abs()
    required_audit = {
        "raw_open",
        "valuation_open",
        "valuation_price_col",
        "raw_up_limit",
        "raw_down_limit",
        "raw_is_suspended",
    }
    checks = {
        "cash_plus_positions_equals_nav": bool(conservation_error.max() <= 1e-7),
        "pretrade_nav_minus_cost_equals_net_nav": bool(cost_identity_error.max() <= 1e-7),
        "order_cost_equals_filled_notional_times_bps": bool(order_cost_error.max() <= 1e-7),
        "raw_and_valuation_audit_columns_present": required_audit.issubset(orders.columns),
        "all_runs_terminal_complete": bool(metrics["terminal_complete"].astype(bool).all()),
    }
    return {
        "max_conservation_error": float(conservation_error.max()),
        "max_daily_cost_identity_error": float(cost_identity_error.max()),
        "max_order_cost_error": float(order_cost_error.max()),
        "checks": checks,
        "passed": all(checks.values()),
    }


def verify(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
    report = json.loads((root / "report.json").read_text(encoding="utf-8"))
    checks = {
        "receipt": _receipt_checks(root, receipt),
        "scores": _score_checks(root),
        "primary": _primary_recompute(root, report),
        "ledger": _ledger_checks(root),
    }
    passed = all(section["passed"] for section in checks.values())
    return {
        "schema_version": "daily_watch20.slow_volume_campaign.verification.v1",
        "status": "passed" if passed else "failed",
        "generated_at": datetime.now(UTC).isoformat(),
        "campaign_receipt_sha256": _sha256(root / "receipt.json"),
        "campaign_report_sha256": _sha256(root / "report.json"),
        "checks": checks,
    }


def main() -> int:
    args = _parser().parse_args()
    payload = verify(args.campaign_dir)
    _atomic_json(args.output, payload)
    print(json.dumps({"output": str(args.output.resolve()), "status": payload["status"]}))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
