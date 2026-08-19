"""Rolling-window statistics and charts for the two-factor long-only combo.

Computes the "odds" (share of rolling windows with positive return), the
longest failure periods (consecutive rolling-12m-negative windows), rolling
excess vs CSI300, information ratio, drawdown segments, and monthly return
distribution, then renders charts.

Reuses the combo daily returns from two_factor_deep_dive.py output and rebuilds
the CSI300 index series for excess / alpha comparisons.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from long_only_style_analysis import return_stats

BG = "#1e1e1e"


def _monthly(series: pd.Series) -> pd.Series:
    return (1 + series.dropna()).resample("ME").prod() - 1


def _load_csi300(data_root: Path) -> pd.Series:
    base = data_root / "assets/tushare/a_share/index_daily"
    parts = []
    for p in (
        base / "a_share_all_index_daily_csi300_2008_2015/data/part.parquet",
        base / "a_share_all_index_daily_csi300_2015/data/part.parquet",
    ):
        d = pd.read_parquet(p)
        d["trade_date"] = pd.to_datetime(d["trade_date"])
        parts.append(d[["trade_date", "pct_chg"]])
    df = pd.concat(parts).drop_duplicates("trade_date").sort_values("trade_date")
    s = pd.to_numeric(df["pct_chg"], errors="coerce") / 100.0
    s.index = df["trade_date"]
    return s[~s.index.duplicated(keep="first")].sort_index()


def _rolling_segments(
    monthly: pd.Series, window: int,
) -> list[tuple[pd.Timestamp, pd.Timestamp, int]]:
    roll = monthly.rolling(window).apply(lambda x: (1 + x).prod() - 1)
    neg = (roll < 0).to_numpy(dtype=bool)
    dates = roll.index
    segments: list[tuple[pd.Timestamp, pd.Timestamp, int]] = []
    start = None
    for i, v in enumerate(neg):
        if v:
            if start is None:
                start = dates[i]
        else:
            if start is not None:
                segments.append(
                    (start, dates[i - 1],
                     len(pd.date_range(start, dates[i - 1], freq="ME")))
                )
                start = None
    if start is not None:
        segments.append((start, dates[-1], len(pd.date_range(start, dates[-1], freq="ME"))))
    segments.sort(key=lambda s: s[2], reverse=True)
    return segments


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
    combo_m = _monthly(combo)
    csi = _load_csi300(data_root)
    csi_m = _monthly(csi)

    # ---- 1. rolling odds ----
    print("[1] rolling-window odds", flush=True)
    odds_rows = []
    for w in [6, 12, 24, 36, 60]:
        roll = combo_m.rolling(w).apply(lambda x: (1 + x).prod() - 1)
        n = roll.notna().sum()
        neg = int((roll < 0).sum())
        odds_rows.append({
            "window_months": w, "samples": int(n),
            "neg": neg, "pos": int(n - neg),
            "neg_pct": round(neg / n * 100, 1) if n else None,
            "pos_pct": round((n - neg) / n * 100, 1) if n else None,
            "odds": round((n - neg) / neg, 2) if neg else None,
        })
    pd.DataFrame(odds_rows).to_csv(outdir / "rolling_odds.csv", index=False)
    print(pd.DataFrame(odds_rows).to_string(index=False))

    # ---- 2. failure periods (rolling 12m negative) ----
    print("\n[2] failure periods (rolling-12m negative)", flush=True)
    segs = _rolling_segments(combo_m, 12)
    pd.DataFrame(
        [{"start": s.date().isoformat(), "end": e.date().isoformat(),
          "windows": n} for s, e, n in segs]
    ).to_csv(outdir / "failure_periods.csv", index=False)
    for s, e, n in segs[:5]:
        print(f"  {s.date()} ~ {e.date()}  ({n} windows)")

    # ---- 3. rolling excess + info ratio vs CSI300 ----
    print("\n[3] rolling excess vs CSI300", flush=True)
    # align monthly
    both = pd.concat({"combo": combo_m, "csi": csi_m}, axis=1).dropna()
    excess_m = both["combo"] - both["csi"]
    ir = excess_m.mean() / excess_m.std() * np.sqrt(12) if excess_m.std() > 0 else np.nan
    ann_excess = (1 + excess_m).prod() ** (12 / len(excess_m)) - 1
    print(f"  info_ratio(annualized): {ir:.2f}")
    print(f"  annualized excess vs CSI300: {ann_excess*100:.1f}%")
    pd.DataFrame({"month": excess_m.index, "excess": excess_m.values}).to_csv(
        outdir / "monthly_excess_csi300.csv", index=False
    )

    # ---- 4. full stats ----
    full = return_stats(combo)
    print("\n[4] full-period stats:", full)

    summary = {
        "combo_2008_2026": full,
        "info_ratio_vs_csi300": float(ir) if ir == ir else None,
        "annualized_excess_vs_csi300": float(ann_excess),
    }
    (outdir / "summary.json").write_text(
        __import__("json").dumps(summary, ensure_ascii=False, indent=2)
    )

    # ===================== charts =====================
    print("\n[charts] rendering", flush=True)

    # NAV + drawdown
    nav = (1 + combo).cumprod()
    dd = nav / nav.cummax() - 1
    fig, ax = plt.subplots(2, 1, figsize=(16, 9), sharex=True)
    ax[0].plot(nav.index, nav.values, lw=1.5, color="#4fc3f7")
    ax[0].set_yscale("log")
    ax[0].set_title("Two-factor Top-100 NAV (log)", color="#eee")
    ax[0].grid(alpha=0.3)
    ax[1].fill_between(dd.index, dd.values, 0, color="#ef5350", alpha=0.6)
    ax[1].set_title("Drawdown", color="#eee")
    ax[1].grid(alpha=0.3)
    for a in ax:
        a.tick_params(colors="#eee")
        a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.savefig(outdir / "nav_drawdown.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)

    # Rolling return curves
    fig, ax = plt.subplots(figsize=(16, 6))
    for w, c in [(12, "#4fc3f7"), (36, "#ffb74d"), (60, "#81c784")]:
        roll = combo_m.rolling(w).apply(lambda x: (1 + x).prod() - 1) * 100
        ax.plot(roll.index, roll.values, lw=1.3, label=f"rolling {w}m", color=c)
    ax.axhline(0, color="#888", lw=0.8)
    ax.set_title("Rolling window returns (%)", color="#eee")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.tick_params(colors="#eee")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.savefig(outdir / "rolling_returns.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)

    # Rolling odds bar
    fig, ax = plt.subplots(figsize=(10, 5))
    o = pd.DataFrame(odds_rows)
    x = o["window_months"].astype(str)
    ax.bar(x, o["pos_pct"], color="#81c784", label="positive %")
    ax.bar(x, o["neg_pct"], bottom=o["pos_pct"], color="#ef5350", label="negative %")
    for i, row in o.iterrows():
        ax.text(i, row["pos_pct"] + 2, f"odds {row['odds']}", ha="center", color="#eee")
    ax.set_ylim(0, 110)
    ax.set_title("Rolling-window positive vs negative odds", color="#eee")
    ax.legend()
    ax.tick_params(colors="#eee")
    fig.savefig(outdir / "rolling_odds.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)

    # Failure-period gantt
    fig, ax = plt.subplots(figsize=(16, 3))
    for i, (s, e, n) in enumerate(segs[:6]):
        ax.barh(6 - i, (e - s).days, left=s, height=0.5, color="#ef5350", alpha=0.7)
        ax.text(s, 6 - i + 0.2, f"{n}m", color="#eee", fontsize=8)
    ax.set_title("Failure periods (rolling-12m negative)", color="#eee")
    ax.tick_params(colors="#eee")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_yticks([])
    fig.savefig(outdir / "failure_periods.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)

    # Monthly return distribution
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.hist(combo_m.dropna() * 100, bins=40, color="#4fc3f7", alpha=0.8)
    ax.axvline(0, color="#ef5350", lw=1)
    ax.set_title("Monthly return distribution (%)", color="#eee")
    ax.tick_params(colors="#eee")
    fig.savefig(outdir / "monthly_distribution.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)

    print("[done] wrote outputs and charts to", outdir)


if __name__ == "__main__":
    main()
