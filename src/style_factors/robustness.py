"""CLI and workflow for the 2015–2026 constrained style-factor appendix."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from .data import (
    load_cashflow,
    load_fina_indicator,
    load_holder_structure,
    load_moneyflow_ths,
    load_sw_industry_membership,
)
from .factor_calc import compute_factors
from .robustness_backtest import (
    RobustnessConfig,
    build_constrained_robustness,
    load_baseline_factor_results,
)
from .robustness_data import RobustnessMarketData, load_robustness_market_data
from .robustness_report import write_robustness_artifacts


def _compute_clean_factors(
    market_data: RobustnessMarketData,
    *,
    data_root: Path,
) -> pd.DataFrame:
    clean = market_data.daily_clean
    rebalance_dates = pd.DatetimeIndex(market_data.universe["trade_date"].unique()).normalize()
    data_start = clean["trade_date"].min()
    data_end = clean["trade_date"].max()
    fina = load_fina_indicator(data_root, end_date=data_end)
    cashflow = load_cashflow(data_root, end_date=data_end)
    moneyflow = load_moneyflow_ths(
        data_root,
        start_date=data_start,
        end_date=data_end,
    )
    holder = load_holder_structure(
        data_root,
        start_date=data_start,
        end_date=data_end,
    )
    sw_membership = load_sw_industry_membership(data_root)
    basics_extra = clean.loc[
        clean["trade_date"].isin(rebalance_dates),
        ["trade_date", "symbol", "dv_ttm", "ps_ttm"],
    ].copy()
    aux = {
        "moneyflow_ths": moneyflow if not moneyflow.empty else None,
        "holder_structure": holder if not holder.empty else None,
        "daily_basic_extra": basics_extra,
    }
    return compute_factors(
        clean,
        clean,
        fina if not fina.empty else None,
        cashflow if not cashflow.empty else None,
        aux=aux,
        sw_membership=sw_membership if not sw_membership.empty else None,
        rebalance_dates=rebalance_dates,
    )


def run_robustness_analysis(
    *,
    data_root: Path,
    baseline_artifacts: Path,
    outdir: Path,
    start_date: str = "2015-01-01",
    end_date: str | None = None,
    config: RobustnessConfig | None = None,
) -> Path:
    config = config or RobustnessConfig()
    market_data = load_robustness_market_data(
        data_root,
        start_date=start_date,
        end_date=end_date,
    )
    factors = _compute_clean_factors(market_data, data_root=data_root)
    trading_dates = pd.DatetimeIndex(market_data.daily_clean["trade_date"].unique()).sort_values()
    first_formation = market_data.universe["trade_date"].min()
    first_execution_position = int(trading_dates.searchsorted(first_formation, side="right"))
    if first_execution_position >= len(trading_dates):
        raise ValueError("No daily_clean trading date follows the first universe formation date")
    analysis_start = pd.Timestamp(trading_dates[first_execution_position])
    analysis_end = pd.Timestamp(trading_dates[-1])
    baseline_results = load_baseline_factor_results(
        baseline_artifacts,
        start_date=analysis_start,
        end_date=analysis_end,
    )
    artifacts = build_constrained_robustness(
        factors,
        market_data.daily_clean,
        market_data.universe,
        market_data.st_history,
        market_data.instruments,
        baseline_results,
        config=config,
    )
    write_robustness_artifacts(
        artifacts,
        outdir=outdir,
        data_metadata=market_data.metadata,
        config=config,
        baseline_artifacts=baseline_artifacts,
    )
    return outdir


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the 2015–2026 constrained style-factor robustness appendix"
    )
    parser.add_argument(
        "--data-root",
        default=os.environ.get("DATA_PLATFORM_ROOT"),
        help="market-data-platform data root; defaults to DATA_PLATFORM_ROOT",
    )
    parser.add_argument(
        "--baseline-artifacts",
        required=True,
        help="existing full raw/gross style-factor artifact directory",
    )
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--start-date", default="2015-01-01")
    parser.add_argument("--end-date")
    parser.add_argument("--min-listed-days", type=int, default=180)
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--delist-terminal-return", type=float, default=-0.50)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.data_root:
        raise SystemExit("--data-root or DATA_PLATFORM_ROOT is required")
    if args.min_listed_days < 0:
        raise SystemExit("--min-listed-days must be non-negative")
    if args.transaction_cost_bps < 0:
        raise SystemExit("--transaction-cost-bps must be non-negative")
    if not -1.0 <= args.delist_terminal_return <= 0.0:
        raise SystemExit("--delist-terminal-return must be between -1 and 0")
    output = run_robustness_analysis(
        data_root=Path(args.data_root).expanduser().resolve(),
        baseline_artifacts=Path(args.baseline_artifacts).expanduser().resolve(),
        outdir=Path(args.outdir).expanduser().resolve(),
        start_date=args.start_date,
        end_date=args.end_date,
        config=RobustnessConfig(
            min_listed_days=args.min_listed_days,
            transaction_cost_bps=args.transaction_cost_bps,
            delist_terminal_return=args.delist_terminal_return,
        ),
    )
    print(f"[OK] constrained robustness artifacts → {output}")


if __name__ == "__main__":
    main()
