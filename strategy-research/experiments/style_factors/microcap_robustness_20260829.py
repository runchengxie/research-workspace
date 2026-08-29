"""Run the frozen A-share microcap robustness battery.

This runner produces research evidence only. It does not register a production
strategy, modify targets.json, or interpret registration-regime differences as
causal effects.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pandas as pd

from style_factors.data import load_sw_industry_membership
from style_factors.microcap_capacity import build_microcap_capacity_matrix
from style_factors.microcap_controls import build_variant_liquidity_controls
from style_factors.microcap_robustness import (
    build_hard_eligible_reference_universe,
    build_microcap_daily_returns,
    build_microcap_factor_matrix,
    build_microcap_long_only_matrix,
    build_microcap_regimes,
    build_microcap_universe_variants,
    build_microcap_weighting_matrix,
    build_microcap_yearly,
    write_microcap_artifacts,
)
from style_factors.robustness import _compute_clean_factors
from style_factors.robustness_data import load_robustness_market_data
from style_factors.small_cap_low_turnover import (
    build_candidate_signal_panel,
    build_lagged_turnover_panel,
)

EXCLUSION_PERCENTILES = (0.0, 0.1, 0.2, 0.3)
WEIGHTING_MODES = ("equal", "value")
DEFAULT_CANDIDATES = {
    "small_cap": "signal_small_cap",
    "low_turnover": "signal_low_turnover",
    "low_turnover_residual": "signal_low_turnover_residual",
    "composite": "signal_composite",
    "large_cap_control": "signal_large_cap_control",
}


def build_microcap_run_manifest(
    *,
    data_start: str,
    data_end: str,
    alpha_commit: str,
    portfolio_commit: str,
    minimum_listed_days: int,
    data_fingerprint: str = "unknown",
) -> dict[str, object]:
    """Return the frozen primary research grid used for cache and audit metadata."""
    return {
        "schema_version": 1,
        "data_start": data_start,
        "data_end": data_end,
        "data_fingerprint": data_fingerprint,
        "alpha_commit": alpha_commit,
        "portfolio_commit": portfolio_commit,
        "minimum_listed_days": minimum_listed_days,
        "rebalance_frequency": "monthly",
        "exclusion_percentiles": list(EXCLUSION_PERCENTILES),
        "weighting_modes": list(WEIGHTING_MODES),
        "development_end": "2023-12-31",
        "holdout_start": "2024-01-01",
        "registration_regime_boundaries": ["2019-07-22", "2023-02-17"],
    }


def _metadata_fingerprint(metadata: dict[str, object]) -> str:
    payload = json.dumps(
        metadata,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _git_revision(path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _variant_slug(value: float) -> str:
    return f"p{int(round(value * 100)):02d}"


def _cache_manifest_path(cache_dir: Path) -> Path:
    return cache_dir / "manifest.json"


def _cache_matches(cache_dir: Path, manifest: dict[str, object]) -> bool:
    path = _cache_manifest_path(cache_dir)
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")) == manifest
    except (OSError, ValueError):
        return False


def _write_cache_manifest(cache_dir: Path, manifest: dict[str, object]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    _cache_manifest_path(cache_dir).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_variant_cache(
    cache_dir: Path,
    variants: dict[float, pd.DataFrame],
    factor_panels: dict[float, pd.DataFrame],
) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    for exclusion, frame in variants.items():
        frame.to_parquet(cache_dir / f"variant_{_variant_slug(exclusion)}.parquet", index=False)
    for exclusion, frame in factor_panels.items():
        frame.to_parquet(cache_dir / f"factors_{_variant_slug(exclusion)}.parquet", index=False)


def _load_variant_cache(
    cache_dir: Path,
) -> tuple[dict[float, pd.DataFrame], dict[float, pd.DataFrame]] | None:
    variants: dict[float, pd.DataFrame] = {}
    factors: dict[float, pd.DataFrame] = {}
    for exclusion in EXCLUSION_PERCENTILES:
        variant_path = cache_dir / f"variant_{_variant_slug(exclusion)}.parquet"
        factor_path = cache_dir / f"factors_{_variant_slug(exclusion)}.parquet"
        if not variant_path.exists() or not factor_path.exists():
            return None
        variants[exclusion] = pd.read_parquet(variant_path)
        factors[exclusion] = pd.read_parquet(factor_path)
    return variants, factors


def _checkpoint(frame: pd.DataFrame, outdir: Path, filename: str) -> None:
    directory = outdir / "checkpoints"
    directory.mkdir(parents=True, exist_ok=True)
    frame.to_csv(directory / filename, index=False)


def _candidate_panels(
    market_data,
    variants: dict[float, pd.DataFrame],
    formation_dates: pd.DatetimeIndex,
    *,
    data_root: Path,
) -> dict[float, pd.DataFrame]:
    clean = market_data.daily_clean
    daily = clean[["trade_date", "symbol", "tr_close", "amount"]].rename(
        columns={"tr_close": "close"}
    )
    basics = clean[["trade_date", "symbol", "total_mv"]]
    sw_membership = load_sw_industry_membership(data_root)
    controls = build_variant_liquidity_controls(
        daily,
        basics,
        formation_dates,
        variants,
        sw_membership=sw_membership if not sw_membership.empty else None,
    )
    turnover = build_lagged_turnover_panel(clean, formation_dates)
    return {
        exclusion: build_candidate_signal_panel(control, turnover)
        for exclusion, control in controls.items()
    }


def _buffer_artifact(long_only_matrix: pd.DataFrame) -> pd.DataFrame:
    if long_only_matrix.empty:
        return long_only_matrix.copy()
    columns = [
        "candidate",
        "exclusion_percentile",
        "weighting",
        "buffer_setting",
        "gross_annual_return",
        "net_annual_return",
        "annualized_turnover",
        "cost_drag",
        "net_sharpe",
        "net_max_drawdown",
    ]
    return long_only_matrix[[column for column in columns if column in long_only_matrix]].copy()


def run_microcap_robustness(
    *,
    data_root: Path,
    outdir: Path,
    start_date: str = "2015-01-01",
    end_date: str | None = None,
    minimum_listed_days: int = 180,
    transaction_cost_bps: float = 10.0,
    initial_capital: float = 100_000_000.0,
    cache_dir: Path | None = None,
    resume: bool = False,
) -> Path:
    """Run the frozen microcap robustness study and write stable artifacts."""
    if minimum_listed_days < 0:
        raise ValueError("minimum_listed_days must be non-negative")
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps must be non-negative")
    if initial_capital <= 0:
        raise ValueError("initial_capital must be positive")
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
    if formation_dates.empty:
        raise ValueError("market universe has no formation dates")

    root = _workspace_root()
    actual_end = pd.Timestamp(market.daily_clean["trade_date"].max()).date().isoformat()
    manifest = build_microcap_run_manifest(
        data_start=pd.Timestamp(start_date).date().isoformat(),
        data_end=actual_end,
        data_fingerprint=_metadata_fingerprint(market.metadata),
        alpha_commit=_git_revision(root / "alpha-research"),
        portfolio_commit=_git_revision(root / "portfolio-backtester"),
        minimum_listed_days=minimum_listed_days,
    )
    effective_cache = cache_dir or (outdir / "cache")

    reference, base_diagnostics = build_hard_eligible_reference_universe(
        market.daily_clean,
        market.universe,
        market.st_history,
        formation_dates=formation_dates,
        minimum_listed_days=minimum_listed_days,
    )
    cached = (
        _load_variant_cache(effective_cache)
        if resume and _cache_matches(effective_cache, manifest)
        else None
    )
    if cached is None:
        variants, variant_diagnostics = build_microcap_universe_variants(reference)
        factor_panels = {
            exclusion: _compute_clean_factors(
                market,
                data_root=data_root,
                formation_universe=variant[["trade_date", "symbol"]],
            )
            for exclusion, variant in variants.items()
        }
        _write_variant_cache(effective_cache, variants, factor_panels)
        _write_cache_manifest(effective_cache, manifest)
    else:
        variants, factor_panels = cached
        _, variant_diagnostics = build_microcap_universe_variants(reference)

    universe_diagnostics = variant_diagnostics.merge(
        base_diagnostics,
        on="formation_date",
        how="left",
        validate="many_to_one",
    )
    _checkpoint(universe_diagnostics, outdir, "microcap_universe_diagnostics.csv")

    factor_matrix, factor_results = build_microcap_factor_matrix(
        factor_panels,
        variants,
        daily=market.daily_clean,
        rebalance_dates=formation_dates,
    )
    _checkpoint(factor_matrix, outdir, "microcap_factor_matrix.csv")

    candidate_panels = _candidate_panels(
        market,
        variants,
        formation_dates,
        data_root=data_root,
    )
    long_only_matrix, simulations, target_plans = build_microcap_long_only_matrix(
        candidate_panels,
        variants,
        formation_dates=formation_dates,
        daily_clean=market.daily_clean,
        instruments=market.instruments,
        candidates=DEFAULT_CANDIDATES,
        target_count=40,
        buffered_count=60,
        transaction_cost_bps=transaction_cost_bps,
        initial_capital=initial_capital,
    )
    buffer_matrix = _buffer_artifact(long_only_matrix)
    _checkpoint(buffer_matrix, outdir, "microcap_buffer_matrix.csv")

    daily_returns = build_microcap_daily_returns(
        factor_results,
        simulations,
        transaction_cost_bps=transaction_cost_bps,
    )
    yearly = build_microcap_yearly(daily_returns)
    regimes = build_microcap_regimes(daily_returns)
    capacity = build_microcap_capacity_matrix(
        target_plans,
        market.daily_clean,
        transaction_cost_bps=transaction_cost_bps,
    )
    weighting = build_microcap_weighting_matrix(factor_matrix)
    _checkpoint(capacity, outdir, "microcap_capacity_matrix.csv")

    summary = {
        **manifest,
        "reference_rows": len(reference),
        "factor_matrix_rows": len(factor_matrix),
        "long_only_matrix_rows": len(long_only_matrix),
        "capacity_rows": len(capacity),
        "interpretation": "descriptive robustness and regime association; not causal",
    }
    return write_microcap_artifacts(
        outdir,
        universe_diagnostics=universe_diagnostics,
        factor_matrix=factor_matrix,
        weighting_matrix=weighting,
        buffer_matrix=buffer_matrix,
        capacity_matrix=capacity,
        yearly=yearly,
        regimes=regimes,
        summary=summary,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the A-share microcap robustness battery")
    parser.add_argument("--data-root", default=os.environ.get("DATA_PLATFORM_ROOT"))
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--start-date", default="2015-01-01")
    parser.add_argument("--end-date")
    parser.add_argument("--minimum-listed-days", type=int, default=180)
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--initial-capital", type=float, default=100_000_000.0)
    parser.add_argument("--cache-dir")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.data_root:
        raise SystemExit("--data-root or DATA_PLATFORM_ROOT is required")
    output = run_microcap_robustness(
        data_root=Path(args.data_root).expanduser().resolve(),
        outdir=Path(args.outdir).expanduser().resolve(),
        start_date=args.start_date,
        end_date=args.end_date,
        minimum_listed_days=args.minimum_listed_days,
        transaction_cost_bps=args.transaction_cost_bps,
        initial_capital=args.initial_capital,
        cache_dir=Path(args.cache_dir).expanduser().resolve() if args.cache_dir else None,
        resume=args.resume,
    )
    print(f"[OK] microcap robustness artifacts → {output}")


if __name__ == "__main__":
    main()
