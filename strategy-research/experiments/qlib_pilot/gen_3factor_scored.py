"""Generate a fixed-score artifact for the 3-factor strategy.

Reuses style_factors loaders + compute_factors to build, for every trading
day in range, per-stock composite score:

    score = -w_size*z(size) + w_liquidity*z(liquidity) + w_growth*z(growth)

Output is a parquet with columns required by strategy-pipeline's
fixed_score_artifact replay mode:
    trade_date, symbol, close, vol, amount, score

Optional --universe filters to a symbol-by-date list (e.g. top800).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from style_factors.factor_calc import compute_factors
from style_factors.workflow import (
    load_cashflow,
    load_fina_indicator,
    load_holder_structure,
    load_moneyflow_ths,
    load_sw_industry_membership,
)

DAILY_CLEAN_DIR = "assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data"
DAILY_BASIC_DIR = "assets/tushare/a_share/daily_basic/a_share_all_daily_basic_latest/data"


def _load_daily_clean(data_root: Path, start: str, end: str) -> pd.DataFrame:
    import concurrent.futures
    import glob

    files = sorted(glob.glob(str(data_root / DAILY_CLEAN_DIR / "*.parquet")))
    if not files:
        # fallback to partitioned dirs
        files = sorted(glob.glob(str(data_root / DAILY_CLEAN_DIR / "trade_date=*" / "part.parquet")))

    start_yy = start.replace("-", "")
    end_yy = end.replace("-", "")

    def read(f):
        d = pd.read_parquet(
            f, columns=["trade_date", "symbol", "close", "pct_chg", "vol", "amount"]
        )
        dt = d["trade_date"].astype(str).str.replace("-", "", regex=False)
        return d[(dt >= start_yy) & (dt <= end_yy)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
        parts = list(ex.map(read, files))
    return pd.concat(parts, ignore_index=True)


def _load_daily_basic(data_root: Path, start: str, end: str) -> pd.DataFrame:
    import concurrent.futures
    import glob

    files = sorted(glob.glob(str(data_root / DAILY_BASIC_DIR / "*.parquet")))
    if not files:
        files = sorted(glob.glob(str(data_root / DAILY_BASIC_DIR / "trade_date=*" / "part.parquet")))

    start_yy = start.replace("-", "")
    end_yy = end.replace("-", "")

    def read(f):
        d = pd.read_parquet(
            f,
            columns=["trade_date", "symbol", "total_mv", "pb", "pe_ttm", "turnover_rate", "ps_ttm", "dv_ttm"],
        )
        dt = d["trade_date"].astype(str).str.replace("-", "", regex=False)
        return d[(dt >= start_yy) & (dt <= end_yy)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
        parts = list(ex.map(read, files))
    return pd.concat(parts, ignore_index=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="/home/richard/data/market-data-platform")
    ap.add_argument("--start-date", default="2019-01-01")
    ap.add_argument("--end-date", default="2026-08-07")
    ap.add_argument("--w-size", type=float, default=2.0)
    ap.add_argument("--w-liquidity", type=float, default=1.0)
    ap.add_argument("--w-growth", type=float, default=1.0)
    ap.add_argument("--universe", choices=["full", "top800"], default="full")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    daily = _load_daily_clean(Path(args.data_root), args.start_date, args.end_date)
    basics = _load_daily_basic(Path(args.data_root), args.start_date, args.end_date)
    daily["trade_date"] = pd.to_datetime(daily["trade_date"])
    basics["trade_date"] = pd.to_datetime(basics["trade_date"])
    print(f"[daily] {len(daily)} rows, {daily['trade_date'].min().date()} ~ {daily['trade_date'].max().date()}, has close/vol/amount")

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
    )
    print(f"[factors] {len(factors)} rows, {factors['trade_date'].min()} ~ {factors['trade_date'].max()}")

    sel = factors.copy()
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

    out_cols = ["trade_date", "symbol", "score"]
    scored = sel[out_cols].copy()

    # compute_factors returns only factors; merge close/vol/amount from daily_clean.
    price = daily[["trade_date", "symbol", "close", "vol", "amount"]].copy()
    scored = scored.merge(price, on=["trade_date", "symbol"], how="left")
    print(f"[merge] {len(scored)} rows, close cov={scored['close'].notna().mean():.1%}, vol cov={scored['vol'].notna().mean():.1%}")

    if args.universe == "top800":
        univ = pd.read_csv("/home/richard/data/market-data-platform/assets/universe/top800_2019_by_date.csv")
        univ["trade_date"] = univ["trade_date"].astype(str)
        scored["trade_date"] = pd.to_datetime(scored["trade_date"]).dt.strftime("%Y%m%d")
        scored = scored.merge(univ, on=["trade_date", "symbol"], how="inner")
        print(f"[universe] top800 filtered: {len(scored)} rows")

    scored = scored.dropna(subset=["score"]).sort_values(["trade_date", "symbol"]).reset_index(drop=True)
    scored["trade_date"] = pd.to_datetime(scored["trade_date"]).dt.strftime("%Y%m%d")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scored.to_parquet(out_path, index=False)
    print(f"[saved] {len(scored)} rows, {scored['trade_date'].nunique()} dates -> {out_path}")
    print(scored[["trade_date", "symbol", "score"]].head(3).to_string(index=False))


if __name__ == "__main__":
    main()
