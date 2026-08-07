#!/usr/bin/env python3
"""One-day execution probe for the A-share next-open-to-high model.

The script keeps the model and feature recipe from a_share_next_high_explore.py,
then adds a simple daily execution layer:

1. rank stocks after the signal-day close;
2. buy the next day open when execution filters allow it;
3. sell at a take-profit price if the next day high reaches it;
4. otherwise sell at the next day close.

This is an OHLC research approximation, not an intraday fill simulator.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from a_share_next_high_explore import (
    BASE_FEATURES,
    DEFAULT_DAILY_DIR,
    DEFAULT_OUT_BASE,
    _daily_corr_rows,
    _float_or_none,
    _json_default,
    _parse_top_k,
    add_labels_and_features,
    fit_model,
    load_daily_clean,
    sample_train_rows,
)
from a_share_next_open_to_high_common import (
    BacktestConfig,
    add_execution_fields,
    add_execution_next_columns,
    add_signal_limit_band,
    filter_signal_rows,
    hac_mean_t,
    label_available_mask,
    parse_bps_list as _parse_bps_list,
    parse_markets as _parse_markets,
    parse_pct_list as _parse_pct_list,
    policy_name as _policy_name,
    write_test_predictions,
)
from a_share_next_open_to_high_cost_stress import summarize_cost_stress
from a_share_next_open_to_high_daily_benchmark import (
    build_limit_band_mix,
    matched_universe_benchmark,
)
from a_share_next_open_to_high_reporting import build_backtest_summary


def select_daily_candidates(frame: pd.DataFrame, top_k: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_parts: list[pd.DataFrame] = []
    daily_rows: list[dict[str, Any]] = []
    prev_symbols: set[str] = set()

    for signal_date, group in frame.groupby("trade_date", sort=False):
        ranked = group.sort_values("pred", ascending=False).copy()
        ranked["raw_rank"] = np.arange(1, len(ranked) + 1)
        raw_top = ranked.head(top_k)
        selected = raw_top.copy()
        selected["signal_date"] = signal_date
        selected["selected_rank"] = selected["raw_rank"]
        selected["top_k"] = top_k
        executable = selected.loc[selected["execution_eligible"]]

        symbols = set(executable["symbol"].astype(str))
        overlap = len(symbols & prev_symbols) if prev_symbols else 0
        turnover = 1.0 - overlap / max(top_k, 1) if prev_symbols else 1.0
        prev_symbols = symbols

        daily_rows.append(
            {
                "signal_date": signal_date,
                "entry_date": selected["entry_date"].min() if not selected.empty else pd.NaT,
                "top_k": top_k,
                "raw_candidates": len(raw_top),
                "raw_executable": int(raw_top["execution_eligible"].sum()),
                "filled": len(executable),
                "fill_rate": len(executable) / max(top_k, 1),
                "selection_turnover": turnover,
                "max_raw_rank_used": _float_or_none(executable["raw_rank"].max())
                if not executable.empty
                else None,
                "blocked_limit_up_open_raw": int(raw_top["blocked_limit_up_open"].sum()),
            }
        )
        if not selected.empty:
            selected_parts.append(selected)

    selected = pd.concat(selected_parts, ignore_index=True) if selected_parts else pd.DataFrame()
    return selected, pd.DataFrame(daily_rows)


def apply_exit_policy(
    selected: pd.DataFrame,
    *,
    take_profit_pct: float | None,
    entry_slippage_bps: float,
    exit_slippage_bps: float,
    round_trip_cost_bps: float,
    participation_rate: float,
) -> pd.DataFrame:
    trades = selected.copy()
    trades["take_profit_pct"] = np.nan if take_profit_pct is None else take_profit_pct
    trades["exit_policy"] = _policy_name(take_profit_pct)
    if take_profit_pct is None:
        hit_take_profit = pd.Series(False, index=trades.index)
        exit_price = trades["next_close_price"]
        exit_reason = pd.Series("close", index=trades.index)
    else:
        target_price = trades["entry_price"] * (1.0 + take_profit_pct)
        hit_take_profit = trades["next_high_price"].gt(target_price)
        exit_price = trades["next_close_price"].where(
            ~hit_take_profit,
            trades["entry_price"] * (1.0 + take_profit_pct),
        )
        exit_reason = pd.Series(
            np.where(hit_take_profit, "take_profit", "close"),
            index=trades.index,
        )

    entry_price = trades["entry_price"] * (1.0 + entry_slippage_bps / 10000.0)
    executed_exit = exit_price * (1.0 - exit_slippage_bps / 10000.0)
    trades["exit_price"] = exit_price
    trades["exit_reason"] = exit_reason
    trades["hit_take_profit"] = hit_take_profit
    trades["gross_return"] = exit_price / trades["entry_price"] - 1.0
    trades["net_return"] = executed_exit / entry_price - 1.0 - round_trip_cost_bps / 10000.0
    trades["capacity_cny"] = trades["next_amount_cny"] * participation_rate
    return trades


def aggregate_daily_returns(
    trades: pd.DataFrame,
    daily_selection: pd.DataFrame,
) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    grouped = (
        trades.groupby(["signal_date", "entry_date", "top_k", "exit_policy"], sort=False)
        .agg(
            filled=("symbol", "count"),
            avg_trade_return=("net_return", "mean"),
            avg_gross_trade_return=("gross_return", "mean"),
            hit_take_profit_rate=("hit_take_profit", "mean"),
            open_to_high_mean=("open_to_high", "mean"),
            open_to_close_mean=("open_to_close", "mean"),
            median_trade_capacity_cny=("capacity_cny", "median"),
            capacity_cny_at_participation=("capacity_cny", "sum"),
            avg_raw_rank_used=("raw_rank", "mean"),
            max_raw_rank_used=("raw_rank", "max"),
        )
        .reset_index()
    )
    selection_cols = [
        "signal_date",
        "entry_date",
        "top_k",
        "raw_executable",
        "fill_rate",
        "selection_turnover",
        "blocked_limit_up_open_raw",
    ]
    policies = trades[["exit_policy"]].drop_duplicates()
    base = daily_selection[selection_cols].merge(policies, how="cross")
    output = base.merge(
        grouped,
        on=["signal_date", "entry_date", "top_k", "exit_policy"],
        how="left",
    )
    output["filled"] = output["filled"].fillna(0).astype(int)
    output["avg_trade_return"] = output["avg_trade_return"].fillna(0.0)
    output["avg_gross_trade_return"] = output["avg_gross_trade_return"].fillna(0.0)
    fill_weight = output["filled"] / output["top_k"]
    output["portfolio_return"] = output["avg_trade_return"] * fill_weight
    output["gross_portfolio_return"] = output["avg_gross_trade_return"] * fill_weight
    output["cash_weight"] = 1.0 - fill_weight
    return output


def _max_drawdown(returns: pd.Series) -> float | None:
    if returns.empty:
        return None
    curve = (1.0 + returns.fillna(0.0)).cumprod()
    drawdown = curve / curve.cummax() - 1.0
    return _float_or_none(drawdown.min())


def _annualized_return(total_return: float | None, days: int) -> float | None:
    if total_return is None or days <= 0 or total_return <= -1.0:
        return None
    return _float_or_none((1.0 + total_return) ** (252.0 / days) - 1.0)


def summarize_metrics(daily: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, group in daily.groupby(["top_k", "exit_policy"], sort=True):
        assert isinstance(keys, tuple)
        top_k, exit_policy = keys
        returns = group["portfolio_return"].fillna(0.0)
        gross_returns = group["gross_portfolio_return"].fillna(0.0)
        benchmark_returns = group["benchmark_return"].fillna(0.0)
        matched_benchmark = group["benchmark_exposure_matched_return"].fillna(0.0)
        active_returns = returns - matched_benchmark
        days = len(group)
        strategy_nav = (1.0 + returns).prod()
        total_return = _float_or_none(strategy_nav - 1.0)
        gross_total_return = _float_or_none((1.0 + gross_returns).prod() - 1.0)
        benchmark_total_return = _float_or_none((1.0 + benchmark_returns).prod() - 1.0)
        matched_benchmark_nav = (1.0 + matched_benchmark).prod()
        relative_nav = _float_or_none(strategy_nav / matched_benchmark_nav - 1.0)
        daily_vol = returns.std(ddof=0)
        benchmark_vol = benchmark_returns.std(ddof=0)
        matched_benchmark_vol = matched_benchmark.std(ddof=0)
        active_vol = active_returns.std(ddof=0)
        rows.append(
            {
                "top_k": int(str(top_k)),
                "exit_policy": str(exit_policy),
                "days": days,
                "filled_avg": _float_or_none(group["filled"].mean()),
                "fill_rate_avg": _float_or_none(group["fill_rate"].mean()),
                "selection_turnover_avg": _float_or_none(group["selection_turnover"].mean()),
                "daily_return_mean": _float_or_none(returns.mean()),
                "daily_return_median": _float_or_none(returns.median()),
                "daily_win_rate": _float_or_none(returns.gt(0).mean()),
                "daily_vol": _float_or_none(daily_vol),
                "ann_return": _annualized_return(total_return, days),
                "ann_vol": _float_or_none(daily_vol * math.sqrt(252.0)),
                "sharpe": _float_or_none(returns.mean() / daily_vol * math.sqrt(252.0))
                if daily_vol and daily_vol > 0
                else None,
                "hac_mean_t_5": hac_mean_t(returns, lags=5),
                "total_return": total_return,
                "gross_total_return": gross_total_return,
                "benchmark_return_mean": _float_or_none(benchmark_returns.mean()),
                "benchmark_total_return": benchmark_total_return,
                "benchmark_sharpe": _float_or_none(
                    benchmark_returns.mean() / benchmark_vol * math.sqrt(252.0)
                )
                if benchmark_vol > 0
                else None,
                "benchmark_hac_mean_t_5": hac_mean_t(benchmark_returns, lags=5),
                "benchmark_exposure_matched_return_mean": _float_or_none(matched_benchmark.mean()),
                "benchmark_exposure_matched_sharpe": _float_or_none(
                    matched_benchmark.mean() / matched_benchmark_vol * math.sqrt(252.0)
                )
                if matched_benchmark_vol > 0
                else None,
                "benchmark_exposure_matched_hac_mean_t_5": hac_mean_t(matched_benchmark, lags=5),
                "active_return_mean": _float_or_none(active_returns.mean()),
                "relative_nav_vs_exposure_matched_benchmark": relative_nav,
                "active_sharpe": _float_or_none(
                    active_returns.mean() / active_vol * math.sqrt(252.0)
                )
                if active_vol > 0
                else None,
                "active_hac_mean_t_5": hac_mean_t(active_returns, lags=5),
                "max_drawdown": _max_drawdown(returns),
                "hit_take_profit_rate": _float_or_none(group["hit_take_profit_rate"].mean()),
                "avg_trade_return": _float_or_none(group["avg_trade_return"].mean()),
                "open_to_high_mean": _float_or_none(group["open_to_high_mean"].mean()),
                "open_to_close_mean": _float_or_none(group["open_to_close_mean"].mean()),
                "median_daily_capacity_cny": _float_or_none(
                    group["capacity_cny_at_participation"].median()
                ),
                "median_trade_capacity_cny": _float_or_none(
                    group["median_trade_capacity_cny"].median()
                ),
                "avg_raw_rank_used": _float_or_none(group["avg_raw_rank_used"].mean()),
                "max_raw_rank_used": _float_or_none(group["max_raw_rank_used"].max()),
                "blocked_limit_up_open_raw_avg": _float_or_none(
                    group["blocked_limit_up_open_raw"].mean()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(["top_k", "exit_policy"])


def selected_bucket_mix(selected: pd.DataFrame) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for keys, group in selected.groupby(
        ["top_k", "size_bucket", "turnover_bucket"], observed=True, sort=False
    ):
        assert isinstance(keys, tuple)
        top_k, size_bucket, turnover_bucket = keys
        denominator = len(selected.loc[selected["top_k"].eq(top_k)])
        rows.append(
            {
                "top_k": int(str(top_k)),
                "size_bucket": str(size_bucket),
                "turnover_bucket": str(turnover_bucket),
                "rows": len(group),
                "selection_share": len(group) / max(denominator, 1),
                "open_to_high_mean": group["open_to_high"].mean(),
                "open_to_close_mean": group["open_to_close"].mean(),
                "median_next_amount_cny": group["next_amount_cny"].median(),
            }
        )
    return pd.DataFrame(rows).sort_values(["top_k", "size_bucket", "turnover_bucket"])


def write_report(
    outdir: Path,
    *,
    config: BacktestConfig,
    summary: dict[str, Any],
    metrics: pd.DataFrame,
    model_ic: pd.DataFrame,
    bucket_mix: pd.DataFrame,
    feature_importance: pd.DataFrame,
    cost_stress: pd.DataFrame,
    limit_band_mix: pd.DataFrame,
) -> None:
    def table(frame: pd.DataFrame, *, max_rows: int = 40, index: bool = False) -> str:
        if frame.empty:
            return "No rows."
        return "```text\n" + frame.head(max_rows).to_string(index=index) + "\n```"

    lines = [
        "# A-share next-open-to-high execution probe",
        "",
        "This is an OHLC execution approximation, not a promoted strategy run.",
        "",
        "## Config",
        "",
        "```json",
        json.dumps(asdict(config), indent=2, ensure_ascii=False),
        "```",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default),
        "```",
        "",
        "## Execution metrics",
        "",
        table(metrics, index=False),
        "",
        "## Cost stress",
        "",
        table(cost_stress, index=False),
        "",
        "## Signal-day price-limit band mix",
        "",
        table(limit_band_mix, index=False),
        "",
        "## Model IC",
        "",
        table(model_ic.describe(), index=True) if not model_ic.empty else "No IC rows.",
        "",
        "## Selected bucket mix",
        "",
        table(bucket_mix, index=False),
        "",
        "## Model feature importance",
        "",
        table(feature_importance, index=False),
        "",
        "## Caveats",
        "",
        "- Daily OHLC cannot prove intraday queue priority or path ordering.",
        "- Take-profit fills assume the target price is reachable once daily high crosses it.",
        "- Signal-day top-K is frozen before the next open; unfilled names remain cash and are not",
        "  replaced with lower-ranked names using opening information.",
        "- Selection is heavily exposed to signal-day price-limit regimes. Wide-universe active",
        "  return can therefore reflect board/limit-band exposure; use the minute audit's",
        "  within-band benchmark before attributing performance to stock selection.",
        "- Capacity uses full-day amount, so open-window capacity still needs a haircut.",
        "- The reported best policy is selected on the reported test period and is descriptive,",
        "  not a frozen-policy out-of-sample estimate.",
        "- Use --test-start/--test-end with --frozen-top-k and --frozen-take-profit-pct",
        "  for a later non-overlapping fixed-policy evaluation.",
        "",
    ]
    (outdir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _resolve_outdir(args: argparse.Namespace) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.outdir or DEFAULT_OUT_BASE / f"a_share_next_oth_backtest_{timestamp}")
    outdir = outdir.expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


def _build_backtest_config(
    args: argparse.Namespace,
    daily_dir: Path,
    outdir: Path,
) -> BacktestConfig:
    config = BacktestConfig(
        daily_dir=str(daily_dir),
        outdir=str(outdir),
        start_date=args.start_date,
        end_date=args.end_date,
        train_end=args.train_end,
        test_start=args.test_start,
        test_end=args.test_end,
        target=args.target,
        markets=list(args.markets),
        max_symbols=int(args.max_symbols),
        train_sample_per_date=int(args.train_sample_per_date),
        top_k=args.top_k,
        take_profit_pct=args.take_profit_pct,
        frozen_top_k=args.frozen_top_k,
        frozen_take_profit_pct=args.frozen_take_profit_pct,
        include_close_exit=bool(args.include_close_exit),
        participation_rate=float(args.participation_rate),
        entry_slippage_bps=float(args.entry_slippage_bps),
        exit_slippage_bps=float(args.exit_slippage_bps),
        round_trip_cost_bps=float(args.round_trip_cost_bps),
        cost_stress_bps=args.cost_stress_bps,
        block_limit_up_open=bool(args.block_limit_up_open),
        random_state=int(args.random_state),
    )
    (outdir / "config.json").write_text(
        json.dumps(asdict(config), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return config


def _load_execution_panel(
    args: argparse.Namespace,
    daily_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = load_daily_clean(
        daily_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        max_symbols=int(args.max_symbols),
    )
    market_suffix = raw["symbol"].str.rsplit(".", n=1).str[-1].str.upper()
    raw = raw.loc[market_suffix.isin(args.markets)].copy()
    if raw.empty:
        raise ValueError(f"No rows remain after market filter: {args.markets}")
    panel = add_signal_limit_band(add_execution_next_columns(add_labels_and_features(raw)))
    market_dates = sorted(pd.Timestamp(date) for date in raw["trade_date"].dropna().unique())
    market_next_by_date = dict(pairwise(market_dates))
    panel["market_next_date"] = panel["trade_date"].map(market_next_by_date)
    panel = filter_signal_rows(panel)
    panel = add_execution_fields(panel, block_limit_up_open=bool(args.block_limit_up_open))
    return raw, panel


def _split_panel(
    panel: pd.DataFrame,
    args: argparse.Namespace,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eligible = panel.loc[label_available_mask(panel, args.target)].copy()
    train_end = pd.Timestamp(args.train_end)
    label_end = pd.to_datetime(eligible["entry_date"], errors="coerce")
    train = eligible[
        eligible["trade_date"].le(train_end) & label_end.notna() & label_end.le(train_end)
    ].copy()
    test = panel[panel["trade_date"].gt(train_end)].copy()
    if getattr(args, "test_start", None):
        test = test.loc[test["trade_date"].ge(pd.Timestamp(args.test_start))]
    if getattr(args, "test_end", None):
        test = test.loc[test["trade_date"].le(pd.Timestamp(args.test_end))]
    if train.empty or test.empty:
        raise ValueError("Train or test split is empty; adjust date arguments")

    train_sample = sample_train_rows(
        train,
        per_date=int(args.train_sample_per_date),
        random_state=int(args.random_state),
    )
    print(
        "[split] train_rows={:,} sampled={:,} test_rows={:,} train_dates={} test_dates={}".format(
            len(train),
            len(train_sample),
            len(test),
            train["trade_date"].nunique(),
            test["trade_date"].nunique(),
        )
    )
    return train, train_sample, test


def _fit_and_score(
    train_sample: pd.DataFrame,
    test: pd.DataFrame,
    args: argparse.Namespace,
    model_features: list[str],
) -> tuple[Any, pd.DataFrame]:
    model = fit_model(
        train_sample,
        model_features,
        args.target,
        random_state=int(args.random_state),
    )
    test = test.copy()
    test["pred"] = model.predict(test[model_features].fillna(0.0).astype("float32"))
    return model, test


def _select_all_topk(
    test: pd.DataFrame,
    top_k_values: list[int],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_parts: list[pd.DataFrame] = []
    daily_selection_parts: list[pd.DataFrame] = []
    for top_k in top_k_values:
        selected, daily_selection = select_daily_candidates(test, int(top_k))
        selected_parts.append(selected)
        daily_selection_parts.append(daily_selection)
    selected_all = (
        pd.concat(selected_parts, ignore_index=True) if selected_parts else pd.DataFrame()
    )
    daily_selection_all = (
        pd.concat(daily_selection_parts, ignore_index=True)
        if daily_selection_parts
        else pd.DataFrame()
    )
    return selected_all, daily_selection_all


def _apply_exit_policies(
    selected_all: pd.DataFrame,
    args: argparse.Namespace,
) -> pd.DataFrame:
    missing_outcome = selected_all["execution_eligible"] & ~selected_all["outcome_available"]
    if missing_outcome.any():
        missing = selected_all.loc[missing_outcome, ["signal_date", "symbol"]].head(5)
        raise ValueError(
            "Selected executable rows have unavailable outcomes; refusing future-aware "
            f"replacement or silent row loss: {missing.to_dict(orient='records')}"
        )
    executable = selected_all.loc[selected_all["evaluation_eligible"]].copy()
    policies: list[float | None] = list(args.take_profit_pct)
    if args.include_close_exit:
        policies.append(None)
    return pd.concat(
        [
            apply_exit_policy(
                executable,
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


def _write_backtest_outputs(
    outdir: Path,
    *,
    config: BacktestConfig,
    raw: pd.DataFrame,
    panel: pd.DataFrame,
    train: pd.DataFrame,
    train_sample: pd.DataFrame,
    test: pd.DataFrame,
    model: Any,
    model_features: list[str],
    selected_all: pd.DataFrame,
    daily_selection_all: pd.DataFrame,
    trades: pd.DataFrame,
    args: argparse.Namespace,
) -> None:
    daily_returns = aggregate_daily_returns(trades, daily_selection_all)
    benchmark = matched_universe_benchmark(test, args, apply_exit_policy)
    daily_returns = daily_returns.merge(
        benchmark,
        on=["signal_date", "exit_policy"],
        how="left",
        validate="many_to_one",
    )
    daily_returns["selected_invested_weight"] = 1.0 - daily_returns["cash_weight"]
    daily_returns["benchmark_exposure_matched_return"] = (
        daily_returns["benchmark_executed_mean_return"] * daily_returns["selected_invested_weight"]
    )
    daily_returns["active_return"] = (
        daily_returns["portfolio_return"] - daily_returns["benchmark_exposure_matched_return"]
    )
    metrics = summarize_metrics(daily_returns)
    cost_stress = summarize_cost_stress(
        trades,
        args.cost_stress_bps,
        daily_selection_all,
        benchmark,
    )

    model_evaluation = test.loc[label_available_mask(test, args.target)]
    model_ic = _daily_corr_rows(model_evaluation, "pred", args.target)
    feature_importance = pd.DataFrame(
        {
            "feature": model_features,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)
    bucket_mix = selected_bucket_mix(selected_all.loc[selected_all["evaluation_eligible"]])
    limit_band_mix = build_limit_band_mix(test, selected_all)

    summary = build_backtest_summary(
        raw=raw,
        panel=panel,
        train=train,
        train_sample=train_sample,
        test=test,
        model_evaluation=model_evaluation,
        model_ic=model_ic,
        metrics=metrics,
        limit_band_mix=limit_band_mix,
        args=args,
    )

    model_ic.to_csv(outdir / "model_daily_ic.csv", index=False)
    feature_importance.to_csv(outdir / "feature_importance.csv", index=False)
    selected_all.to_csv(outdir / "selected_candidates.csv", index=False)
    write_test_predictions(outdir, test, args.target)
    daily_selection_all.to_csv(outdir / "daily_selection.csv", index=False)
    benchmark.to_csv(outdir / "matched_universe_benchmark.csv", index=False)
    trades.to_csv(outdir / "trade_details.csv", index=False)
    daily_returns.to_csv(outdir / "daily_returns.csv", index=False)
    metrics.to_csv(outdir / "execution_metrics.csv", index=False)
    cost_stress.to_csv(outdir / "cost_stress_metrics.csv", index=False)
    bucket_mix.to_csv(outdir / "selected_bucket_mix.csv", index=False)
    limit_band_mix.to_csv(outdir / "limit_band_mix.csv", index=False)
    (outdir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default) + "\n",
        encoding="utf-8",
    )
    write_report(
        outdir,
        config=config,
        summary=summary,
        metrics=metrics,
        model_ic=model_ic,
        bucket_mix=bucket_mix,
        feature_importance=feature_importance,
        cost_stress=cost_stress,
        limit_band_mix=limit_band_mix,
    )
    print(f"[done] {outdir}")


def run(args: argparse.Namespace) -> Path:
    frozen_fields = (args.frozen_top_k, args.frozen_take_profit_pct)
    if (frozen_fields[0] is None) != (frozen_fields[1] is None):
        raise ValueError("Frozen top-k and take-profit must be specified together")
    daily_dir = Path(args.daily_dir).expanduser().resolve()
    outdir = _resolve_outdir(args)
    config = _build_backtest_config(args, daily_dir, outdir)
    raw, panel = _load_execution_panel(args, daily_dir)
    model_features: list[str] = [str(f"cs_{column}") for column in BASE_FEATURES]
    train, train_sample, test = _split_panel(panel, args)
    model, test = _fit_and_score(train_sample, test, args, model_features)
    selected_all, daily_selection_all = _select_all_topk(test, args.top_k)
    trades = _apply_exit_policies(selected_all, args)
    _write_backtest_outputs(
        outdir,
        config=config,
        raw=raw,
        panel=panel,
        train=train,
        train_sample=train_sample,
        test=test,
        model=model,
        model_features=model_features,
        selected_all=selected_all,
        daily_selection_all=daily_selection_all,
        trades=trades,
        args=args,
    )
    return outdir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-dir", default=str(DEFAULT_DAILY_DIR))
    parser.add_argument("--outdir")
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date")
    parser.add_argument("--train-end", default="2025-12-31")
    parser.add_argument("--test-start")
    parser.add_argument("--test-end")
    parser.add_argument("--target", default="next_open_to_high")
    parser.add_argument(
        "--markets",
        type=_parse_markets,
        default=_parse_markets("SH,SZ"),
        help="Comma-separated suffixes; SH,SZ is the product research universe",
    )
    parser.add_argument("--max-symbols", type=int, default=0, help="0 means all symbols")
    parser.add_argument("--train-sample-per-date", type=int, default=900)
    parser.add_argument("--top-k", type=_parse_top_k, default=_parse_top_k("10,20,30"))
    parser.add_argument(
        "--take-profit-pct",
        type=_parse_pct_list,
        default=_parse_pct_list("0.02,0.03,0.05,0.08"),
    )
    parser.add_argument("--frozen-top-k", type=int)
    parser.add_argument("--frozen-take-profit-pct", type=float)
    parser.add_argument("--include-close-exit", action="store_true", default=True)
    parser.add_argument("--no-include-close-exit", dest="include_close_exit", action="store_false")
    parser.add_argument("--participation-rate", type=float, default=0.05)
    parser.add_argument("--entry-slippage-bps", type=float, default=5.0)
    parser.add_argument("--exit-slippage-bps", type=float, default=5.0)
    parser.add_argument("--round-trip-cost-bps", type=float, default=12.0)
    parser.add_argument(
        "--cost-stress-bps",
        type=_parse_bps_list,
        default=_parse_bps_list("22,50,100,150,200"),
    )
    parser.add_argument("--block-limit-up-open", action="store_true", default=True)
    parser.add_argument(
        "--allow-limit-up-open",
        dest="block_limit_up_open",
        action="store_false",
    )
    parser.add_argument("--random-state", type=int, default=42)
    return parser


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
