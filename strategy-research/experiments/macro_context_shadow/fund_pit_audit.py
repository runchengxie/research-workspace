"""Audit the point-in-time contract of the public-fund feature asset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _asset_paths(data_root: Path) -> tuple[Path, Path]:
    base = data_root / "assets/tushare/a_share"
    raw = base / "fund_portfolio/a_share_all_20141231_20260529_fund_portfolio/data/**/*.parquet"
    features = base / (
        "fund_portfolio_features/a_share_all_fund_portfolio_features_20260821/data/**/*.parquet"
    )
    return raw, features


def run_audit(data_root: str | Path) -> dict[str, Any]:
    """Return reproducible PIT and vintage findings for the fund asset."""

    import duckdb

    root = Path(data_root).expanduser().resolve()
    raw_path, feature_path = _asset_paths(root)
    con = duckdb.connect()
    raw = str(raw_path)
    features = str(feature_path)

    raw_summary = con.execute(
        f"""
        SELECT COUNT(*) AS rows, COUNT(DISTINCT ts_code) AS funds,
               COUNT(DISTINCT symbol) AS symbols,
               COUNT(DISTINCT end_date) AS report_periods,
               MIN(ann_date) AS min_ann_date, MAX(ann_date) AS max_ann_date,
               MIN(end_date) AS min_report_period, MAX(end_date) AS max_report_period,
               SUM(CASE WHEN CAST(ann_date AS BIGINT) < end_date THEN 1 ELSE 0 END)
                 AS ann_before_report_rows
        FROM read_parquet('{raw}', hive_partitioning=true)
        """
    ).fetchone()
    feature_summary = con.execute(
        f"""
        SELECT COUNT(*) AS rows, COUNT(DISTINCT symbol) AS symbols,
               COUNT(DISTINCT trade_date) AS available_dates,
               MIN(trade_date) AS min_trade_date, MAX(trade_date) AS max_trade_date,
               SUM(CASE WHEN available_date IS NULL OR disclosure_date IS NULL
                         OR trade_date IS NULL THEN 1 ELSE 0 END) AS missing_pit_dates,
               SUM(CASE WHEN CAST(disclosure_date AS BIGINT) > CAST(available_date AS BIGINT)
                         OR CAST(available_date AS BIGINT) > trade_date
                        THEN 1 ELSE 0 END) AS invalid_date_order,
               COUNT(*) - COUNT(DISTINCT (symbol, trade_date)) AS duplicate_symbol_dates
        FROM read_parquet('{features}', hive_partitioning=true)
        """
    ).fetchone()
    availability = con.execute(
        f"""
        WITH dates AS (
          SELECT DISTINCT trade_date FROM read_parquet('{features}', hive_partitioning=true)
        ), expected AS (
          SELECT f.available_date,
                 MIN(d.trade_date) AS expected_trade_date
          FROM read_parquet('{features}', hive_partitioning=true) f
          LEFT JOIN dates d ON d.trade_date >= CAST(f.available_date AS BIGINT)
          GROUP BY f.available_date
        )
        SELECT SUM(CASE WHEN CAST(f.available_date AS BIGINT) = e.expected_trade_date
                        THEN 0 ELSE 1 END) AS non_next_trade_date_rows
        FROM read_parquet('{features}', hive_partitioning=true) f
        JOIN expected e ON e.available_date = f.available_date
        """
    ).fetchone()[0]

    raw_keys = con.execute(
        f"""
        SELECT COUNT(*) - COUNT(DISTINCT (ts_code, symbol, end_date, ann_date))
        FROM read_parquet('{raw}', hive_partitioning=true)
        """
    ).fetchone()[0]
    raw_exact_duplicate_rows = con.execute(
        f"""
        SELECT COUNT(*) - COUNT(DISTINCT (ts_code, ann_date, end_date, symbol, mkv,
                                          amount, stk_mkv_ratio, stk_float_ratio,
                                          platform_market))
        FROM read_parquet('{raw}', hive_partitioning=true)
        """
    ).fetchone()[0]
    raw_conflicting_groups = con.execute(
        f"""
        SELECT COUNT(*) FROM (
          SELECT ts_code, symbol, end_date, ann_date,
                 COUNT(DISTINCT (mkv, amount, stk_mkv_ratio, stk_float_ratio,
                                 platform_market)) AS variants
          FROM read_parquet('{raw}', hive_partitioning=true)
          GROUP BY 1, 2, 3, 4
          HAVING variants > 1
        )
        """
    ).fetchone()[0]
    manifest_candidates = list(
        (root / "assets/tushare/a_share/fund_portfolio_features").glob(
            "a_share_all_fund_portfolio_features_20260821/manifest.yml"
        )
    )
    manifest_text = (
        manifest_candidates[0].read_text(encoding="utf-8") if manifest_candidates else ""
    )
    has_retrieval_history = "retrieved_at" in manifest_text or "vintage" in manifest_text
    result = {
        "data_root": str(root),
        "asset": "tushare.fund_portfolio_features",
        "raw": {
            "rows": raw_summary[0],
            "funds": raw_summary[1],
            "symbols": raw_summary[2],
            "report_periods": raw_summary[3],
            "min_ann_date": raw_summary[4],
            "max_ann_date": raw_summary[5],
            "min_report_period": raw_summary[6],
            "max_report_period": raw_summary[7],
            "ann_before_report_rows": raw_summary[8],
            "duplicate_grain_rows": raw_keys,
            "exact_duplicate_rows": raw_exact_duplicate_rows,
            "conflicting_duplicate_groups": raw_conflicting_groups,
        },
        "features": {
            "rows": feature_summary[0],
            "symbols": feature_summary[1],
            "available_dates": feature_summary[2],
            "min_trade_date": feature_summary[3],
            "max_trade_date": feature_summary[4],
            "missing_pit_dates": feature_summary[5],
            "invalid_date_order": feature_summary[6],
            "duplicate_symbol_dates": feature_summary[7],
            "non_next_trade_date_rows": availability,
        },
        "pit_status": "publication_date_pit",
        "revision_safe": False,
        "vintage_evidence": {
            "manifest_found": bool(manifest_candidates),
            "retrieval_or_vintage_history_declared": has_retrieval_history,
            "finding": (
                "Features are PIT relative to disclosure_date plus the configured delay, "
                "but the asset has no per-row historical retrieval/vintage archive."
            ),
        },
    }
    result["promotion_safe"] = bool(
        raw_summary[8] == 0
        and raw_keys == 0
        and feature_summary[5] == 0
        and feature_summary[6] == 0
        and feature_summary[7] == 0
        and availability == 0
        and has_retrieval_history
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    payload = run_audit(args.data_root)
    Path(args.output).expanduser().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
