"""Shared style factor analysis workflow used by CLI entry points."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from alpha_research.style_factors import VALUE_CLUSTER_COL, compute_factors
from portfolio_backtester.style_factors_backtest import (
    build_factor_returns,
    build_quantile_portfolio_returns,
    compute_factor_correlations,
    compute_summary,
    compute_yearly_breakdown,
    get_rebalance_dates,
)

from .attribution import run_strategy_attribution, run_yearly_strategy_attribution
from .charts import (
    plot_correlation_heatmap,
    plot_cumulative_comparison,
    plot_factor_nav,
    plot_yearly_barchart,
)
from .data import (
    load_cashflow,
    load_data,
    load_fina_indicator,
    load_holder_structure,
    load_moneyflow_ths,
    load_sw_industry_membership,
)
from .report import generate_report


@dataclass(frozen=True)
class StyleFactorArtifacts:
    outdir: Path
    factor_results: dict
    summary: pd.DataFrame
    correlation: pd.DataFrame
    yearly: pd.DataFrame
    attribution: dict | None
    yearly_attribution: pd.DataFrame | None
    metadata: dict[str, Any]


def load_strategy_returns(path: Path | None) -> pd.Series | None:
    if path is None:
        return None
    frame = pd.read_csv(path, parse_dates=[0], index_col=0)
    if frame.empty or len(frame.columns) == 0:
        raise ValueError(f"Strategy CSV has no return columns: {path}")
    return frame.iloc[:, 0]


def _save_factor_outputs(
    outdir: Path,
    factor_results: dict,
    summary: pd.DataFrame,
    corr: pd.DataFrame,
    yearly: pd.DataFrame,
    attribution: dict | None,
    yearly_attribution: pd.DataFrame | None,
    metadata: dict[str, Any],
) -> None:
    summary.to_json(outdir / "factor_summary.json", orient="records", indent=2)
    corr.to_json(outdir / "factor_correlation.json", orient="index", indent=2)
    yearly.to_csv(outdir / "factor_yearly.csv", index=False)
    if attribution:
        (outdir / "strategy_attribution.json").write_text(json.dumps(attribution, indent=2) + "\n")
    if yearly_attribution is not None and not yearly_attribution.empty:
        yearly_attribution.to_csv(outdir / "strategy_attribution_yearly.csv", index=False)
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
    yearly_attribution: pd.DataFrame | None,
    factors: pd.DataFrame,
    daily: pd.DataFrame,
) -> dict[str, Any]:
    industry_coverage = (
        float(factors["industry_l1"].notna().mean())
        if "industry_l1" in factors.columns and not factors.empty
        else 0.0
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "data_root": str(data_root),
        "output": str(outdir),
        "quick": quick,
        "quick_start_date": "2020-01-01" if quick else None,
        "factor_count": len(factor_results),
        "factors": sorted(factor_results),
        "data_start": daily["trade_date"].min().date().isoformat(),
        "data_end": daily["trade_date"].max().date().isoformat(),
        "industry_signal_demeaning": bool(industry_coverage > 0),
        "industry_coverage": round(industry_coverage, 6),
        "rebalance_frequency": "month_end",
        "quantiles": 5,
        "holding_accounting": "fixed_shares_between_rebalances",
        "missing_holding_return": "zero",
        "annual_ret_method": "daily_mean_compounded_252_days_legacy_field",
        "geometric_annual_ret_method": "cumulative_return_compounded_252_over_observations",
        "data_posture": "screen_grade_raw_history_and_legacy_fundamentals",
        "attribution": attribution,
        "yearly_attribution_file": (
            str(outdir / "strategy_attribution_yearly.csv")
            if yearly_attribution is not None and not yearly_attribution.empty
            else None
        ),
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

    start_date = "2020-01-01" if quick else None
    daily, basics = load_data(
        data_root,
        start_date=start_date,
        basics_rebalance_only=True,
    )
    all_dates = pd.DatetimeIndex(sorted(daily["trade_date"].unique()))
    if all_dates.empty:
        raise ValueError("No daily dates available after filtering")
    rebalance_dates = get_rebalance_dates(all_dates)
    fina = load_fina_indicator(data_root)
    cashflow = load_cashflow(data_root)

    # Locally-landed tushare datasets (zero network traffic) for auxiliary
    # factors + PIT SW-L1 industry neutralization.
    moneyflow = load_moneyflow_ths(data_root, start_date=start_date)
    holder = load_holder_structure(data_root, start_date=start_date)
    sw_membership = load_sw_industry_membership(data_root)

    # dv_ttm / ps_ttm come from daily_basic (already loaded); surface as aux.
    basics_extra = (
        basics.loc[
            basics["trade_date"].isin(rebalance_dates),
            ["trade_date", "symbol", "dv_ttm", "ps_ttm"],
        ].copy()
        if {
            "dv_ttm",
            "ps_ttm",
        }
        <= set(basics.columns)
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
        sw_membership=sw_membership if not sw_membership.empty else None,
        rebalance_dates=rebalance_dates,
    )
    if factors.empty:
        raise ValueError("No factor dates available after filtering")
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
    yearly_attribution = run_yearly_strategy_attribution(results, strategy_returns, strategy_name)
    if attribution and "error" in attribution:
        attribution = None
    if yearly_attribution.empty:
        yearly_attribution = None

    metadata = _build_metadata(
        data_root=data_root,
        outdir=outdir,
        quick=quick,
        factor_results=results,
        attribution=attribution,
        yearly_attribution=yearly_attribution,
        factors=factors,
        daily=daily,
    )

    artifacts = _finalize_style_analysis(
        outdir=outdir,
        results=results,
        summary=summary,
        corr=corr,
        yearly=yearly,
        attribution=attribution,
        yearly_attribution=yearly_attribution,
        data_root=data_root,
        quick=quick,
        metadata=metadata,
    )
    _publish_value_cluster_series(outdir, factors, daily, rebalance_dates)
    return artifacts


def _publish_value_cluster_series(
    outdir: Path,
    factors: pd.DataFrame,
    daily: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
) -> None:
    """Write the score-level value-cluster long-short series as an extra artifact.

    The cluster is the equal-weight mean of the four standardized value-group
    z-scores; it feeds the weekly Value report's 口径对照 but stays out of the
    formal 15-factor research set.
    """
    if VALUE_CLUSTER_COL not in factors.columns or not factors[VALUE_CLUSTER_COL].notna().any():
        return
    cluster = build_quantile_portfolio_returns(
        factors,
        daily,
        rebalance_dates,
        {"value_cluster": VALUE_CLUSTER_COL},
        n_quantiles=5,
        requested_quantiles=(1, 5),
        include_universe=False,
    )["value_cluster"]["long_short"]
    if len(cluster):
        cluster.to_csv(outdir / "factor_value_cluster_daily.csv", index=True, header=True)
        print("[workflow] value-cluster composite → factor_value_cluster_daily.csv", flush=True)


def _finalize_style_analysis(
    *,
    outdir: Path,
    results: dict,
    summary: pd.DataFrame,
    corr: pd.DataFrame,
    yearly: pd.DataFrame,
    attribution: dict[str, Any] | None,
    yearly_attribution: pd.DataFrame | None,
    data_root: Path,
    quick: bool,
    metadata: dict[str, Any],
) -> StyleFactorArtifacts:
    plot_factor_nav(results, outdir)
    plot_cumulative_comparison(results, outdir)
    plot_correlation_heatmap(results, outdir)
    plot_yearly_barchart(yearly, outdir)
    generate_report(
        summary,
        corr,
        results,
        outdir,
        attribution,
        yearly,
        yearly_attribution,
        metadata,
    )
    _save_factor_outputs(
        outdir,
        results,
        summary,
        corr,
        yearly,
        attribution,
        yearly_attribution,
        metadata,
    )
    return StyleFactorArtifacts(
        outdir=outdir,
        factor_results=results,
        summary=summary,
        correlation=corr,
        yearly=yearly,
        attribution=attribution,
        yearly_attribution=yearly_attribution,
        metadata=metadata,
    )
