"""Cost-stress comparisons for next-open-to-high daily OHLC research."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from a_share_next_open_to_high_common import build_stress_daily, hac_mean_t


def _float_or_none(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _max_drawdown(returns: pd.Series) -> float | None:
    if returns.empty:
        return None
    curve = (1.0 + returns.fillna(0.0)).cumprod()
    return _float_or_none((curve / curve.cummax() - 1.0).min())


def _benchmark_metrics(
    selected: pd.Series,
    benchmark: pd.Series,
    matched_benchmark: pd.Series,
    active: pd.Series,
) -> dict[str, Any]:
    benchmark_vol = benchmark.std(ddof=0)
    active_vol = active.std(ddof=0)
    selected_nav = (1.0 + selected).prod()
    matched_nav = (1.0 + matched_benchmark).prod()
    return {
        "benchmark_return_mean": _float_or_none(benchmark.mean()),
        "benchmark_sharpe": _float_or_none(benchmark.mean() / benchmark_vol * math.sqrt(252.0))
        if benchmark_vol > 0
        else None,
        "benchmark_hac_mean_t_5": hac_mean_t(benchmark, lags=5),
        "exposure_matched_benchmark_mean": _float_or_none(matched_benchmark.mean()),
        "active_return_mean": _float_or_none(active.mean()),
        "active_sharpe": _float_or_none(active.mean() / active_vol * math.sqrt(252.0))
        if active_vol > 0
        else None,
        "active_hac_mean_t_5": hac_mean_t(active, lags=5),
        "relative_nav_vs_exposure_matched_benchmark": _float_or_none(
            selected_nav / matched_nav - 1.0
        ),
    }


def summarize_cost_stress(
    trades: pd.DataFrame,
    stress_bps: list[float],
    daily_selection: pd.DataFrame | None = None,
    benchmark_daily: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for drag_bps in stress_bps:
        stressed = trades.copy()
        stressed["stress_return"] = stressed["gross_return"] - drag_bps / 10000.0
        daily = build_stress_daily(stressed, daily_selection)
        if benchmark_daily is not None:
            daily = daily.merge(
                benchmark_daily,
                on=["signal_date", "exit_policy"],
                how="left",
                validate="many_to_one",
            )
        for keys, group in daily.groupby(["top_k", "exit_policy"], sort=True):
            assert isinstance(keys, tuple)
            top_k, exit_policy = keys
            returns = group["portfolio_return"].fillna(0.0)
            daily_vol = returns.std(ddof=0)
            row = {
                "drag_bps": _float_or_none(drag_bps),
                "top_k": int(str(top_k)),
                "exit_policy": str(exit_policy),
                "days": len(group),
                "selected_return_mean": _float_or_none(returns.mean()),
                "selected_sharpe": _float_or_none(returns.mean() / daily_vol * math.sqrt(252.0))
                if daily_vol > 0
                else None,
                "selected_hac_mean_t_5": hac_mean_t(returns, lags=5),
                "selected_total_return": _float_or_none((1.0 + returns).prod() - 1.0),
                "selected_max_drawdown": _max_drawdown(returns),
            }
            if benchmark_daily is not None:
                benchmark_sum = (
                    group["benchmark_gross_return_sum"]
                    - drag_bps / 10000.0 * group["benchmark_executed"]
                )
                benchmark = benchmark_sum / group["benchmark_slots"]
                executed_mean = (
                    benchmark_sum / group["benchmark_executed"].replace(0, np.nan)
                ).fillna(0.0)
                matched = executed_mean * group["filled"] / group["top_k"]
                row.update(_benchmark_metrics(returns, benchmark, matched, returns - matched))
            rows.append(row)
    return pd.DataFrame(rows).sort_values(["drag_bps", "top_k", "exit_policy"])
