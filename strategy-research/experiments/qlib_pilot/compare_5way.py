"""Compare two 3-factor portfolios with CSI300, CSI800, and a PIT top800 benchmark.

The equal-weight benchmark uses the market-data platform's canonical monthly
universe. Its liquidity metric is a 60-day rolling median shifted by one day.
The 800 most liquid seasoned stocks at each rebalance become effective on the
next trading day. Missing daily rows, normally suspensions, earn zero return.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import glob
import json
from functools import reduce
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def series_from_nav(
    path: str,
    date_col: str = "trade_date",
    val_col: str = "executed_return",
) -> pd.Series:
    data = pd.read_csv(path)
    data[date_col] = pd.to_datetime(data[date_col].astype(str), format="%Y%m%d")
    data = data.sort_values(date_col)
    return data.set_index(date_col)[val_col]


def series_from_index(path: str, symbol: str) -> pd.Series:
    data = pd.read_parquet(path)
    data["trade_date"] = pd.to_datetime(data["trade_date"].astype(str), format="%Y%m%d")
    selected = data[data["symbol"] == symbol].sort_values("trade_date")
    returns = selected["pct_chg"] / 100.0
    returns.index = selected["trade_date"]
    return returns


def _read_daily_file(path: str, start: str, end: str) -> pd.DataFrame:
    columns = [
        "trade_date",
        "symbol",
        "pct_chg",
        "close",
        "pre_close",
        "listed_days",
        "is_suspended",
    ]
    data = pd.read_parquet(path, columns=columns)
    data["trade_date"] = data["trade_date"].astype(str)
    return data[(data["trade_date"] >= start) & (data["trade_date"] <= end)]


def _point_in_time_membership(
    universe: pd.DataFrame,
    daily: pd.DataFrame,
    *,
    top_n: int,
    min_listed_days: int,
) -> pd.DataFrame:
    required_universe = {"trade_date", "symbol", "liq_metric"}
    required_daily = {"trade_date", "symbol", "listed_days", "is_suspended"}
    if missing := required_universe.difference(universe.columns):
        raise ValueError(f"universe is missing columns: {sorted(missing)}")
    if missing := required_daily.difference(daily.columns):
        raise ValueError(f"daily data is missing columns: {sorted(missing)}")

    rebalance_dates = set(universe["trade_date"])
    eligibility = daily.loc[
        daily["trade_date"].isin(rebalance_dates),
        ["trade_date", "symbol", "listed_days", "is_suspended"],
    ].drop_duplicates(["trade_date", "symbol"], keep="last")
    candidates = universe.merge(
        eligibility,
        on=["trade_date", "symbol"],
        how="inner",
        validate="one_to_one",
    )
    candidates = candidates[
        candidates["listed_days"].ge(min_listed_days) & ~candidates["is_suspended"].fillna(False)
    ]
    membership = (
        candidates.sort_values(
            ["trade_date", "liq_metric", "symbol"],
            ascending=[True, False, True],
        )
        .groupby("trade_date", sort=True)
        .head(top_n)
        .rename(columns={"trade_date": "rebalance_date"})
    )
    counts = membership.groupby("rebalance_date")["symbol"].nunique()
    if counts.empty:
        raise ValueError("no eligible top800 rebalance membership was built")
    short = counts[counts < top_n]
    if not short.empty:
        sample = ", ".join(f"{date}={count}" for date, count in short.head().items())
        raise ValueError(f"fewer than {top_n} eligible symbols at rebalance: {sample}")
    return membership[["rebalance_date", "symbol", "liq_metric"]].reset_index(drop=True)


def _effective_rebalance_dates(
    trading_dates: pd.Series,
    rebalance_dates: pd.Series,
) -> pd.DataFrame:
    dates = np.array(sorted(trading_dates.astype(str).unique()))
    rebalances = np.array(sorted(rebalance_dates.astype(str).unique()))
    positions = np.searchsorted(rebalances, dates, side="left") - 1
    valid = positions >= 0
    return pd.DataFrame(
        {
            "trade_date": dates[valid],
            "rebalance_date": rebalances[positions[valid]],
        }
    )


def _validate_held_returns(held: pd.DataFrame) -> None:
    observed = held.dropna(subset=["pct_chg"])
    price_return = (observed["close"] / observed["pre_close"] - 1) * 100
    mismatch = (observed["pct_chg"] - price_return).abs()
    if not mismatch.empty and float(mismatch.max()) > 0.1:
        raise ValueError(
            "daily pct_chg disagrees with close/pre_close by more than 0.1 percentage point"
        )
    extreme = observed[observed["pct_chg"].abs() > 30.1]
    if not extreme.empty:
        sample = extreme[["trade_date", "symbol", "pct_chg"]].head().to_dict("records")
        raise ValueError(f"seasoned PIT holdings contain implausible returns: {sample}")


def series_equal_weight_top800(
    universe_path: str,
    daily_dir: str,
    start: str,
    end: str,
    *,
    top_n: int = 800,
    min_listed_days: int = 60,
    max_workers: int = 24,
) -> pd.Series:
    universe = pd.read_csv(universe_path)
    universe["trade_date"] = universe["trade_date"].astype(str)
    universe = universe[(universe["trade_date"] >= start) & (universe["trade_date"] <= end)]

    files = sorted(glob.glob(f"{daily_dir}/*.parquet"))
    if not files:
        raise FileNotFoundError(f"no daily parquet files under {daily_dir}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        parts = list(executor.map(lambda path: _read_daily_file(path, start, end), files))
    daily = pd.concat(parts, ignore_index=True)
    daily["trade_date"] = daily["trade_date"].astype(str)

    membership = _point_in_time_membership(
        universe,
        daily,
        top_n=top_n,
        min_listed_days=min_listed_days,
    )
    date_map = _effective_rebalance_dates(
        daily["trade_date"],
        membership["rebalance_date"],
    )
    expected = date_map.merge(
        membership[["rebalance_date", "symbol"]],
        on="rebalance_date",
        how="inner",
        validate="many_to_many",
    )
    observed = daily[["trade_date", "symbol", "pct_chg", "close", "pre_close"]].drop_duplicates(
        ["trade_date", "symbol"], keep="last"
    )
    held = expected.merge(
        observed,
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    _validate_held_returns(held)

    missing_return_rows = int(held["pct_chg"].isna().sum())
    held["pct_chg"] = held["pct_chg"].fillna(0.0)
    counts = held.groupby("trade_date")["symbol"].nunique()
    if not counts.eq(top_n).all():
        raise ValueError("effective top800 membership is not exactly 800 names per trading date")
    returns = held.groupby("trade_date", sort=True)["pct_chg"].mean() / 100.0
    returns.index = pd.to_datetime(returns.index, format="%Y%m%d")
    returns.attrs.update(
        {
            "universe_method": "monthly_60d_lagged_median_amount_top800",
            "membership_effective": "next_trading_day",
            "min_listed_days": min_listed_days,
            "missing_return_rows_filled_zero": missing_return_rows,
            "rebalance_dates": int(membership["rebalance_date"].nunique()),
        }
    )
    return returns.sort_index()


def full_report(returns: pd.Series, name: str) -> dict[str, Any]:
    returns = returns.dropna().sort_index()
    if returns.empty:
        raise ValueError(f"{name} has no returns")
    if returns.index.has_duplicates:
        raise ValueError(f"{name} has duplicate return dates")
    nav = (1 + returns).cumprod()
    peak = nav.cummax()
    drawdown = nav / peak - 1
    yearly = returns.groupby(returns.index.year).apply(
        lambda values: (1 + values).prod() - 1,
        include_groups=False,
    )
    monthly = returns.resample("ME").apply(lambda values: (1 + values).prod() - 1)
    last = returns.index.max()
    trailing = {
        "1week": float((1 + returns.tail(5)).prod() - 1),
        "1month": float((1 + returns.tail(21)).prod() - 1),
        "6month": float((1 + returns.tail(126)).prod() - 1),
        "YTD": float((1 + returns[returns.index.year == last.year]).prod() - 1),
        "12month": float((1 + returns.tail(252)).prod() - 1),
    }
    longest = current = 0
    for underwater in drawdown < 0:
        current = current + 1 if underwater else 0
        longest = max(longest, current)
    report: dict[str, Any] = {
        "name": name,
        "total_return": float(nav.iloc[-1] - 1),
        "annual_ret": float(nav.iloc[-1] ** (252 / len(returns)) - 1),
        "sharpe": (
            float(returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        ),
        "max_drawdown": float(drawdown.min()),
        "longest_underwater_days": int(longest),
        "yearly": {str(key): float(value) for key, value in yearly.items()},
        "monthly": {key.strftime("%Y-%m"): float(value) for key, value in monthly.items()},
        "trailing": trailing,
        "last_date": str(last.date()),
    }
    if returns.attrs:
        report["source_audit"] = dict(returns.attrs)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="/tmp/3factor_5way.json")
    parser.add_argument("--start", default="20150101")
    parser.add_argument("--end", default="20260807")
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args()

    base = "/home/richard/data/market-data-platform"
    nav_unrestricted = (
        f"{base}/runs/3factor_2015_fullperiod_20260811_130703_c050e7e1/ideal_daily_nav_daily.csv"
    )
    nav_top800 = (
        f"{base}/runs/3factor_2015_top800_fullperiod_20260811_143113_f1c21522/"
        "ideal_daily_nav_daily.csv"
    )
    index_csi300 = (
        f"{base}/assets/tushare/a_share/index_daily/"
        "a_share_all_index_daily_csi300_2015/data/part.parquet"
    )
    index_csi800 = (
        f"{base}/assets/tushare/a_share/index_daily/a_share_all_index_daily_zj800/data/part.parquet"
    )
    universe_top800 = f"{base}/assets/universe/a_share_all_full_by_date.csv"
    daily_dir = f"{base}/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data"

    series = {
        "三因子-无限制(真小盘)": series_from_nav(nav_unrestricted),
        "三因子-top800": series_from_nav(nav_top800),
        "沪深300": series_from_index(index_csi300, "000300.SH"),
        "中证800": series_from_index(index_csi800, "000906.SH"),
    }
    print("computing PIT equal-weight top800 ...")
    series["等权800-PIT"] = series_equal_weight_top800(
        universe_top800,
        daily_dir,
        args.start,
        args.end,
        max_workers=args.workers,
    )

    common_index = reduce(pd.Index.intersection, (values.index for values in series.values()))
    common_index = common_index.sort_values()
    if common_index.empty:
        raise ValueError("the five return series have no common trading dates")
    print(f"common period: {common_index.min().date()} ~ {common_index.max().date()}")
    aligned = {name: values.reindex(common_index) for name, values in series.items()}

    reports = {name: full_report(values, name) for name, values in aligned.items()}
    Path(args.out).write_text(
        json.dumps(reports, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[ok] -> {args.out}")


if __name__ == "__main__":
    main()
