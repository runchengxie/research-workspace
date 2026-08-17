"""Run alternative-definition and exposure diagnostics for the low-turnover factor."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from portfolio_backtester.style_factors_backtest import get_rebalance_dates

from .data import load_data, load_sw_industry_membership
from .liquidity_backtest import (
    build_liquidity_portfolios,
    compare_baseline_returns,
    daily_liquidity_output,
    summarize_liquidity_portfolios,
)
from .liquidity_report import (
    generate_liquidity_report,
    plot_liquidity_long_only,
    plot_liquidity_quintiles,
    plot_liquidity_signal_nav,
)
from .liquidity_signals import (
    build_liquidity_control_panel,
    build_liquidity_signal_panel,
    liquidity_signal_labels,
    load_turnover_lookbacks,
)


@dataclass(frozen=True)
class LiquidityDiagnosticArtifacts:
    outdir: Path
    summary: pd.DataFrame
    quintiles: pd.DataFrame
    daily: pd.DataFrame
    metadata: dict[str, object]


def _save_outputs(
    artifacts: LiquidityDiagnosticArtifacts,
    portfolios: dict[str, dict[str, object]],
) -> None:
    outdir = artifacts.outdir
    artifacts.summary.to_csv(outdir / "liquidity_diagnostics_summary.csv", index=False)
    artifacts.quintiles.to_csv(outdir / "liquidity_diagnostics_quintiles.csv", index=False)
    artifacts.daily.to_csv(outdir / "liquidity_diagnostics_daily.csv", index=True)
    (outdir / "liquidity_diagnostics_meta.json").write_text(
        json.dumps(artifacts.metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    plot_liquidity_signal_nav(portfolios, outdir)
    plot_liquidity_quintiles(artifacts.summary, outdir)
    plot_liquidity_long_only(artifacts.summary, outdir)
    generate_liquidity_report(artifacts.summary, artifacts.metadata, outdir)


def run_liquidity_factor_diagnostics(
    *,
    data_root: Path,
    outdir: Path,
    quick: bool = False,
    minimum_coverage: float = 0.75,
    baseline_artifacts: Path | None = None,
) -> LiquidityDiagnosticArtifacts:
    outdir.mkdir(parents=True, exist_ok=True)
    start_date = "2020-01-01" if quick else None
    daily, basics = load_data(
        data_root,
        start_date=start_date,
        basics_rebalance_only=True,
    )
    all_dates = pd.DatetimeIndex(sorted(daily["trade_date"].unique()))
    if all_dates.empty:
        raise ValueError("no daily dates are available after filtering")
    formation_dates = get_rebalance_dates(all_dates)
    turnover, turnover_metadata = load_turnover_lookbacks(
        data_root,
        formation_dates,
        minimum_coverage=minimum_coverage,
    )
    sw_membership = load_sw_industry_membership(data_root)
    controls = build_liquidity_control_panel(
        daily,
        basics,
        formation_dates,
        sw_membership=sw_membership if not sw_membership.empty else None,
    )
    signal_panel, signal_diagnostics = build_liquidity_signal_panel(turnover, controls)
    portfolios = build_liquidity_portfolios(signal_panel, daily, formation_dates)
    summary, quintiles = summarize_liquidity_portfolios(portfolios, signal_diagnostics)
    daily_output = daily_liquidity_output(portfolios)
    baseline_tieout = compare_baseline_returns(
        portfolios["turnover_1d"]["long_short"], baseline_artifacts
    )
    if baseline_tieout.get("performed") and not baseline_tieout.get("passed"):
        raise ValueError("single-day turnover diagnostic does not tie out to the supplied baseline")

    metadata: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "data_start": daily["trade_date"].min().date().isoformat(),
        "data_end": daily["trade_date"].max().date().isoformat(),
        "formation_dates": len(formation_dates),
        "formation_start": formation_dates.min().date().isoformat(),
        "formation_end": formation_dates.max().date().isoformat(),
        "quick": quick,
        "minimum_coverage": minimum_coverage,
        "signals": liquidity_signal_labels(),
        "turnover_loader": turnover_metadata,
        "signal_observations": len(signal_panel),
        "industry_coverage": float(signal_panel["industry_l1"].notna().mean()),
        "baseline_tieout": baseline_tieout,
        "portfolio_method": "month_end_equal_weight_fixed_shares",
        "data_posture": "screen_grade_raw_history",
    }
    artifacts = LiquidityDiagnosticArtifacts(
        outdir=outdir,
        summary=summary,
        quintiles=quintiles,
        daily=daily_output,
        metadata=metadata,
    )
    _save_outputs(artifacts, portfolios)
    return artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description="A 股低换手因子定义与暴露诊断")
    parser.add_argument(
        "--data-root",
        default=os.environ.get("DATA_PLATFORM_ROOT"),
        help="数据根目录，缺省时从环境变量 DATA_PLATFORM_ROOT 读取",
    )
    parser.add_argument("--outdir", default="artifacts/liquidity_factor_diagnostics")
    parser.add_argument("--quick", action="store_true", help="仅使用 2020 年以来的数据")
    parser.add_argument(
        "--minimum-coverage",
        type=float,
        default=0.75,
        help="滚动换手率窗口所需的最低有效观察比例",
    )
    parser.add_argument(
        "--baseline-artifacts",
        help="可选的历史风格因子产物目录，用于单日换手率逐日收益对账",
    )
    args = parser.parse_args()
    if not args.data_root:
        raise SystemExit(
            "数据根未提供。请设置环境变量 DATA_PLATFORM_ROOT，"
            "或传入 --data-root /path/to/market-data-platform"
        )

    artifacts = run_liquidity_factor_diagnostics(
        data_root=Path(args.data_root),
        outdir=Path(args.outdir),
        quick=args.quick,
        minimum_coverage=args.minimum_coverage,
        baseline_artifacts=(Path(args.baseline_artifacts) if args.baseline_artifacts else None),
    )
    columns = [
        "variant",
        "long_annual_return",
        "long_excess_annual_return",
        "long_short_annual_return",
        "monotonicity_spearman",
        "mean_size_correlation",
        "mean_lowvol_correlation",
    ]
    print(artifacts.summary[columns].to_string(index=False))
    print(f"\n[OK] 低换手因子诊断写入 {artifacts.outdir}")


if __name__ == "__main__":
    main()
