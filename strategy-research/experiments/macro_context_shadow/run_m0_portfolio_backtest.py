"""Run the strict-availability M0 fund-holder-count portfolio shadow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def summarize_portfolio(daily: Any, *, turnover_bps: float) -> dict[str, Any]:
    """Summarize daily gross/net returns without hiding empty samples."""

    if daily.empty:
        return {"days": 0, "turnover_bps": turnover_bps, "gross_ann": None, "net_ann": None}
    gross = daily["gross_return"]
    net = gross - daily["turnover"] * turnover_bps / 10_000.0
    periods = len(daily)
    return {
        "days": periods,
        "turnover_bps": turnover_bps,
        "mean_daily_turnover": float(daily["turnover"].mean()),
        "gross_ann": float((1.0 + gross).prod() ** (252.0 / periods) - 1.0),
        "net_ann": float((1.0 + net).prod() ** (252.0 / periods) - 1.0),
    }


def run_backtest(data_root: str | Path, *, turnover_bps: float = 30.0) -> dict[str, Any]:
    """Backtest M0 using the latest disclosed state and daily equal weights."""

    import duckdb
    import pandas as pd

    root = Path(data_root).expanduser().resolve()
    prices = root / (
        "assets/tushare/a_share/daily/a_share_all_20150101_20260828_daily_clean/data/*.parquet"
    )
    features = root / (
        "assets/tushare/a_share/fund_portfolio_features/"
        "a_share_all_fund_portfolio_features_20260821/**/*.parquet"
    )
    query = f"""
    WITH px AS (
      SELECT ts_code, trade_date, adj_close,
             LEAD(adj_close) OVER (PARTITION BY ts_code ORDER BY trade_date)
               / NULLIF(adj_close, 0) - 1 AS fwd1
      FROM read_parquet('{prices}')
      WHERE trade_date BETWEEN '20250101' AND '20260722' AND adj_close > 0
    ), events AS (
      SELECT symbol AS ts_code, CAST(trade_date AS VARCHAR) AS event_date,
             fund_count_holding_stock_qoq_change AS holder_change
      FROM read_parquet('{features}')
      WHERE trade_date BETWEEN 20250120 AND 20260722
        AND fund_count_holding_stock_qoq_change IS NOT NULL
        AND CAST(available_date AS BIGINT) <= trade_date
    ), known AS (
      SELECT px.trade_date, px.ts_code, px.fwd1, events.holder_change
      FROM px ASOF JOIN events
        ON px.ts_code = events.ts_code AND px.trade_date >= events.event_date
    ), ranked AS (
      SELECT *, NTILE(5) OVER (PARTITION BY trade_date ORDER BY holder_change) AS holder_q
      FROM known WHERE holder_change IS NOT NULL AND fwd1 IS NOT NULL
    )
    SELECT trade_date, ts_code, fwd1 AS next_return
    FROM ranked WHERE holder_q = 5
    ORDER BY trade_date, ts_code
    """
    selected = duckdb.connect().execute(query).fetchdf()
    if selected.empty:
        return {"data_root": str(root), "model": "M0", "periods": {}}
    selected["trade_date"] = pd.to_datetime(selected["trade_date"])
    selected_sets = {
        date: set(group["ts_code"]) for date, group in selected.groupby("trade_date", sort=True)
    }
    daily = selected.groupby("trade_date")["next_return"].mean().rename("gross_return").to_frame()
    previous: set[str] = set()
    turnovers: list[tuple[Any, float]] = []
    for date, current in selected_sets.items():
        turnover = 1.0 - len(current & previous) / max(len(current), len(previous), 1)
        turnovers.append((date, turnover))
        previous = current
    daily["turnover"] = pd.Series(dict(turnovers))
    periods = {
        str(year): summarize_portfolio(group, turnover_bps=turnover_bps)
        for year, group in daily.groupby(daily.index.year)
    }
    return {
        "data_root": str(root),
        "model": "M0_holder_count_change_top_quintile",
        "strict_disclosure_filter": "available_date <= trade_date",
        "portfolio_rule": "latest_known_state_equal_weight_top_quintile",
        "periods": periods,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--turnover-bps", type=float, default=30.0)
    args = parser.parse_args(argv)
    payload = run_backtest(args.data_root, turnover_bps=args.turnover_bps)
    Path(args.output).expanduser().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
