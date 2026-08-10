"""Execution feasibility check for the 3-factor strategy.

Uses the exported monthly holdings and daily amount to estimate whether a
100万 portfolio can actually trade the small-cap-heavy 3-factor book under
VWAP-style splitting (participation_rate x buy_max_days), mirroring the
execution_sim approach validated for top800.

For each rebalance, the portfolio wants to hold top-30 equal weight. At
rebalance we sell the names leaving the book and buy the names entering.
Per name the target notional = portfolio_value / top_k. We estimate
executable notional = daily_amount * participation_rate * buy_max_days
(rolling window from the rebalance date). Fill ratio per name is
min(1, executable / target). Names with low amount may not fully fill.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdings", default="/tmp/3f_holdings.csv")
    ap.add_argument("--data-root", default="/home/richard/data/market-data-platform")
    ap.add_argument("--portfolio-value", type=float, default=1_000_000.0)
    ap.add_argument("--participation-rate", type=float, default=0.10)
    ap.add_argument("--buy-max-days", type=int, default=10)
    ap.add_argument("--top-k", type=int, default=30)
    ap.add_argument("--out", default="/tmp/3factor_exec.json")
    args = ap.parse_args()

    holdings = pd.read_csv(args.holdings)
    holdings["rebalance"] = pd.to_datetime(holdings["rebalance"])
    rebalance_dates = sorted(holdings["rebalance"].unique())
    print(f"[holdings] {len(holdings)} rows, {len(rebalance_dates)} rebalances")

    target_per_name = args.portfolio_value / args.top_k
    target_amounts = []

    for reb in rebalance_dates:
        period_holdings = holdings[holdings["rebalance"] == reb]["symbol"].tolist()
        # daily amount for these symbols over the buy window after rebalance
        frames = []
        for sym in period_holdings:
            try:
                d = pd.read_parquet(
                    f"{args.data_root}/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data/{sym}.parquet",
                    columns=["trade_date", "amount"],
                )
                d["trade_date"] = pd.to_datetime(d["trade_date"])
                d = d[d["trade_date"] > reb]
                d = d.sort_values("trade_date").head(args.buy_max_days)
                if not d.empty:
                    d["symbol"] = sym
                    frames.append(d)
            except FileNotFoundError:
                continue
        if not frames:
            continue
        amt = pd.concat(frames, ignore_index=True)
        # executable notional per name = mean daily amount over window * participation * days
        per_name = (
            amt.groupby("symbol")["amount"].mean()
            * args.participation_rate
            * args.buy_max_days
            * 1000.0  # amount is in 千元 (thousands of CNY); convert to 元
        )
        for sym in period_holdings:
            exec_amt = float(per_name.get(sym, np.nan))
            fill = min(1.0, exec_amt / target_per_name) if exec_amt == exec_amt else 0.0
            target_amounts.append(
                {"rebalance": reb.date().isoformat(), "symbol": sym, "exec_amt": exec_amt, "fill_ratio": fill}
            )

    res = pd.DataFrame(target_amounts)
    if res.empty:
        print("No data.")
        return

    print("\n=== 成交率（fill ratio）分布 ===")
    print(res["fill_ratio"].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]))
    full_fill = (res["fill_ratio"] >= 1.0).mean()
    print(f"\n完整成交占比: {full_fill:.1%}")
    print(f"成交率<50%: {(res['fill_ratio'] < 0.5).mean():.1%}")
    print(f"平均成交率: {res['fill_ratio'].mean():.1%}")

    # per-name notional = 100万/30 ≈ 3.33万
    print(f"\n[context] 每只目标金额 {target_per_name:.0f} 元（100万/30）")
    med_exec = res.groupby("symbol")["exec_amt"].median().median()
    print(f"持仓股票中位可成交额（10天窗口）: {med_exec:.0f} 元")

    out = {
        "portfolio_value": args.portfolio_value,
        "participation_rate": args.participation_rate,
        "buy_max_days": args.buy_max_days,
        "avg_fill_ratio": float(res["fill_ratio"].mean()),
        "full_fill_ratio": float(full_fill),
        "below_50pct_ratio": float((res["fill_ratio"] < 0.5).mean()),
        "median_fill_ratio": float(res["fill_ratio"].median()),
        "target_per_name": float(target_per_name),
    }
    print("\n" + str(out))
    Path(args.out).write_text(__import__("json").dumps(out, indent=2))
    res.to_csv(str(Path(args.out).with_suffix(".csv")), index=False)


if __name__ == "__main__":
    main()
