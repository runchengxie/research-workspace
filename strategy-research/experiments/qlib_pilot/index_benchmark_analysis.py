"""Two-factor combo vs real index benchmarks (CSI300 / 中证800).

Compares the small-cap + low-turnover (no growth) Top-100 long-only combo
against real A-share indexes to separate alpha from market beta and to verify
whether the post-2018 attenuation is absolute or relative.

Reuses the combo daily returns from two_factor_deep_dive.py output.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from long_only_style_analysis import return_stats, yearly_returns


def _load_index_returns(data_root: Path, name: str) -> pd.Series:
    base = data_root / "assets/tushare/a_share/index_daily"
    if name == "csi300":
        p1 = base / "a_share_all_index_daily_csi300_2008_2015/data/part.parquet"
        p2 = base / "a_share_all_index_daily_csi300_2015/data/part.parquet"
        parts = []
        for p in (p1, p2):
            d = pd.read_parquet(p)
            d["trade_date"] = pd.to_datetime(d["trade_date"])
            parts.append(d[["trade_date", "pct_chg"]])
        df = pd.concat(parts).drop_duplicates("trade_date").sort_values("trade_date")
    elif name == "zj800":
        p = base / "a_share_all_index_daily_zj800/data/part.parquet"
        d = pd.read_parquet(p)
        d["trade_date"] = pd.to_datetime(d["trade_date"])
        df = d[["trade_date", "pct_chg"]]
    else:
        raise ValueError(name)
    df["return"] = pd.to_numeric(df["pct_chg"], errors="coerce") / 100.0
    s = df.dropna(subset=["return"]).set_index("trade_date")["return"]
    return s[~s.index.duplicated(keep="first")].sort_index()


def _align(excess: pd.Series, ref: pd.Series) -> pd.Series:
    return excess.reindex(ref.index).ffill()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="/home/richard/data/market-data-platform")
    ap.add_argument("--combo-daily", default="/tmp/twof_out/two_factor_vs_benchmark_daily.parquet")
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    data_root = Path(args.data_root)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    daily = pd.read_parquet(args.combo_daily)
    combo = daily["two_factor_top100"].dropna().sort_index()
    combo.name = "return"

    csi300 = _load_index_returns(data_root, "csi300")
    zj800 = _load_index_returns(data_root, "zj800")

    print("[combo] 2008-2026 full stats", flush=True)
    print("  combo:", return_stats(combo), flush=True)

    rows = []
    rows.append({"bench": "csi300_2008_2026", **return_stats(combo)})
    rows.append({"bench": "csi300_2008_2026", "series": "index",
                 **return_stats(csi300)})
    rows.append({"bench": "zj800_2015_2026", **return_stats(combo)})
    rows.append({"bench": "zj800_2015_2026", "series": "index",
                 **return_stats(zj800)})

    # Annual comparison vs CSI300 (2008-2026)
    annual = []
    combo_y = yearly_returns(combo)
    csi_y = yearly_returns(csi300)
    for year in sorted(set(combo_y.index) & set(csi_y.index)):
        annual.append({
            "year": year,
            "combo": combo_y[year],
            "csi300": csi_y[year],
            "excess": combo_y[year] - csi_y[year],
        })
    annual_df = pd.DataFrame(annual)
    annual_df.to_csv(outdir / "annual_vs_csi300.csv", index=False)

    # Rolling-window (starting 2018) to test attenuation: absolute vs relative
    print("\n[roll] combo vs CSI300 by window", flush=True)
    roll = []
    for start in ["2008-01-01", "2010-01-01", "2012-01-01", "2015-01-01",
                  "2018-01-01", "2020-01-01"]:
        s = pd.Timestamp(start)
        c = combo[combo.index >= s]
        b = csi300[csi300.index >= s]
        a = c - b.reindex(c.index).ffill()
        roll.append({
            "start": start,
            "combo_sharpe": return_stats(c)["sharpe"],
            "csi300_sharpe": return_stats(b)["sharpe"],
            "excess_ann": (a.mean() * 252),
            "combo_ann": return_stats(c)["annual_return"],
        })
    roll_df = pd.DataFrame(roll)
    roll_df.to_csv(outdir / "rolling_vs_csi300.csv", index=False)
    print(roll_df.to_string(index=False))

    summary = {
        "csi300_2008_2026": return_stats(csi300),
        "zj800_2015_2026": return_stats(zj800),
        "combo_2008_2026": return_stats(combo),
        "combo_2015_2026": return_stats(combo[combo.index >= "2015-01-01"]),
    }
    (outdir / "index_benchmark_summary.json").write_text(
        __import__("json").dumps(summary, ensure_ascii=False, indent=2)
    )
    print("\n[done] wrote to", outdir)


if __name__ == "__main__":
    main()
