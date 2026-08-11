"""3-factor strategy performance analysis.

Uses the daily executed NAV (real cost) from the full-market (true
small-cap) backtest run, plus CSI300 benchmark, to compute:
- annual / quarterly / monthly return heatmaps
- max drawdown and max underwater (drawdown duration)
- trailing returns: 1 week / 1 month / 6 months / YTD / 12 months
  as of the last available date
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def max_drawdown(returns: pd.Series) -> dict:
    nav = (1 + returns).cumprod()
    peak = nav.cummax()
    dd = nav / peak - 1
    max_dd = dd.min()
    # underwater duration: longest run of consecutive below-peak days
    underwater = dd < 0
    longest = 0
    cur = 0
    for flag in underwater:
        cur = cur + 1 if flag else 0
        longest = max(longest, cur)
    # max underwater from the max-drawdown trough back to recovery
    return {
        "max_drawdown": float(max_dd),
        "max_drawdown_date": str(dd.idxmin()),
        "longest_underwater_days": int(longest),
    }


def trailing_returns(returns: pd.Series) -> dict:
    last = returns.index.max()
    out: dict[str, float] = {}
    def cum(s: pd.Series) -> float:
        return float((1 + s).prod() - 1)
    out["1week"] = cum(returns.tail(5))
    out["1month"] = cum(returns.tail(21))
    out["6month"] = cum(returns.tail(126))
    out["YTD"] = cum(returns[returns.index.year == last.year])
    out["12month"] = cum(returns.tail(252))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nav", default="/home/richard/data/market-data-platform/runs/3factor_fullmarket_20260810_194649_2892b32d/ideal_daily_nav_daily.csv")
    ap.add_argument("--benchmark", default="/home/richard/data/market-data-platform/assets/benchmark/csi300_daily_return.parquet")
    ap.add_argument("--out", default="/tmp/3factor_perf.json")
    args = ap.parse_args()

    nav = pd.read_csv(args.nav)
    nav["trade_date"] = pd.to_datetime(nav["trade_date"].astype(str), format="%Y%m%d")
    nav = nav.sort_values("trade_date").reset_index(drop=True)
    ret = nav.set_index("trade_date")["executed_return"]
    print(f"[nav] {len(ret)} days, {ret.index.min().date()} ~ {ret.index.max().date()}")

    bench = pd.read_parquet(args.benchmark)
    bench["trade_date"] = pd.to_datetime(bench["trade_date"].astype(str), format="%Y%m%d")
    bench = bench.sort_values("trade_date").reset_index(drop=True)
    bench_ret = bench.set_index("trade_date")["return"]
    # align to strategy dates
    common = ret.index.intersection(bench_ret.index)
    br = bench_ret.loc[common]

    print("\n=== 年度收益 ===")
    yearly = ret.groupby(ret.index.year).apply(lambda s: (1 + s).prod() - 1, include_groups=False)
    bench_yearly = br.groupby(br.index.year).apply(lambda s: (1 + s).prod() - 1, include_groups=False)
    for y in yearly.index:
        b = bench_yearly.get(y, np.nan)
        print(f"  {y}: 策略 {yearly[y]*100:+.1f}%  CSI300 {b*100:+.1f}%")

    print("\n=== 季度收益（策略） ===")
    q = ret.resample("QE").apply(lambda s: (1 + s).prod() - 1)
    qm = q.groupby([q.index.year, q.index.quarter]).mean()
    for (y, qq), v in qm.items():
        print(f"  {y}Q{qq}: {v*100:+.1f}%")

    print("\n=== 月度收益（策略） ===")
    m = ret.resample("ME").apply(lambda s: (1 + s).prod() - 1)
    for dt, v in m.items():
        print(f"  {dt.strftime('%Y-%m')}: {v*100:+.1f}%")

    print("\n=== 回撤分析 ===")
    dd = max_drawdown(ret)
    print(f"  最大回撤: {dd['max_drawdown']*100:.1f}%（{dd['max_drawdown_date']}）")
    print(f"  最长水下时间: {dd['longest_underwater_days']} 个交易日")

    print("\n=== 滚动窗口收益（截至 %s）===" % ret.index.max().date())
    tr = trailing_returns(ret)
    print(f"  近 1 周: {tr['1week']*100:+.2f}%")
    print(f"  近 1 月: {tr['1month']*100:+.2f}%")
    print(f"  近 6 月: {tr['6month']*100:+.2f}%")
    print(f"  今年至今 (YTD): {tr['YTD']*100:+.2f}%")
    print(f"  近 12 月: {tr['12month']*100:+.2f}%")

    out = {
        "period": f"{ret.index.min().date()} ~ {ret.index.max().date()}",
        "yearly": {str(k): float(v) for k, v in yearly.items()},
        "quarterly": {f"{y}Q{q}": float(v) for (y, q), v in qm.items()},
        "monthly": {k.strftime("%Y-%m"): float(v) for k, v in m.items()},
        "drawdown": dd,
        "trailing": tr,
        "last_date": str(ret.index.max().date()),
    }
    Path(args.out).write_text(__import__("json").dumps(out, indent=2, ensure_ascii=False))
    print(f"\n[ok] -> {args.out}")


if __name__ == "__main__":
    main()
