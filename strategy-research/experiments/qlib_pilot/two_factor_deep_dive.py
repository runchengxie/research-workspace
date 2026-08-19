"""Deep-dive on the small-cap + low-turnover (no growth) long-only combination.

Follows the finding from barra_long_only_analysis.py that dropping growth (the
weak long-only factor) maximises the composite Sharpe.  This script:

1. Top-K sensitivity (30 / 50 / 100 / 200) for the two-factor composite.
2. Rolling-window robustness (2008 / 2010 / 2012 / 2015 / 2018 / 2020).
3. Yearly breakdown vs an equal-weight full-market benchmark built from the
   same eligible universe, plus CSI300 where index data covers the window.

Reuses the Phase 2 factor panel and raw pricing produced by
long_only_style_analysis.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from long_only_style_analysis import (
    load_pricing,
    long_only_topk_backtest,
    return_stats,
    yearly_returns,
)

from style_factors.workflow import load_data

TOP_K_VARIANTS = [30, 50, 100, 200]
ROLLING_STARTS = [
    "2008-01-01", "2010-01-01", "2012-01-01",
    "2015-01-01", "2018-01-01", "2020-01-01",
]


def _two_factor_score(panel: pd.DataFrame) -> pd.Series:
    return panel.get("small_cap_score", 0) + panel.get("low_turnover_score", 0)


def _equal_weight_benchmark(panel: pd.DataFrame, pricing: pd.DataFrame,
                            trade_dates: pd.DatetimeIndex,
                            cost_bps: float) -> pd.Series:
    """Monthly equal-weight long-only benchmark of all eligible names."""
    panel = panel.copy()
    panel["_bench"] = 1.0
    return long_only_topk_backtest(
        panel, pricing, trade_dates,
        score_col="_bench", top_k=10_000_000, cost_bps=cost_bps,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="/home/richard/data/market-data-platform")
    ap.add_argument("--panel", default="/tmp/longonly_p2_full/panel_p2_full.parquet")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--cost-bps", type=float, default=30.0)
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    data_root = Path(args.data_root)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    end = pd.Timestamp("2026-08-18")

    print("[load] panel", flush=True)
    panel = pd.read_parquet(args.panel)
    panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    print(f"[panel] {len(panel)} rows, {panel['trade_date'].nunique()} dates", flush=True)

    print("[load] daily + pricing", flush=True)
    daily, _ = load_data(data_root, start_date="2008-01-01", basics_rebalance_only=False)
    trade_dates = pd.DatetimeIndex(sorted(daily["trade_date"].unique()))
    trade_dates = trade_dates[trade_dates <= end]
    symbols = set(panel["symbol"].unique())
    pricing = load_pricing(data_root, symbols, pd.Timestamp("2008-01-01"), end,
                           workers=args.workers, source="raw")
    print(f"[pricing] {len(pricing)} rows", flush=True)
    trade_dates_all = trade_dates

    panel["two_factor_score"] = _two_factor_score(panel)

    # ---- 1. Top-K sensitivity (2008-2026) ----
    print("\n[topk] two-factor Top-K sensitivity (2008-2026)", flush=True)
    topk_rows = []
    topk_series = {}
    for k in TOP_K_VARIANTS:
        series = long_only_topk_backtest(
            panel, pricing, trade_dates_all,
            score_col="two_factor_score", top_k=k, cost_bps=args.cost_bps,
        )
        topk_series[k] = series
        topk_rows.append({"top_k": k, **return_stats(series)})
        print(topk_rows[-1], flush=True)
    pd.DataFrame(topk_rows).to_csv(outdir / "topk_sensitivity.csv", index=False)

    # ---- 2. Rolling-window robustness (Top-100) ----
    print("\n[rolling] two-factor rolling-window (Top-100)", flush=True)
    rolling_rows = []
    for start_str in ROLLING_STARTS:
        s = pd.Timestamp(start_str)
        sub_panel = panel[panel["trade_date"] >= s].copy()
        sub_td = trade_dates_all[trade_dates_all >= s]
        series = long_only_topk_backtest(
            sub_panel, pricing, sub_td,
            score_col="two_factor_score", top_k=100, cost_bps=args.cost_bps,
        )
        rolling_rows.append({"start": start_str, **return_stats(series)})
        print(rolling_rows[-1], flush=True)
    pd.DataFrame(rolling_rows).to_csv(outdir / "rolling_two_factor.csv", index=False)

    # ---- 3. Yearly + benchmark (Top-100) ----
    print("\n[benchmark] two-factor (Top-100) vs equal-weight universe (2008-2026)", flush=True)
    twof = long_only_topk_backtest(
        panel, pricing, trade_dates_all,
        score_col="two_factor_score", top_k=100, cost_bps=args.cost_bps,
    )
    bench = _equal_weight_benchmark(panel, pricing, trade_dates_all, args.cost_bps)

    yearly = []
    for label, s in [("two_factor_top100", twof), ("equal_weight_universe", bench)]:
        for year, r in yearly_returns(s).items():
            yearly.append({"series": label, "year": year, "return": r})
    pd.DataFrame(yearly).to_csv(outdir / "yearly_vs_benchmark.csv", index=False)

    summary = {
        "two_factor_top100": return_stats(twof),
        "equal_weight_universe": return_stats(bench),
        "excess": {
            "annual_return": twof.mean() * 252 - bench.mean() * 252,
            "sharpe": return_stats(twof)["sharpe"] - return_stats(bench)["sharpe"],
        },
    }
    print(json_dumps(summary))

    pd.DataFrame({
        "two_factor_top100": twof,
        "equal_weight_universe": bench,
    }).to_parquet(outdir / "two_factor_vs_benchmark_daily.parquet")

    print("\n[done] wrote outputs to", outdir)


def json_dumps(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
