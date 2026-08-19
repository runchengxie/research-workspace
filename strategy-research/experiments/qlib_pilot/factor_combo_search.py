"""Search factor combinations for synergy (2-factor and 3-factor combos).

Tests all C(15,2) two-factor and C(15,3) three-factor combinations of the 15
Barra-style factors for a long-only Top-K portfolio, ranking by a combined
metric of Sharpe and rolling-36m odds.

Method: load the monthly factor panel (factor_z scores) and the daily return
matrix once, then for each combo compute the composite score, pick Top-100 each
month, and accumulate the equal-weight daily returns in memory.  This avoids
re-reading the full pricing file per combo.

Only 2- and 3-factor combos are tested (560 total) to keep the search tractable
while capturing pairwise and triple synergy.
"""

from __future__ import annotations

import argparse
import itertools
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from long_only_style_analysis import load_pricing

from style_factors.workflow import load_data

# Direction for each factor (from the Barra long-only study).
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

# Exclude factors with too little data for a long-only Top-K study.
EXCLUDE = {"liquidity_flow"}  # only ~0.5y of coverage


def _factors() -> list[str]:
    return [f for f in FACTOR_DIRECTION if f not in EXCLUDE]


def _composite_score(panel: pd.DataFrame, factors: tuple[str, ...]) -> pd.Series:
    return sum(
        panel[f"factor_{f}_z"].fillna(0) * FACTOR_DIRECTION[f] for f in factors
    )


def _run_combo(panel, ret_matrix, rebalance_dates, trade_dates, factors, top_k,
               cost_bps) -> pd.Series:
    """Fast monthly Top-K long-only backtest returning a daily return series."""
    score = _composite_score(panel, factors)
    p = panel[["trade_date", "symbol"]].copy()
    p["score"] = score.values

    daily = {}
    held = set()
    for i, reb in enumerate(rebalance_dates):
        entry = _next_trading_day(reb, trade_dates)
        if entry is None:
            break
        next_reb = rebalance_dates[i + 1] if i + 1 < len(rebalance_dates) else trade_dates[-1]
        day_rows = p[p["trade_date"] == reb].sort_values("score", ascending=False)
        top = set(day_rows.head(top_k)["symbol"].tolist())
        if not top:
            continue
        # turnover: names bought + names sold
        turnover = (len(top - held) + len(held - top)) / top_k
        window = ret_matrix.loc[(ret_matrix.index > entry) & (ret_matrix.index <= next_reb), :]
        if window.empty:
            held = top
            continue
        cols = [c for c in window.columns if c in top]
        if not cols:
            held = top
            continue
        sub = window[cols].dropna(axis=1, how="all")
        if sub.empty:
            held = top
            continue
        day_ret = sub.mean(axis=1)
        for dt, r in day_ret.items():
            daily[dt] = daily.get(dt, 1.0) * (1 + r) - 1
        cost = turnover * cost_bps / 1e4
        daily[entry] = (1 + daily.get(entry, 0.0)) * (1 - cost) - 1
        held = top
    return pd.Series(daily).sort_index()


def _next_trading_day(date: pd.Timestamp, trade_dates: pd.DatetimeIndex) -> pd.Timestamp | None:
    later = trade_dates[trade_dates > date]
    return later[0] if len(later) else None


def _stats(returns: pd.Series) -> dict:
    r = returns.dropna()
    if r.empty or r.std() == 0:
        return {"sharpe": np.nan, "ann": np.nan}
    nav = (1 + r).cumprod()
    years = len(r) / 252
    ann = nav.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
    sharpe = r.mean() / r.std() * np.sqrt(252)
    # rolling 36m odds
    m = (1 + r).resample("ME").prod() - 1
    roll = m.rolling(36).apply(lambda x: (1 + x).prod() - 1)
    n = roll.notna().sum()
    neg = (roll < 0).sum()
    odds = (n - neg) / neg if neg > 0 else np.nan
    return {"sharpe": sharpe, "ann": ann, "odds36": odds}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="/home/richard/data/market-data-platform")
    ap.add_argument("--panel", default="/tmp/longonly_p2_full/panel_p2_full.parquet")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--top-k", type=int, default=100)
    ap.add_argument("--cost-bps", type=float, default=30.0)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ret-cache", type=Path, default=None)
    args = ap.parse_args()

    data_root = Path(args.data_root)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    end = pd.Timestamp("2026-08-18")

    print("[load] panel", flush=True)
    panel = pd.read_parquet(args.panel)
    panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    factors = _factors()
    print(f"[factors] testing {len(factors)} factors", flush=True)

    print("[load] daily + pricing return matrix", flush=True)
    if args.ret_cache is not None and args.ret_cache.exists():
        ret_matrix = pd.read_parquet(args.ret_cache)
        meta_path = args.ret_cache.with_suffix(".pkl")
        with open(meta_path, "rb") as fh:
            meta = pickle.load(fh)
        trade_dates = meta["trade_dates"]
        print(f"[cache] ret_matrix {ret_matrix.shape}", flush=True)
    else:
        daily, _ = load_data(data_root, start_date="2008-01-01",
                             basics_rebalance_only=False)
        trade_dates = pd.DatetimeIndex(sorted(daily["trade_date"].unique()))
        trade_dates = trade_dates[trade_dates <= end]
        symbols = set(panel["symbol"].unique())
        pricing = load_pricing(data_root, symbols, pd.Timestamp("2008-01-01"), end,
                               workers=args.workers, source="raw")
        ret_matrix = pricing.pivot_table(index="trade_date", columns="symbol",
                                         values="ret")
        ret_matrix = ret_matrix.sort_index()
        print(f"[matrix] {ret_matrix.shape}", flush=True)

    rebalance_dates = pd.DatetimeIndex(sorted(panel["trade_date"].unique()))

    combos = list(itertools.combinations(factors, 2)) + list(itertools.combinations(factors, 3))
    if args.limit:
        combos = combos[: args.limit]
    print(f"[combos] {len(combos)} to test", flush=True)

    results = []
    for idx, combo in enumerate(combos):
        s = _run_combo(panel, ret_matrix, rebalance_dates, trade_dates, combo,
                       args.top_k, args.cost_bps)
        st = _stats(s)
        results.append({"combo": "+".join(combo), "n_factors": len(combo),
                        "sharpe": round(st["sharpe"], 3),
                        "ann": round(st["ann"], 4) if st["ann"] == st["ann"] else None,
                        "odds36": round(st["odds36"], 2) if st["odds36"] == st["odds36"] else None})
        if (idx + 1) % 50 == 0 or idx == len(combos) - 1:
            print(f"[progress] {idx+1}/{len(combos)}", flush=True)

    df = pd.DataFrame(results)
    df = df.sort_values("sharpe", ascending=False).reset_index(drop=True)
    df.to_csv(outdir / "factor_combo_results.csv", index=False)
    print("\n=== Top 20 by Sharpe ===")
    print(df.head(20).to_string(index=False))
    print("\n=== Top 10 by odds36 ===")
    print(df.sort_values("odds36", ascending=False).head(10).to_string(index=False))
    print("\n[done] wrote to", outdir)


if __name__ == "__main__":
    main()
