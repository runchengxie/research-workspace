"""Run the frozen microcap characteristic-decomposition study."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from style_factors.microcap_characteristics import build_microcap_characteristics
from style_factors.microcap_inference import (
    build_microcap_decomposition_panel,
    build_microcap_double_sorts,
    run_microcap_cross_sectional_regressions,
    summarize_cross_sectional_coefficients,
)
from style_factors.microcap_robustness import (
    build_hard_eligible_reference_universe,
    build_microcap_universe_variants,
)
from style_factors.robustness import _compute_clean_factors
from style_factors.robustness_data import load_robustness_market_data
from style_factors.robustness_execution import daily_return_matrix
from style_factors.small_cap_low_turnover import build_lagged_turnover_panel

ARTIFACTS = {
    "characteristics": "microcap_characteristics.csv",
    "double_sorts": "microcap_double_sorts.csv",
    "coefficients": "microcap_cross_sectional_coefficients.csv",
    "coefficient_summary": "microcap_coefficient_summary.csv",
    "summary": "microcap_decomposition_summary.json",
}


def build_decomposition_manifest(*, data_end: str) -> dict[str, object]:
    """Return the frozen primary mechanism specification."""
    return {
        "schema_version": 1,
        "data_end": data_end,
        "development_start": "2015-01-01",
        "development_end": "2023-12-31",
        "holdout_start": "2024-01-01",
        "illiquidity": {"window": 60, "min_observations": 45},
        "max": {"window": 21, "min_observations": 15},
        "ivol": {"window": 60, "min_observations": 40},
        "turnover": {"window": 60, "min_observations": 45},
        "hac_maxlags": 3,
        "exclusion_percentiles": [0.0, 0.1, 0.2, 0.3],
        "interpretation": "conditional predictive association; not structural causality",
    }


def _filter_to_variant(frame: pd.DataFrame, variant: pd.DataFrame) -> pd.DataFrame:
    keys = variant[["trade_date", "symbol"]].copy()
    keys["trade_date"] = pd.to_datetime(keys["trade_date"]).dt.normalize()
    work = frame.copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"]).dt.normalize()
    return work.merge(
        keys,
        on=["trade_date", "symbol"],
        how="inner",
        validate="one_to_one",
    )


def _write_artifacts(
    outdir: Path,
    *,
    characteristics: pd.DataFrame,
    double_sorts: pd.DataFrame,
    coefficients: pd.DataFrame,
    coefficient_summary: pd.DataFrame,
    summary: dict[str, object],
) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    characteristics.to_csv(outdir / ARTIFACTS["characteristics"], index=False)
    double_sorts.to_csv(outdir / ARTIFACTS["double_sorts"], index=False)
    coefficients.to_csv(outdir / ARTIFACTS["coefficients"], index=False)
    coefficient_summary.to_csv(outdir / ARTIFACTS["coefficient_summary"], index=False)
    (outdir / ARTIFACTS["summary"]).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return outdir


def run_microcap_characteristic_decomposition(
    *,
    data_root: Path,
    outdir: Path,
    start_date: str = "2015-01-01",
    end_date: str | None = None,
    minimum_listed_days: int = 180,
    hac_maxlags: int = 3,
) -> Path:
    """Run characteristics, double sorts, and monthly cross-sectional inference."""
    if minimum_listed_days < 0:
        raise ValueError("minimum_listed_days must be non-negative")
    if hac_maxlags < 0:
        raise ValueError("hac_maxlags must be non-negative")
    if end_date is not None and pd.Timestamp(start_date) > pd.Timestamp(end_date):
        raise ValueError("start_date must not be after end_date")

    market = load_robustness_market_data(
        data_root,
        start_date=start_date,
        end_date=end_date,
    )
    formation_dates = pd.DatetimeIndex(
        sorted(pd.to_datetime(market.universe["trade_date"]).dt.normalize().unique())
    )
    reference, universe_diagnostics = build_hard_eligible_reference_universe(
        market.daily_clean,
        market.universe,
        market.st_history,
        formation_dates=formation_dates,
        minimum_listed_days=minimum_listed_days,
    )
    variants, exclusion_diagnostics = build_microcap_universe_variants(reference)

    returns = daily_return_matrix(market.daily_clean)
    base_characteristics = build_microcap_characteristics(
        market.daily_clean,
        formation_dates,
        market_return=returns.mean(axis=1),
    )
    turnover = build_lagged_turnover_panel(
        market.daily_clean,
        formation_dates,
        window=60,
        minimum_observations=45,
    )

    characteristic_rows: list[pd.DataFrame] = []
    sort_rows: list[pd.DataFrame] = []
    coefficient_rows: list[pd.DataFrame] = []
    coefficient_summary_rows: list[pd.DataFrame] = []
    panel_diagnostics: list[pd.DataFrame] = []

    for exclusion, variant in variants.items():
        factor_panel = _compute_clean_factors(
            market,
            data_root=data_root,
            formation_universe=variant[["trade_date", "symbol"]],
        )
        if "factor_quality" not in factor_panel.columns:
            raise ValueError("factor_quality is unavailable for the frozen decomposition specification")

        characteristics = _filter_to_variant(base_characteristics, variant)
        characteristics.insert(2, "exclusion_percentile", float(exclusion))
        characteristic_rows.append(characteristics)
        panel, diagnostics = build_microcap_decomposition_panel(
            characteristics.drop(columns="exclusion_percentile"),
            _filter_to_variant(turnover, variant),
            factor_panel[["trade_date", "symbol", "factor_quality"]],
        )
        diagnostics.insert(1, "exclusion_percentile", float(exclusion))
        panel_diagnostics.append(diagnostics)

        double_sorts = build_microcap_double_sorts(
            panel,
            returns,
            formation_dates=formation_dates,
        )
        double_sorts.insert(1, "exclusion_percentile", float(exclusion))
        sort_rows.append(double_sorts)

        coefficients, regression_diagnostics = run_microcap_cross_sectional_regressions(
            panel,
            returns,
            formation_dates=formation_dates,
        )
        coefficients.insert(1, "exclusion_percentile", float(exclusion))
        regression_diagnostics.insert(1, "exclusion_percentile", float(exclusion))
        coefficient_rows.append(coefficients)
        panel_diagnostics.append(regression_diagnostics)

        coefficient_summary = summarize_cross_sectional_coefficients(
            coefficients.drop(columns="exclusion_percentile"),
            hac_maxlags=hac_maxlags,
        )
        coefficient_summary.insert(1, "exclusion_percentile", float(exclusion))
        coefficient_summary_rows.append(coefficient_summary)

    characteristics_out = pd.concat(characteristic_rows, ignore_index=True)
    double_sorts_out = pd.concat(sort_rows, ignore_index=True)
    coefficients_out = pd.concat(coefficient_rows, ignore_index=True)
    coefficient_summary_out = pd.concat(coefficient_summary_rows, ignore_index=True)
    actual_end = pd.Timestamp(market.daily_clean["trade_date"].max()).date().isoformat()
    summary = {
        **build_decomposition_manifest(data_end=actual_end),
        "minimum_listed_days": minimum_listed_days,
        "universe_diagnostics_rows": len(universe_diagnostics),
        "exclusion_diagnostics_rows": len(exclusion_diagnostics),
        "panel_diagnostics": [
            frame.to_dict(orient="records") for frame in panel_diagnostics
        ],
    }
    return _write_artifacts(
        outdir,
        characteristics=characteristics_out,
        double_sorts=double_sorts_out,
        coefficients=coefficients_out,
        coefficient_summary=coefficient_summary_out,
        summary=summary,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the A-share microcap characteristic-decomposition study"
    )
    parser.add_argument("--data-root", default=os.environ.get("DATA_PLATFORM_ROOT"))
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--start-date", default="2015-01-01")
    parser.add_argument("--end-date")
    parser.add_argument("--minimum-listed-days", type=int, default=180)
    parser.add_argument("--hac-maxlags", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.data_root:
        raise SystemExit("--data-root or DATA_PLATFORM_ROOT is required")
    output = run_microcap_characteristic_decomposition(
        data_root=Path(args.data_root).expanduser().resolve(),
        outdir=Path(args.outdir).expanduser().resolve(),
        start_date=args.start_date,
        end_date=args.end_date,
        minimum_listed_days=args.minimum_listed_days,
        hac_maxlags=args.hac_maxlags,
    )
    print(f"[OK] microcap characteristic-decomposition artifacts → {output}")


if __name__ == "__main__":
    main()
