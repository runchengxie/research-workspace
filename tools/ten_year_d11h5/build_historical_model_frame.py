"""Build a research-only historical D11-H5 model frame from clean daily data.

This runner deliberately starts from the earliest available clean daily asset,
rather than borrowing the current published frame.  It reuses the owner
feature and limit-aware label implementations and writes a self-describing
Parquet artifact plus a coverage receipt.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from alpha_research.daily_watch20_features import (
    DailyWatch20FeatureConfig,
    build_daily_watch20_feature_frame,
)
from market_data_platform.research_views.daily_watch20_data import (
    load_daily_watch20_daily,
    resolve_daily_watch20_assets,
)
from strategy_app.daily_watch20.d11_h5_shadow_model import (
    _add_d11_label,
    _freeze_top800,
)
from strategy_app.daily_watch20.daily_watch20_flite_contract import DAILY_FEATURES


def build(data_root: Path, output_dir: Path, *, start_date: str, end_date: str) -> pd.DataFrame:
    assets = resolve_daily_watch20_assets(data_root)
    daily = load_daily_watch20_daily(
        assets,
        start_date=start_date,
        end_date=end_date,
        memory_limit="16GB",
        threads=4,
    )
    base = build_daily_watch20_feature_frame(
        daily,
        None,
        config=DailyWatch20FeatureConfig(
            forward_days=20,
            label_horizon_weights=((1, 0.25), (5, 0.25), (10, 0.25), (20, 0.25)),
            minute_lag_trade_days=0,
        ),
    )
    base = _add_d11_label(base)
    base, universe_summary = _freeze_top800(base)
    eligible = base["hard_eligible"].astype(bool)
    returns = pd.to_numeric(base["incremental_return_D11_20"], errors="coerce").where(eligible)
    base["incremental_rank_D11_20"] = returns.groupby(base["trade_date"], sort=False).rank(
        method="average", pct=True
    )
    keep = list(
        dict.fromkeys(
            [
                "trade_date",
                "symbol",
                "hard_eligible",
                *DAILY_FEATURES,
                "incremental_return_D11_20",
                "incremental_rank_D11_20",
                "incremental_label_end_D11_20",
            ]
        )
    )
    missing = sorted(set(keep) - set(base.columns))
    if missing:
        raise ValueError(f"historical D11 model frame misses columns: {missing}")
    frame = (
        base.loc[eligible, keep]
        .sort_values(["trade_date", "symbol"], kind="mergesort")
        .reset_index(drop=True)
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_dir / "model_frame.parquet", index=False)
    counts = frame.groupby("trade_date", sort=True).size()
    receipt = {
        "schema_version": "research.d11_h5_historical_model_frame.v1",
        "research_only": True,
        "production_eligible": False,
        "data_root": str(data_root),
        "daily_asset": str(assets.daily_clean),
        "requested_start_date": start_date,
        "requested_end_date": end_date,
        "date_min": frame["trade_date"].min().isoformat(),
        "date_max": frame["trade_date"].max().isoformat(),
        "dates": int(frame["trade_date"].nunique()),
        "rows": int(len(frame)),
        "per_date_count_min": int(counts.min()),
        "per_date_count_median": float(counts.median()),
        "per_date_count_max": int(counts.max()),
        "feature_columns": list(DAILY_FEATURES),
        "label_policy": "next_open_incremental_bucket_limit_aware.v1",
        "universe_summary": universe_summary,
    }
    (output_dir / "model_frame.receipt.json").write_text(
        json.dumps(receipt, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start-date", default="20150105")
    parser.add_argument("--end-date", default="20260902")
    args = parser.parse_args()
    frame = build(
        args.data_root,
        args.output_dir,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    print(
        f"built {len(frame):,} rows across {frame['trade_date'].nunique():,} dates "
        f"from {frame['trade_date'].min():%Y-%m-%d} to {frame['trade_date'].max():%Y-%m-%d}",
        flush=True,
    )


if __name__ == "__main__":
    main()
