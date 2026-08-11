"""Five-way comparison: unrestricted 3-factor, top800 3-factor, CSI300,
CSI800 (000906), equal-weight top800. Same period 2016-2026.

All series normalized to 1.0 at the earliest common date; annual/monthly
returns, drawdown, trailing windows computed identically for each.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def series_from_nav(path: str, date_col: str = "trade_date", val_col: str = "executed_return") -> pd.Series:
    d = pd.read_csv(path)
    d[date_col] = pd.to_datetime(d[date_col].astype(str), format="%Y%m%d")
    d = d.sort_values(date_col)
    return d.set_index(date_col)[val_col]


def series_from_index(path: str, symbol: str) -> pd.Series:
    d = pd.read_parquet(path)
    d["trade_date"] = pd.to_datetime(d["trade_date"].astype(str), format="%Y%m%d")
    sub = d[d["symbol"] == symbol].sort_values("trade_date")
    ret = sub["pct_chg"] / 100.0
    ret.index = sub["trade_date"]
    return ret


def series_equal_weight_top800(univ_path: str, daily_dir: str, start: str, end: str) -> pd.Series:
    univ = pd.read_csv(univ_path)
    univ["trade_date"] = univ["trade_date"].astype(str)
    univ = univ[(univ["trade_date"] >= start) & (univ["trade_date"] <= end)]
    # daily equal-weight return per date from daily_clean
    import glob, concurrent.futures
    files = sorted(glob.glob(f"{daily_dir}/*.parquet"))
    dates = sorted(univ["trade_date"].unique())
    # build per-date top800 symbols -> merge with daily returns
    # chunked read of daily_clean for performance is heavy; use cached per-symbol returns
    rets = {}
    def read(f):
        sym = f.split("/")[-1].replace(".parquet", "")
        d = pd.read_parquet(f, columns=["trade_date", "symbol", "pct_chg"])
        return d[(d["trade_date"] >= start) & (d["trade_date"] <= end)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
        parts = list(ex.map(read, files))
    big = pd.concat(parts, ignore_index=True)
    big["trade_date"] = big["trade_date"].astype(str)
    # winsorize pct_chg to A-share daily limit (±10%) to remove extreme
    # new-listing / resumption outliers that are not tradable signals.
    big["pct_chg"] = big["pct_chg"].clip(-10, 10)
    merged = big.merge(univ, on=["trade_date", "symbol"], how="inner")
    ew = merged.groupby("trade_date")["pct_chg"].mean()
    ew.index = pd.to_datetime(ew.index, format="%Y%m%d")
    return (ew / 100.0).sort_index()


def full_report(returns: pd.Series, name: str) -> dict:
    nav = (1 + returns).cumprod()
    peak = nav.cummax()
    dd = nav / peak - 1
    yearly = returns.groupby(returns.index.year).apply(lambda s: (1 + s).prod() - 1, include_groups=False)
    monthly = returns.resample("ME").apply(lambda s: (1 + s).prod() - 1)
    last = returns.index.max()
    trailing = {
        "1week": float((1 + returns.tail(5)).prod() - 1),
        "1month": float((1 + returns.tail(21)).prod() - 1),
        "6month": float((1 + returns.tail(126)).prod() - 1),
        "YTD": float((1 + returns[returns.index.year == last.year]).prod() - 1),
        "12month": float((1 + returns.tail(252)).prod() - 1),
    }
    underwater = dd < 0
    longest = cur = 0
    for flag in underwater:
        cur = cur + 1 if flag else 0
        longest = max(longest, cur)
    return {
        "name": name,
        "total_return": float(nav.iloc[-1] - 1),
        "annual_ret": float((nav.iloc[-1]) ** (252 / len(returns)) - 1),
        "sharpe": float(returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0,
        "max_drawdown": float(dd.min()),
        "longest_underwater_days": int(longest),
        "yearly": {str(k): float(v) for k, v in yearly.items()},
        "monthly": {k.strftime("%Y-%m"): float(v) for k, v in monthly.items()},
        "trailing": trailing,
        "last_date": str(last.date()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/3factor_5way.json")
    args = ap.parse_args()

    base = "/home/richard/data/market-data-platform"
    # strategy NAVs (executed = real cost)
    nav_unrestricted = f"{base}/runs/3factor_2015_fullperiod_20260811_130703_c050e7e1/ideal_daily_nav_daily.csv"
    nav_top800 = f"{base}/runs/3factor_2015_top800_fullperiod_20260811_143113_f1c21522/ideal_daily_nav_daily.csv"
    idx_csi300 = f"{base}/assets/tushare/a_share/index_daily/a_share_all_index_daily_csi300_2015/data/part.parquet"
    idx_csi800 = f"{base}/assets/tushare/a_share/index_daily/a_share_all_index_daily_zj800/data/part.parquet"
    univ_top800 = f"{base}/assets/universe/top800_2015_by_date.csv"
    daily_dir = f"{base}/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data"

    series = {
        "三因子-无限制(真小盘)": series_from_nav(nav_unrestricted),
        "三因子-top800": series_from_nav(nav_top800),
        "沪深300": series_from_index(idx_csi300, "000300.SH"),
        "中证800": series_from_index(idx_csi800, "000906.SH"),
    }
    print("computing equal-weight top800 ...")
    series["等权800"] = series_equal_weight_top800(univ_top800, daily_dir, "20150101", "20260807")

    # align to common period
    common_start = max(s.index.min() for s in series.values())
    common_end = min(s.index.max() for s in series.values())
    print(f"common period: {common_start.date()} ~ {common_end.date()}")
    aligned = {k: s.loc[common_start:common_end] for k, s in series.items()}

    reports = {name: full_report(ser, name) for name, ser in aligned.items()}
    import json
    Path(args.out).write_text(json.dumps(reports, indent=2, ensure_ascii=False))
    print(f"[ok] -> {args.out}")


if __name__ == "__main__":
    main()
