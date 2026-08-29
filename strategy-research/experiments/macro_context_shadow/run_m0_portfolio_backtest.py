"""Run the strict-availability M0 fund-holder-count portfolio shadow."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def summarize_portfolio(daily: Any, *, turnover_bps: float) -> dict[str, Any]:
    """Summarize daily gross/net returns without hiding empty samples."""

    if daily.empty:
        return {"days": 0, "turnover_bps": turnover_bps, "gross_ann": None, "net_ann": None}
    gross = daily["gross_return"]
    net = gross - daily["turnover"] * turnover_bps / 10_000.0
    periods = len(daily)
    result = {
        "days": periods,
        "turnover_bps": turnover_bps,
        "mean_daily_turnover": float(daily["turnover"].mean()),
        "gross_ann": float((1.0 + gross).prod() ** (252.0 / periods) - 1.0),
        "net_ann": float((1.0 + net).prod() ** (252.0 / periods) - 1.0),
        "net_max_drawdown": _max_drawdown(net),
    }
    if "benchmark_return" in daily:
        benchmark = daily["benchmark_return"].fillna(0.0)
        result["benchmark_total"] = float((1.0 + benchmark).prod() - 1.0)
        result["active_total_after_cost"] = float(
            (1.0 + net).prod() / (1.0 + benchmark).prod() - 1.0
        )
        active = net - benchmark
        result["active_hac_t_20"] = _hac_mean_t(active.to_numpy(), lags=20)
        result["active_hit_rate"] = float((active > 0.0).mean())
    if "selected_adv_cny" in daily:
        capacity = {}
        for participation in (0.01, 0.03, 0.05):
            values = (
                daily["selected_adv_cny"]
                * participation
                / daily["turnover"].replace(0, float("nan"))
            )
            capacity[str(int(participation * 100)) + "pct"] = {
                "median_cny": float(values.median()),
                "p10_cny": float(values.quantile(0.10)),
            }
        result["capacity_cny_by_participation"] = capacity
    return result


def _max_drawdown(returns: Any) -> float:
    curve = (1.0 + returns).cumprod()
    return float((curve / curve.cummax() - 1.0).min())


def _hac_mean_t(values: Any, *, lags: int) -> float | None:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return None
    mean = float(values.mean())
    centered = values - mean
    max_lag = min(lags, len(values) - 1)
    variance = float(np.mean(centered * centered))
    for lag in range(1, max_lag + 1):
        covariance = float(np.mean(centered[lag:] * centered[:-lag]))
        variance += 2.0 * (1.0 - lag / (max_lag + 1.0)) * covariance
    if variance <= 0.0:
        return None
    return float(mean / math.sqrt(variance / len(values)))


def run_backtest(data_root: str | Path, *, turnover_bps: float = 30.0) -> dict[str, Any]:
    """Backtest M0 and M3 using the latest disclosed state and daily weights."""

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
      SELECT ts_code, trade_date, adj_close, amount,
             LEAD(adj_close) OVER (PARTITION BY ts_code ORDER BY trade_date)
               / NULLIF(adj_close, 0) - 1 AS fwd1
      FROM read_parquet('{prices}')
      WHERE trade_date BETWEEN '20250101' AND '20260722' AND adj_close > 0
    ), events AS (
      SELECT symbol AS ts_code, CAST(trade_date AS VARCHAR) AS event_date,
             fund_count_holding_stock_qoq_change AS holder_change,
             fund_hold_mv_to_float_mv_qoq_change AS ownership_change
      FROM read_parquet('{features}')
      WHERE trade_date BETWEEN 20250120 AND 20260722
        AND fund_count_holding_stock_qoq_change IS NOT NULL
        AND fund_hold_mv_to_float_mv_qoq_change IS NOT NULL
        AND CAST(available_date AS BIGINT) <= trade_date
    ), known AS (
      SELECT px.trade_date, px.ts_code, px.amount, px.fwd1,
             events.holder_change, events.ownership_change
      FROM px ASOF JOIN events
        ON px.ts_code = events.ts_code AND px.trade_date >= events.event_date
    ), ranked AS (
      SELECT *,
             NTILE(5) OVER (PARTITION BY trade_date ORDER BY holder_change) AS holder_q,
             NTILE(5) OVER (PARTITION BY trade_date ORDER BY ownership_change) AS ownership_q
      FROM known WHERE holder_change IS NOT NULL AND fwd1 IS NOT NULL
    )
    SELECT 'M0' AS model, trade_date, ts_code, amount, fwd1 AS next_return
    FROM ranked WHERE holder_q = 5
    UNION ALL
    SELECT 'M3' AS model, trade_date, ts_code, amount, fwd1 AS next_return
    FROM ranked WHERE holder_q = 5 AND ownership_q = 5
    ORDER BY model, trade_date, ts_code
    """
    selected = duckdb.connect().execute(query).fetchdf()
    if selected.empty:
        return {"data_root": str(root), "model": "M0", "periods": {}}
    selected["trade_date"] = pd.to_datetime(selected["trade_date"])
    benchmark_query = f"""
    WITH prices AS (
      SELECT trade_date,
             LEAD(adj_close) OVER (PARTITION BY ts_code ORDER BY trade_date)
               / NULLIF(adj_close, 0) - 1 AS next_return
      FROM read_parquet('{prices}')
      WHERE trade_date BETWEEN '20250101' AND '20260722' AND adj_close > 0
    )
    SELECT trade_date, AVG(next_return) AS benchmark_return
    FROM prices WHERE next_return IS NOT NULL GROUP BY trade_date
    """
    benchmark = duckdb.connect().execute(benchmark_query).fetchdf()
    benchmark["trade_date"] = pd.to_datetime(benchmark["trade_date"])
    periods: dict[str, Any] = {}
    for model, model_frame in selected.groupby("model", sort=True):
        selected_sets = {
            date: set(group["ts_code"])
            for date, group in model_frame.groupby("trade_date", sort=True)
        }
        daily = (
            model_frame.groupby("trade_date")["next_return"]
            .mean()
            .rename("gross_return")
            .to_frame()
        )
        previous: set[str] = set()
        turnovers: list[tuple[Any, float]] = []
        for date, current in selected_sets.items():
            turnover = 1.0 - len(current & previous) / max(len(current), len(previous), 1)
            turnovers.append((date, turnover))
            previous = current
        daily["turnover"] = pd.Series(dict(turnovers))
        daily["benchmark_return"] = benchmark.set_index("trade_date")["benchmark_return"].reindex(
            daily.index
        )
        daily["selected_adv_cny"] = model_frame.groupby("trade_date")["amount"].sum() * 1000.0
        periods[model] = {
            str(year): summarize_portfolio(group, turnover_bps=turnover_bps)
            for year, group in daily.groupby(daily.index.year)
        }
    return {
        "data_root": str(root),
        "models": {
            "M0": "holder_count_change_top_quintile",
            "M3": "holder_count_change_and_ownership_change_top_quintile",
        },
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
