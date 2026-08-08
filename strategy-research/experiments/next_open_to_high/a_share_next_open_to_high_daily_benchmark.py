"""Matched-universe daily benchmark for next-open-to-high research."""

from __future__ import annotations

import argparse
from collections.abc import Callable

import pandas as pd
from a_share_next_open_to_high_common import policy_name


def matched_universe_benchmark(
    test: pd.DataFrame,
    args: argparse.Namespace,
    apply_exit_policy: Callable[..., pd.DataFrame],
) -> pd.DataFrame:
    slots = (
        test.groupby("trade_date", sort=True).agg(benchmark_slots=("symbol", "size")).reset_index()
    )
    slots = slots.rename(columns={"trade_date": "signal_date"})
    policies: list[float | None] = list(args.take_profit_pct)
    if args.include_close_exit:
        policies.append(None)
    policy_frame = pd.DataFrame({"exit_policy": [policy_name(policy) for policy in policies]})
    base = slots.merge(policy_frame, how="cross")
    eligible = test.loc[test["evaluation_eligible"]].copy()
    if eligible.empty:
        realized = pd.DataFrame(
            {
                "signal_date": pd.Series(dtype="datetime64[ns]"),
                "exit_policy": pd.Series(dtype="string"),
                "benchmark_executed": pd.Series(dtype="int64"),
                "benchmark_gross_return_sum": pd.Series(dtype="float64"),
                "benchmark_return_sum": pd.Series(dtype="float64"),
            }
        )
    else:
        eligible["signal_date"] = eligible["trade_date"]
        benchmark_trades = pd.concat(
            [
                apply_exit_policy(
                    eligible,
                    take_profit_pct=policy,
                    entry_slippage_bps=float(args.entry_slippage_bps),
                    exit_slippage_bps=float(args.exit_slippage_bps),
                    round_trip_cost_bps=float(args.round_trip_cost_bps),
                    participation_rate=float(args.participation_rate),
                )
                for policy in policies
            ],
            ignore_index=True,
        )
        realized = (
            benchmark_trades.groupby(["signal_date", "exit_policy"], sort=True)
            .agg(
                benchmark_executed=("symbol", "size"),
                benchmark_gross_return_sum=("gross_return", "sum"),
                benchmark_return_sum=("net_return", "sum"),
            )
            .reset_index()
        )
    output = base.merge(
        realized,
        on=["signal_date", "exit_policy"],
        how="left",
        validate="one_to_one",
    )
    output["benchmark_executed"] = output["benchmark_executed"].fillna(0).astype(int)
    output["benchmark_gross_return_sum"] = output["benchmark_gross_return_sum"].fillna(0.0)
    output["benchmark_return_sum"] = output["benchmark_return_sum"].fillna(0.0)
    output["benchmark_return"] = output["benchmark_return_sum"] / output["benchmark_slots"]
    output["benchmark_invested_weight"] = output["benchmark_executed"] / output["benchmark_slots"]
    output["benchmark_executed_mean_return"] = (
        output["benchmark_return_sum"] / output["benchmark_executed"].replace(0, pd.NA)
    ).fillna(0.0)
    return output


def _summarize_band_mix(
    frame: pd.DataFrame,
    *,
    scope: str,
    date_column: str,
    top_k: int | None,
) -> pd.DataFrame:
    total_rows = len(frame)
    total_dates = frame[date_column].nunique()
    daily = (
        frame.groupby([date_column, "limit_band"], observed=True, sort=True)
        .agg(band_rows=("limit_band", "size"))
        .reset_index()
    )
    daily["daily_weight"] = daily["band_rows"] / daily.groupby(date_column)["band_rows"].transform(
        "sum"
    )
    summary = (
        daily.groupby("limit_band", observed=True, sort=True)
        .agg(
            rows=("band_rows", "sum"),
            dates_present=(date_column, "nunique"),
            daily_weight_sum=("daily_weight", "sum"),
            daily_weight_median_when_present=("daily_weight", "median"),
        )
        .reset_index()
    )
    summary["row_share"] = summary["rows"] / max(total_rows, 1)
    summary["daily_weight_mean"] = summary.pop("daily_weight_sum") / max(total_dates, 1)
    summary["total_dates"] = total_dates
    summary.insert(0, "top_k", top_k)
    summary.insert(0, "scope", scope)
    return summary


def build_limit_band_mix(test: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    parts = [
        _summarize_band_mix(
            test,
            scope="signal_universe",
            date_column="trade_date",
            top_k=None,
        )
    ]
    for top_k, group in selected.groupby("top_k", sort=True):
        top_k_value = int(str(top_k))
        parts.append(
            _summarize_band_mix(
                group,
                scope="selected_signal",
                date_column="signal_date",
                top_k=top_k_value,
            )
        )
        parts.append(
            _summarize_band_mix(
                group.loc[group["execution_eligible"]],
                scope="selected_execution_eligible",
                date_column="signal_date",
                top_k=top_k_value,
            )
        )
    return pd.concat(parts, ignore_index=True)
