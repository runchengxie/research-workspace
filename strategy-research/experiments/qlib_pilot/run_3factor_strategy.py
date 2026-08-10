"""Three-factor composite strategy: small-cap + low-turnover + growth.

Reuses style_factors loaders and compute_factors, then builds a monthly
equal-weight top-K portfolio ranked by the composite score:

    score = -z(factor_size) + z(factor_liquidity) + z(factor_growth)

where factor_size = log(total_mv) (large-cap positive, so negate for
small-cap), factor_liquidity = -turnover (low turnover positive),
factor_growth = avg(yoy net profit, yoy revenue).

This is the explicit-factor counterpart to the top800 ML strategy, testing
whether the three strongest historical factors (small-cap, low-turnover,
growth) form a competitive portfolio.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from style_factors.factor_calc import compute_factors
from style_factors.workflow import (
    load_cashflow,
    load_data,
    load_fina_indicator,
    load_holder_structure,
    load_moneyflow_ths,
    load_sw_industry_membership,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="/home/richard/data/market-data-platform")
    ap.add_argument("--start-date", default="2019-01-01")
    ap.add_argument("--top-k", type=int, default=30)
    ap.add_argument("--cost-bps", type=float, default=10.0,
                    help="One-way transaction cost in bps for realized turnover.")
    ap.add_argument("--w-size", type=float, default=1.0, help="Weight on small-cap (negative size) z.")
    ap.add_argument("--w-liquidity", type=float, default=1.0, help="Weight on low-turnover z.")
    ap.add_argument("--w-growth", type=float, default=1.0, help="Weight on growth z.")
    ap.add_argument("--out", default="/tmp/3factor_result.json")
    args = ap.parse_args()

    daily, basics = load_data(Path(args.data_root), start_date=args.start_date)
    all_dates = pd.DatetimeIndex(sorted(daily["trade_date"].unique()))
    rebalance_dates = (
        pd.Series(all_dates)
        .groupby([all_dates.year, all_dates.month])
        .last()
        .sort_index()
        .to_numpy()
    )
    fina = load_fina_indicator(Path(args.data_root))
    cashflow = load_cashflow(Path(args.data_root))
    moneyflow = load_moneyflow_ths(Path(args.data_root), start_date=args.start_date)
    holder = load_holder_structure(Path(args.data_root), start_date=args.start_date)
    sw = load_sw_industry_membership(Path(args.data_root))
    basics_extra = (
        basics.loc[
            basics["trade_date"].isin(rebalance_dates),
            ["trade_date", "symbol", "dv_ttm", "ps_ttm"],
        ].copy()
        if {"dv_ttm", "ps_ttm"} <= set(basics.columns)
        else pd.DataFrame()
    )
    aux = {
        "moneyflow_ths": moneyflow if not moneyflow.empty else None,
        "holder_structure": holder if not holder.empty else None,
        "daily_basic_extra": basics_extra if not basics_extra.empty else None,
    }
    factors = compute_factors(
        daily,
        basics,
        fina if not fina.empty else None,
        cashflow if not cashflow.empty else None,
        aux=aux,
        sw_membership=sw if not sw.empty else None,
        rebalance_dates=rebalance_dates,
    )
    print(f"[factors] {len(factors)} rows, dates {factors['trade_date'].min()} ~ {factors['trade_date'].max()}")

    rebalance_ts = pd.DatetimeIndex(rebalance_dates)
    rebalance_set = set(rebalance_ts)
    sel = factors[factors["trade_date"].isin(rebalance_set)].copy()
    print(f"[rebalance] {len(sel)} rows on {len(rebalance_ts)} rebalance dates")

    for col in ("factor_size", "factor_liquidity", "factor_growth"):
        sel[col] = pd.to_numeric(sel[col], errors="coerce")

    def zscore(s: pd.Series) -> pd.Series:
        return (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) > 0 else s * 0

    sel["z_size"] = sel.groupby("trade_date")["factor_size"].transform(zscore)
    sel["z_liquidity"] = sel.groupby("trade_date")["factor_liquidity"].transform(zscore)
    sel["z_growth"] = sel.groupby("trade_date")["factor_growth"].transform(zscore)
    sel["score"] = (
        -args.w_size * sel["z_size"]
        + args.w_liquidity * sel["z_liquidity"]
        + args.w_growth * sel["z_growth"]
    )
    sel = sel[sel["score"].notna()].copy()

    daily_ret = daily[["trade_date", "symbol", "pct_chg"]].copy()
    daily_ret["trade_date"] = pd.to_datetime(daily_ret["trade_date"])
    daily_ret["pct_chg"] = pd.to_numeric(daily_ret["pct_chg"], errors="coerce") / 100.0

    results = []
    sorted_reb = sorted(rebalance_ts)
    prev_holdings: set[str] = set()
    cost_per_turn = args.cost_bps / 1e4
    for i, reb_date in enumerate(sorted_reb):
        day_rows = sel[sel["trade_date"] == reb_date].sort_values("score", ascending=False)
        top = day_rows.head(args.top_k)["symbol"].tolist()
        if not top:
            continue
        top_set = set(top)
        # one-way turnover: sold names + new names, each ~1/top_k of portfolio
        if prev_holdings:
            turnover = len(top_set - prev_holdings) + len(prev_holdings - top_set)
            turnover_frac = turnover / (2 * args.top_k)
        else:
            turnover_frac = 1.0
        prev_holdings = top_set
        if i + 1 < len(sorted_reb):
            hold_end = sorted_reb[i + 1]
        else:
            hold_end = daily_ret["trade_date"].max()
        window = daily_ret[(daily_ret["trade_date"] > reb_date) & (daily_ret["trade_date"] <= hold_end)]
        held = window[window["symbol"].isin(top)]
        if held.empty:
            continue
        daily_ret_series = held.groupby("trade_date")["pct_chg"].mean()
        cum = (1 + daily_ret_series).prod() - 1
        cost = turnover_frac * 2 * cost_per_turn
        cum_net = (1 + cum) * (1 - cost) - 1
        results.append({"rebalance": reb_date.date().isoformat(), "period_return": float(cum_net), "gross_return": float(cum), "turnover": round(turnover_frac, 4), "n_held": len(top)})

    if not results:
        print("No periods built.")
        return

    df = pd.DataFrame(results)
    total = (1 + df["period_return"]).prod() - 1
    mean_daily = df["period_return"].mean()
    periods_per_year = 12
    ann_ret = (1 + total) ** (periods_per_year / len(df)) - 1 if len(df) > 0 else 0
    vol = df["period_return"].std() * np.sqrt(periods_per_year) if len(df) > 1 else 0
    sharpe = ann_ret / vol if vol > 0 else 0
    running = (1 + df["period_return"]).cumprod()
    peak = running.cummax()
    max_dd = float(((running - peak) / peak).min())

    out = {
        "strategy": f"3factor_s{args.w_size:g}_l{args.w_liquidity:g}_g{args.w_growth:g}",
        "period": f"{df['rebalance'].iloc[0]} ~ {df['rebalance'].iloc[-1]}",
        "n_periods": len(df),
        "total_return": float(total),
        "annual_return": float(ann_ret),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_dd),
        "avg_period_return": float(df["period_return"].mean()),
        "positive_period_ratio": float((df["period_return"] > 0).mean()),
        "avg_n_held": float(df["n_held"].mean()),
    }
    print(out)
    Path(args.out).write_text(__import__("json").dumps(out, indent=2, ensure_ascii=False))
    df.to_csv(str(Path(args.out).with_suffix(".csv")), index=False)


if __name__ == "__main__":
    main()
