"""Run the reproducible public-fund crowding shadow scan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def summarize_rows(rows: Any) -> dict[str, Any]:
    """Convert grouped scan rows into a compact JSON-safe report."""

    report: dict[str, Any] = {"groups": []}
    for row in rows.to_dict(orient="records"):
        report["groups"].append(
            {key: (value.item() if hasattr(value, "item") else value) for key, value in row.items()}
        )
    return report


def run_scan(data_root: str | Path) -> dict[str, Any]:
    """Run raw and industry/size-neutral fund signal diagnostics."""

    import duckdb

    root = Path(data_root).expanduser().resolve()
    fund = root / (
        "assets/tushare/a_share/fund_portfolio_features/"
        "a_share_all_fund_portfolio_features_20260821/**/*.parquet"
    )
    prices = root / (
        "assets/tushare/a_share/daily/a_share_all_20150101_20260828_daily_clean/data/*.parquet"
    )
    industries = root / (
        "assets/tushare/a_share/sw_industry_member/"
        "a_share_all_sw_industry_member_latest/data/part.parquet"
    )
    context = root / "assets/context/cn/pit/cn_context_pit_20260831/data.parquet"
    con = duckdb.connect()
    query = f"""
    WITH c0 AS (
      SELECT period_end, reconstructed,
             value - LAG(value, 5) OVER (ORDER BY period_end) AS change5
      FROM read_parquet('{context}') WHERE series_id='rates.shibor_3m'
    ), c AS (
      SELECT period_end, reconstructed,
             CASE WHEN change5 < 0 THEN 'down'
                  WHEN change5 > 0 THEN 'up' ELSE 'flat' END AS regime
      FROM c0 WHERE change5 IS NOT NULL
    ), px AS (
      SELECT ts_code, trade_date, total_mv,
             LEAD(adj_close, 20) OVER
               (PARTITION BY ts_code ORDER BY trade_date) / NULLIF(adj_close, 0) - 1 AS fwd20
      FROM read_parquet('{prices}')
      WHERE trade_date BETWEEN '20250101' AND '20260722'
        AND adj_close > 0 AND total_mv > 0
    ), f AS (
      SELECT symbol AS ts_code, CAST(trade_date AS VARCHAR) AS trade_date,
             CAST(available_date AS VARCHAR) AS available_date,
             fund_hold_mv_to_float_mv AS crowd,
             fund_hold_mv_to_float_mv_qoq_change AS addchg
      FROM read_parquet('{fund}')
      WHERE trade_date BETWEEN 20250120 AND 20260722
        AND fund_hold_mv_to_float_mv IS NOT NULL
        AND fund_hold_mv_to_float_mv_qoq_change IS NOT NULL
        AND CAST(available_date AS BIGINT) <= trade_date
    ), i AS (
      SELECT con_code AS ts_code, industry_code, in_date, out_date
      FROM read_parquet('{industries}')
    ), j AS (
      SELECT f.*, px.fwd20, px.total_mv, i.industry_code,
             c.regime, c.reconstructed,
             CASE WHEN f.trade_date < '20260101' THEN 'pre_2026' ELSE '2026' END AS sample
      FROM f JOIN px ON px.ts_code=f.ts_code AND px.trade_date=f.trade_date
      JOIN i ON i.ts_code=f.ts_code AND f.trade_date >= i.in_date
             AND (i.out_date IS NULL OR f.trade_date <= i.out_date)
      ASOF JOIN c ON strptime(f.trade_date, '%Y%m%d') >= c.period_end
    ), q AS (
      SELECT *,
             NTILE(5) OVER (PARTITION BY trade_date ORDER BY crowd) AS crowd_q,
             NTILE(5) OVER (PARTITION BY trade_date ORDER BY addchg) AS add_q,
             NTILE(5) OVER (PARTITION BY trade_date ORDER BY total_mv) AS size_q
      FROM j
    ), n AS (
      SELECT *,
             NTILE(5) OVER
               (PARTITION BY trade_date, industry_code, size_q ORDER BY crowd) AS ncrowd_q,
             NTILE(5) OVER
               (PARTITION BY trade_date, industry_code, size_q ORDER BY addchg) AS nadd_q
      FROM q
    ), z AS (
      SELECT *,
             CASE WHEN crowd_q <= 2 AND add_q >= 4
                  THEN 'low_crowd_increasing' ELSE 'other' END AS raw_signal,
             CASE WHEN ncrowd_q <= 2 AND nadd_q >= 4
                  THEN 'low_crowd_increasing' ELSE 'other' END AS neutral_signal
      FROM n
    )
    SELECT sample, regime, reconstructed, 'raw' AS test, raw_signal AS bucket,
           COUNT(*) AS n, AVG(fwd20) AS avg_fwd20
    FROM z GROUP BY 1,2,3,4,5
    UNION ALL
    SELECT sample, regime, reconstructed, 'industry_size_neutral' AS test,
           neutral_signal AS bucket, COUNT(*) AS n, AVG(fwd20) AS avg_fwd20
    FROM z GROUP BY 1,2,3,4,5
    ORDER BY 1,2,3,4,5
    """
    grouped = con.execute(query).fetchdf()
    return {
        "data_root": str(root),
        "signal": "low current fund ownership + high ownership change",
        "horizon_days": 20,
        "strict_disclosure_filter": "available_date <= trade_date",
        "reconstructed_policy": "reported_only_not_promotion_safe",
        **summarize_rows(grouped),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    payload = run_scan(args.data_root)
    Path(args.output).expanduser().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
