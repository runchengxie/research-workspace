"""Backtest summary assembly for next-open-to-high research."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from typing import Any, cast

import pandas as pd
from a_share_next_high_explore import _float_or_none
from a_share_next_open_to_high_common import label_available_mask, policy_name


def _frozen_metric(metrics: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if args.frozen_top_k is None or args.frozen_take_profit_pct is None:
        return pd.DataFrame()
    frozen = metrics.loc[
        metrics["top_k"].eq(args.frozen_top_k)
        & metrics["exit_policy"].eq(policy_name(args.frozen_take_profit_pct))
    ]
    if frozen.empty:
        raise ValueError("Frozen policy is not present in the requested policy grid")
    return frozen


def build_backtest_summary(
    *,
    raw: pd.DataFrame,
    panel: pd.DataFrame,
    train: pd.DataFrame,
    train_sample: pd.DataFrame,
    test: pd.DataFrame,
    model_evaluation: pd.DataFrame,
    model_ic: pd.DataFrame,
    metrics: pd.DataFrame,
    limit_band_mix: pd.DataFrame,
    args: argparse.Namespace,
) -> dict[str, Any]:
    frozen_metric = _frozen_metric(metrics, args)
    pre_purge_train = panel.loc[
        label_available_mask(panel, args.target)
        & panel["trade_date"].le(pd.Timestamp(args.train_end))
    ]
    train_label_end = cast(pd.Timestamp, pd.Timestamp(train["entry_date"].max()))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "rows_loaded": len(raw),
        "rows_research": len(panel),
        "symbols": int(panel["symbol"].nunique()),
        "date_start": panel["trade_date"].min().date().isoformat(),
        "date_end": panel["trade_date"].max().date().isoformat(),
        "train_rows": len(train),
        "train_sample_rows": len(train_sample),
        "train_signal_date_max": train["trade_date"].max().date().isoformat(),
        "train_label_end_max": train_label_end.date().isoformat(),
        "train_label_cutoff": args.train_end,
        "train_rows_purged_for_label_end_after_cutoff": len(pre_purge_train) - len(train),
        "test_rows": len(test),
        "model_evaluation_rows": len(model_evaluation),
        "target": args.target,
        "markets": list(args.markets),
        "model_days": int(model_ic["trade_date"].nunique()) if not model_ic.empty else 0,
        "model_rank_ic_mean": _float_or_none(model_ic["rank_ic"].mean())
        if not model_ic.empty
        else None,
        "primary_policy_is_frozen": not frozen_metric.empty,
        "frozen_metric_row": frozen_metric.head(1).to_dict(orient="records"),
        "policy_grid_best_uses_test_period": True,
        "promotion_eligible": False,
        "hard_limitations": [
            "Wide-universe active return may be dominated by signal-day price-limit-band exposure.",
            "Use the same-entry minute within-band benchmark for stock-selection attribution.",
        ],
        "frozen_selected_limit_band_mix": limit_band_mix.loc[
            limit_band_mix["scope"].eq("selected_signal")
            & limit_band_mix["top_k"].eq(args.frozen_top_k)
        ][["limit_band", "daily_weight_mean"]].to_dict(orient="records"),
        "best_metric_row": metrics.sort_values("sharpe", ascending=False)
        .head(1)
        .to_dict(orient="records"),
    }
