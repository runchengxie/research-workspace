"""Shared style factor analysis workflow used by CLI entry points."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .attribution import run_strategy_attribution
from .charts import (
    plot_correlation_heatmap,
    plot_cumulative_comparison,
    plot_factor_nav,
    plot_yearly_barchart,
)
from .data import load_data, load_fina_indicator
from .factor_backtest import (
    build_factor_returns,
    compute_factor_correlations,
    compute_summary,
    compute_yearly_breakdown,
    get_rebalance_dates,
)
from .factor_calc import compute_factors
from .report import generate_report


@dataclass(frozen=True)
class StyleFactorArtifacts:
    outdir: Path
    factor_results: dict
    summary: pd.DataFrame
    correlation: pd.DataFrame
    yearly: pd.DataFrame
    attribution: dict | None
    metadata: dict[str, Any]


def load_strategy_returns(path: Path | None) -> pd.Series | None:
    if path is None:
        return None
    frame = pd.read_csv(path, parse_dates=[0], index_col=0)
    if frame.empty or len(frame.columns) == 0:
        raise ValueError(f"Strategy CSV has no return columns: {path}")
    return frame.iloc[:, 0]


def _filter_quick_sample(
    daily: pd.DataFrame,
    basics: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        daily[daily["trade_date"] >= "2020-01-01"].copy(),
        basics[basics["trade_date"] >= "2020-01-01"].copy(),
    )


def _save_factor_outputs(
    outdir: Path,
    factor_results: dict,
    summary: pd.DataFrame,
    corr: pd.DataFrame,
    yearly: pd.DataFrame,
    metadata: dict[str, Any],
) -> None:
    summary.to_json(outdir / "factor_summary.json", orient="records", indent=2)
    corr.to_json(outdir / "factor_correlation.json", orient="index", indent=2)
    yearly.to_csv(outdir / "factor_yearly.csv", index=False)
    (outdir / "meta.json").write_text(json.dumps(metadata, indent=2) + "\n")
    for name, res in factor_results.items():
        res["long_short"].to_csv(
            outdir / f"factor_{name}_daily.csv",
            index=True,
            header=True,
        )


def _build_metadata(
    *,
    data_root: Path,
    outdir: Path,
    quick: bool,
    factor_results: dict,
    attribution: dict | None,
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "data_root": str(data_root),
        "output": str(outdir),
        "quick": quick,
        "factor_count": len(factor_results),
        "factors": sorted(factor_results),
        "attribution": attribution,
    }


def run_style_factor_analysis(
    *,
    data_root: Path,
    outdir: Path,
    quick: bool = False,
    strategy_csv: Path | None = None,
    strategy_name: str = "strategy",
) -> StyleFactorArtifacts:
    outdir.mkdir(parents=True, exist_ok=True)

    daily, basics = load_data(data_root)
    fina = load_fina_indicator(data_root)
    if quick:
        daily, basics = _filter_quick_sample(daily, basics)

    factors = compute_factors(daily, basics, fina if not fina.empty else None)
    all_dates = pd.DatetimeIndex(sorted(factors["trade_date"].unique()))
    if all_dates.empty:
        raise ValueError("No factor dates available after filtering")

    rebalance_dates = get_rebalance_dates(all_dates)
    print(
        f"[rebalance] {len(rebalance_dates)} dates, "
        f"{rebalance_dates[0].date()} ~ {rebalance_dates[-1].date()}"
    )

    results = build_factor_returns(factors, daily, rebalance_dates)
    summary = compute_summary(results)
    corr = compute_factor_correlations(results)
    yearly = compute_yearly_breakdown(results)

    strategy_returns = load_strategy_returns(strategy_csv)
    attribution = run_strategy_attribution(results, strategy_returns, strategy_name)
    if attribution and "error" in attribution:
        attribution = None

    plot_factor_nav(results, outdir)
    plot_cumulative_comparison(results, outdir)
    plot_correlation_heatmap(results, outdir)
    plot_yearly_barchart(yearly, outdir)
    generate_report(summary, corr, results, outdir, attribution, yearly)

    metadata = _build_metadata(
        data_root=data_root,
        outdir=outdir,
        quick=quick,
        factor_results=results,
        attribution=attribution,
    )
    _save_factor_outputs(outdir, results, summary, corr, yearly, metadata)
    return StyleFactorArtifacts(
        outdir=outdir,
        factor_results=results,
        summary=summary,
        correlation=corr,
        yearly=yearly,
        attribution=attribution,
        metadata=metadata,
    )
