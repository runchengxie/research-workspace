"""Factor portfolio backtest — quintile long-short, summary, correlations, yearly breakdown."""

from __future__ import annotations

import numpy as np
import pandas as pd

FACTOR_NAMES = [
    "size",
    "value",
    "momentum",
    "quality",
    "lowvol",
    "growth",
    "leverage",
    "beta",
    "liquidity",
]


def available_factor_names(factors_df: pd.DataFrame) -> list[str]:
    """Return factors whose standardized columns exist in the factor frame."""
    names = []
    for name in FACTOR_NAMES:
        column = f"factor_{name}_z"
        if column in factors_df.columns and factors_df[column].notna().any():
            names.append(name)
    return names


def get_rebalance_dates(dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Monthly rebalance: last trading day of each month."""
    df = pd.DataFrame({"date": dates})
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    return pd.DatetimeIndex(df.groupby(["year", "month"])["date"].max().sort_values())


def _daily_return_matrix(daily: pd.DataFrame) -> pd.DataFrame:
    ret_df = daily[["trade_date", "symbol", "pct_chg"]].dropna().copy()
    ret_df["trade_date"] = pd.to_datetime(ret_df["trade_date"]).dt.normalize()
    ret_df["pct_chg"] = ret_df["pct_chg"] / 100.0
    returns = ret_df.pivot_table(
        index="trade_date",
        columns="symbol",
        values="pct_chg",
        aggfunc="mean",
    )
    returns.index = pd.DatetimeIndex(returns.index)
    return returns.sort_index()


def build_factor_returns(
    factors_df: pd.DataFrame,
    daily: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
    n_quantiles: int = 5,
) -> dict:
    """For each factor: quintile long-short monthly rebalance."""
    factor_names = available_factor_names(factors_df)

    daily_returns = _daily_return_matrix(daily)
    rd_list = sorted(rebalance_dates)

    results = {}
    for fname in factor_names:
        fcol = f"factor_{fname}_z"
        print(f"[backtest] {fname} ...", flush=True)
        long_parts: list[pd.Series] = []
        short_parts: list[pd.Series] = []
        ls_parts: list[pd.Series] = []

        for i, rd in enumerate(rd_list):
            if i == len(rd_list) - 1:
                break
            next_rd = rd_list[i + 1]

            rd = pd.Timestamp(rd).normalize()
            next_rd = pd.Timestamp(next_rd).normalize()
            rd_data = factors_df[factors_df["trade_date"] == rd].dropna(subset=[fcol])
            if len(rd_data) < n_quantiles * 10:
                continue

            rd_data = rd_data.sort_values(fcol)
            rd_data["quantile"] = pd.qcut(
                rd_data[fcol], n_quantiles, labels=False, duplicates="drop"
            )
            if rd_data["quantile"].nunique() < n_quantiles:
                continue

            top_syms = rd_data[rd_data["quantile"] == n_quantiles - 1]["symbol"].tolist()
            bot_syms = rd_data[rd_data["quantile"] == 0]["symbol"].tolist()

            period_returns = daily_returns.loc[rd:next_rd]
            period_returns = period_returns[period_returns.index > rd]
            if period_returns.empty:
                continue

            top_r = period_returns.reindex(columns=top_syms).mean(axis=1)
            bot_r = period_returns.reindex(columns=bot_syms).mean(axis=1)
            paired = pd.concat({"long": top_r, "short": bot_r}, axis=1).dropna()
            if paired.empty:
                continue

            long_parts.append(paired["long"])
            short_parts.append(paired["short"])
            ls_parts.append(paired["long"] - paired["short"])

        if ls_parts:
            long_series = pd.concat(long_parts).sort_index()
            short_series = pd.concat(short_parts).sort_index()
            ls_series = pd.concat(ls_parts).sort_index()
        else:
            empty_index = pd.DatetimeIndex([], name="trade_date")
            long_series = pd.Series(dtype=float, index=empty_index)
            short_series = pd.Series(dtype=float, index=empty_index)
            ls_series = pd.Series(dtype=float, index=empty_index)
        ls_series.name = fname
        results[fname] = {
            "long_short": ls_series,
            "long": long_series,
            "short": short_series,
        }

    return results


def _max_drawdown(returns: pd.Series) -> float:
    cumulative = (1 + returns).cumprod()
    drawdown = (cumulative - cumulative.cummax()) / cumulative.cummax()
    return float(drawdown.min())


def compute_summary(factor_results: dict, trading_days: int = 252) -> pd.DataFrame:
    rows = []
    for name, res in factor_results.items():
        ls = res["long_short"].dropna()
        if len(ls) < 20:
            continue
        dm = ls.mean()
        annual_ret = (1 + dm) ** trading_days - 1
        annual_vol = ls.std() * np.sqrt(trading_days)
        sharpe = dm / ls.std() * np.sqrt(trading_days) if ls.std() > 0 else 0
        hit_rate = (ls > 0).mean()
        n_years = (ls.index.max() - ls.index.min()).days / 365.25
        rows.append(
            {
                "factor": name,
                "days": len(ls),
                "years": round(n_years, 1),
                "annual_ret": round(annual_ret * 100, 2),
                "annual_vol": round(annual_vol * 100, 2),
                "sharpe": round(sharpe, 2),
                "max_drawdown": round(_max_drawdown(ls) * 100, 2),
                "hit_rate": round(hit_rate * 100, 1),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "factor",
                "days",
                "years",
                "annual_ret",
                "annual_vol",
                "sharpe",
                "max_drawdown",
                "hit_rate",
            ]
        )
    return pd.DataFrame(rows).sort_values("sharpe", ascending=False)


def compute_factor_correlations(factor_results: dict) -> pd.DataFrame:
    series = {}
    for name, res in factor_results.items():
        s = res["long_short"].dropna()
        if len(s) > 20:
            series[name] = s
    return pd.DataFrame(series).corr()


def compute_yearly_breakdown(factor_results: dict) -> pd.DataFrame:
    rows = []
    for name, res in factor_results.items():
        s = res["long_short"].dropna()
        for year_end, group in s.resample("YE"):
            if len(group) < 50:
                continue
            annual_ret = (1 + group).prod() - 1
            ann_vol = group.std() * np.sqrt(252)
            sharpe = group.mean() / group.std() * np.sqrt(252) if group.std() > 0 else 0
            rows.append(
                {
                    "year": year_end.year,
                    "factor": name,
                    "days": len(group),
                    "annual_ret": round(annual_ret * 100, 2),
                    "annual_vol": round(ann_vol * 100, 2),
                    "sharpe": round(sharpe, 2),
                    "max_drawdown": round(_max_drawdown(group) * 100, 2),
                }
            )
    if not rows:
        return pd.DataFrame(
            columns=["year", "factor", "days", "annual_ret", "annual_vol", "sharpe", "max_drawdown"]
        )
    return pd.DataFrame(rows).sort_values(["year", "factor"])
