"""Barra-style 15-factor long-only full-market analysis (2008-2026) + sensitivity.

Extends the existing 15-factor long-short (Q4-Q1) full-market study
(style_analysis_2008 / style-factor-market-regimes-2008-2026.md) with a
long-only, costed, tradable Top-K view.  Also runs:

- 3-factor composite rolling-window sensitivity (Phase 2, 2008+)
- 3-factor composite weight sensitivity (size/liquidity/growth)

Reuses the Phase 2 factor panel and raw pricing already produced by
long_only_style_analysis.py so no factor recomputation is needed.

Direction for each Barra factor follows the long-short study's profitable side:
factors with positive Q4-Q1 returns keep the raw direction (+1); factors with
negative long-short returns (size, momentum, beta) are flipped (-1) so the
long-only portfolio holds the side that has historically outperformed.
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

# Direction for each of the 15 Barra-style factors.  +1 keeps the raw factor_z
# (higher is the historically-good side), -1 flips (small-cap, reversal, low-beta).
FACTOR_DIRECTION = {
    "liquidity": 1.0,
    "growth": 1.0,
    "value": 1.0,
    "liquidity_flow": 1.0,
    "ps_value": 1.0,
    "dividend_yield": 1.0,
    "lowvol": 1.0,
    "earnings_yield": 1.0,
    "chip_concentration": 1.0,
    "institution_holding": 1.0,
    "quality": 1.0,
    "leverage": 1.0,
    "beta": -1.0,
    "size": -1.0,
    "momentum": -1.0,
}

WEIGHT_VARIANTS = {
    "1/1/1 (等权)": (1.0, 1.0, 1.0),
    "2/1/1 (重小盘)": (2.0, 1.0, 1.0),
    "1/0/1 (无低换手)": (1.0, 0.0, 1.0),
    "1/2/1 (重低换手)": (1.0, 2.0, 1.0),
    "1/1/2 (重成长)": (1.0, 1.0, 2.0),
    "0/1/1 (无小盘)": (0.0, 1.0, 1.0),
    "1/1/0 (无成长)": (1.0, 1.0, 0.0),
}

ROLLING_STARTS = [
    "2008-01-01", "2010-01-01", "2012-01-01",
    "2015-01-01", "2018-01-01", "2020-01-01",
]


def _weighted_composite(
    panel: pd.DataFrame, w_size: float, w_liq: float, w_growth: float,
) -> pd.Series:
    return (
        w_size * panel.get("small_cap_score", 0)
        + w_liq * panel.get("low_turnover_score", 0)
        + w_growth * panel.get("growth_score", 0)
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="/home/richard/data/market-data-platform")
    ap.add_argument("--panel", default="/tmp/longonly_p2_full/panel_p2_full.parquet")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--top-k", type=int, default=100)
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

    # ---- Task 2: rolling-window composite sensitivity ----
    print("\n[rolling] composite long-only across start dates", flush=True)
    rolling_rows = []
    for start_str in ROLLING_STARTS:
        s = pd.Timestamp(start_str)
        sub_panel = panel[panel["trade_date"] >= s].copy()
        sub_panel["composite_score"] = _weighted_composite(sub_panel, 1.0, 1.0, 1.0)
        sub_td = trade_dates_all[trade_dates_all >= s]
        series = long_only_topk_backtest(
            sub_panel, pricing, sub_td,
            score_col="composite_score", top_k=args.top_k, cost_bps=args.cost_bps,
        )
        rolling_rows.append({"start": start_str, **return_stats(series)})
        print(rolling_rows[-1], flush=True)
    pd.DataFrame(rolling_rows).to_csv(outdir / "rolling_composite.csv", index=False)

    # ---- Task 3: weight sensitivity (2008-2026) ----
    print("\n[weight] composite weight sensitivity (2008-2026)", flush=True)
    weight_rows = []
    for label, (w_size, w_liq, w_growth) in WEIGHT_VARIANTS.items():
        panel["composite_score"] = _weighted_composite(panel, w_size, w_liq, w_growth)
        series = long_only_topk_backtest(
            panel, pricing, trade_dates_all,
            score_col="composite_score", top_k=args.top_k, cost_bps=args.cost_bps,
        )
        weight_rows.append({"variant": label, "w_size": w_size, "w_liq": w_liq,
                            "w_growth": w_growth, **return_stats(series)})
        print(weight_rows[-1], flush=True)
    pd.DataFrame(weight_rows).to_csv(outdir / "weight_sensitivity.csv", index=False)

    # ---- Task 4: 15-factor long-only (2008-2026) ----
    print("\n[barra] 15-factor long-only (2008-2026)", flush=True)
    barra_rows = []
    barra_daily = {}
    for name, sign in FACTOR_DIRECTION.items():
        col = f"factor_{name}_z"
        if col not in panel.columns:
            print(f"  skip {name}: no {col}", flush=True)
            continue
        panel["dir_score"] = sign * panel[col]
        series = long_only_topk_backtest(
            panel, pricing, trade_dates_all,
            score_col="dir_score", top_k=args.top_k, cost_bps=args.cost_bps,
        )
        barra_daily[name] = series
        barra_rows.append({"factor": name, "direction": sign, **return_stats(series)})
        print(barra_rows[-1], flush=True)
    barra_df = pd.DataFrame(barra_rows)
    barra_df.to_csv(outdir / "barra_long_only_topk.csv", index=False)

    # yearly for the 15-factor long-only
    annual_rows = []
    for name, s in barra_daily.items():
        for year, r in yearly_returns(s).items():
            annual_rows.append({"factor": name, "year": year, "return": r})
    pd.DataFrame(annual_rows).to_csv(outdir / "barra_long_only_annual.csv", index=False)
    pd.DataFrame(barra_daily).to_parquet(outdir / "barra_long_only_daily.parquet")

    print("\n[done] wrote outputs to", outdir)


if __name__ == "__main__":
    main()
