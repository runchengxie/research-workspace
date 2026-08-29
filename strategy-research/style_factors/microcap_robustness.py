"""A-share microcap robustness research helpers.

This module owns research-only universe variants and summary builders. It
reuses the existing style-factor, small-cap, and portfolio-backtester engines;
it does not register a production strategy or alter execution behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from portfolio_backtester.style_factors_backtest import (
    available_factor_names,
    build_quantile_portfolio_returns,
    compute_summary,
)

from .robustness_execution import simulate_leg
from .small_cap_low_turnover import (
    LongOnlySimulation,
    _build_long_only_execution_context,
    build_buffered_targets,
    build_candidate_signal_panel,
    filter_candidate_eligibility,
    map_targets_to_execution_dates,
    summarize_long_only_simulations,
)

MICROCAP_ARTIFACTS = {
    "universe": "microcap_universe_diagnostics.csv",
    "factors": "microcap_factor_matrix.csv",
    "weighting": "microcap_weighting_matrix.csv",
    "buffer": "microcap_buffer_matrix.csv",
    "capacity": "microcap_capacity_matrix.csv",
    "yearly": "microcap_yearly.csv",
    "regimes": "microcap_regimes.csv",
    "summary": "microcap_summary.json",
}


def _require_columns(frame: pd.DataFrame, columns: set[str], *, label: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def build_hard_eligible_reference_universe(
    daily_clean: pd.DataFrame,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    *,
    formation_dates: pd.DatetimeIndex,
    minimum_listed_days: int = 180,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the common formation universe used by every microcap stress arm."""
    _require_columns(
        daily_clean,
        {"trade_date", "symbol", "listed_days", "amount", "total_mv"},
        label="daily_clean",
    )
    dates = pd.DatetimeIndex(formation_dates).normalize().sort_values().unique()
    base = daily_clean.loc[
        pd.to_datetime(daily_clean["trade_date"]).dt.normalize().isin(dates),
        ["trade_date", "symbol", "total_mv"],
    ].drop_duplicates(["trade_date", "symbol"])
    eligible = filter_candidate_eligibility(
        base,
        universe,
        daily_clean,
        st_history,
        minimum_listed_days=minimum_listed_days,
    ).copy()
    eligible["trade_date"] = pd.to_datetime(eligible["trade_date"]).dt.normalize()
    eligible["total_mv"] = pd.to_numeric(eligible["total_mv"], errors="coerce")
    finite = np.isfinite(eligible["total_mv"].to_numpy(dtype=float))
    eligible["invalid_market_cap"] = ~finite | eligible["total_mv"].le(0)

    diagnostics = (
        eligible.groupby("trade_date", as_index=False, sort=True)
        .agg(
            eligible_before_market_cap_filter=("symbol", "size"),
            invalid_market_cap_count=("invalid_market_cap", "sum"),
        )
        .set_index("trade_date")
        .reindex(dates, fill_value=0)
        .rename_axis("formation_date")
        .reset_index()
    )
    diagnostics["eligible_reference"] = (
        diagnostics["eligible_before_market_cap_filter"]
        - diagnostics["invalid_market_cap_count"]
    )

    reference = eligible.loc[
        ~eligible["invalid_market_cap"],
        ["trade_date", "symbol", "total_mv"],
    ].copy()
    reference = reference.sort_values(["trade_date", "symbol"], kind="stable")
    return reference.reset_index(drop=True), diagnostics


def build_microcap_universe_variants(
    reference: pd.DataFrame,
    *,
    market_cap_column: str = "total_mv",
    exclusion_percentiles: tuple[float, ...] = (0.0, 0.1, 0.2, 0.3),
) -> tuple[dict[float, pd.DataFrame], pd.DataFrame]:
    """Build deterministic formation-date market-cap exclusion variants."""
    _require_columns(
        reference,
        {"trade_date", "symbol", market_cap_column},
        label="reference",
    )
    if reference.duplicated(["trade_date", "symbol"]).any():
        raise ValueError("reference contains duplicate trade_date/symbol keys")
    if any(not 0.0 <= value < 1.0 for value in exclusion_percentiles):
        raise ValueError("exclusion percentiles must satisfy 0 <= p < 1")

    work = reference.copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"]).dt.normalize()
    work[market_cap_column] = pd.to_numeric(work[market_cap_column], errors="coerce")
    finite = np.isfinite(work[market_cap_column].to_numpy(dtype=float))
    if not bool((finite & work[market_cap_column].gt(0)).all()):
        raise ValueError("reference market caps must be finite and positive")

    variant_parts: dict[float, list[pd.DataFrame]] = {
        value: [] for value in exclusion_percentiles
    }
    diagnostic_rows: list[dict[str, object]] = []
    for formation_date, group in work.groupby("trade_date", sort=True):
        ranked = group.sort_values([market_cap_column, "symbol"], kind="stable").copy()
        count = len(ranked)
        if count == 0:
            continue
        ranked["market_cap_rank"] = np.arange(1, count + 1, dtype=int)
        ranked["market_cap_percentile"] = ranked["market_cap_rank"] / count
        total_cap = float(ranked[market_cap_column].sum())
        for exclusion in exclusion_percentiles:
            excluded_count = int(np.floor(count * exclusion))
            excluded = ranked.iloc[:excluded_count]
            kept = ranked.iloc[excluded_count:].copy()
            kept["exclusion_percentile"] = float(exclusion)
            variant_parts[exclusion].append(kept)
            diagnostic_rows.append(
                {
                    "formation_date": pd.Timestamp(formation_date),
                    "exclusion_percentile": float(exclusion),
                    "eligible_reference": count,
                    "excluded_count": excluded_count,
                    "eligible_after": len(kept),
                    "market_cap_cutoff": (
                        float(excluded[market_cap_column].max())
                        if excluded_count
                        else np.nan
                    ),
                    "excluded_market_cap_share": (
                        float(excluded[market_cap_column].sum() / total_cap)
                        if excluded_count and total_cap > 0
                        else 0.0
                    ),
                }
            )

    variants: dict[float, pd.DataFrame] = {}
    for exclusion, parts in variant_parts.items():
        if parts:
            variants[exclusion] = pd.concat(parts, ignore_index=True)
        else:
            variants[exclusion] = work.iloc[0:0].assign(
                market_cap_rank=pd.Series(dtype="int64"),
                market_cap_percentile=pd.Series(dtype="float64"),
                exclusion_percentile=pd.Series(dtype="float64"),
            )
    return variants, pd.DataFrame(diagnostic_rows)


def reweight_formation_targets(
    targets: dict[pd.Timestamp, dict[str, float]],
    formation_caps: pd.DataFrame,
    *,
    weighting: str,
) -> dict[pd.Timestamp, dict[str, float]]:
    """Reweight an already-selected symbol set without changing membership."""
    if weighting not in {"equal", "value"}:
        raise ValueError("weighting must be 'equal' or 'value'")
    _require_columns(
        formation_caps,
        {"trade_date", "symbol", "total_mv"},
        label="formation_caps",
    )
    caps = formation_caps[["trade_date", "symbol", "total_mv"]].copy()
    caps["trade_date"] = pd.to_datetime(caps["trade_date"]).dt.normalize()
    caps["symbol"] = caps["symbol"].astype(str)
    if caps.duplicated(["trade_date", "symbol"]).any():
        raise ValueError("formation_caps contains duplicate trade_date/symbol keys")
    cap_lookup = caps.set_index(["trade_date", "symbol"])["total_mv"]

    result: dict[pd.Timestamp, dict[str, float]] = {}
    for date, target in targets.items():
        normalized_date = pd.Timestamp(date).normalize()
        symbols = list(target)
        if not symbols:
            result[normalized_date] = {}
            continue
        if weighting == "equal":
            result[normalized_date] = dict.fromkeys(symbols, 1.0 / len(symbols))
            continue

        values = pd.Series(
            [cap_lookup.get((normalized_date, str(symbol)), np.nan) for symbol in symbols],
            index=symbols,
            dtype=float,
        )
        valid = np.isfinite(values.to_numpy(dtype=float)) & values.gt(0)
        if not bool(valid.all()):
            raise ValueError("selected symbols require finite positive formation market caps")
        result[normalized_date] = (values / values.sum()).to_dict()
    return result


def build_microcap_factor_matrix(
    factor_panels: dict[float, pd.DataFrame],
    formation_caps: dict[float, pd.DataFrame],
    *,
    daily: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
    weighting_modes: tuple[str, ...] = ("equal", "value"),
) -> tuple[
    pd.DataFrame,
    dict[tuple[float, str], dict[str, dict[str, object]]],
]:
    """Evaluate recomputed factor panels under equal and value weights."""
    rows: list[dict[str, object]] = []
    raw_results: dict[tuple[float, str], dict[str, dict[str, object]]] = {}
    for exclusion, panel in factor_panels.items():
        if exclusion not in formation_caps:
            raise ValueError(f"formation caps missing exclusion variant: {exclusion}")
        caps = formation_caps[exclusion][["trade_date", "symbol", "total_mv"]]
        weighted = panel.merge(
            caps,
            on=["trade_date", "symbol"],
            how="left",
            validate="one_to_one",
        )
        signals = {
            name: f"factor_{name}_z" for name in available_factor_names(weighted)
        }
        for weighting in weighting_modes:
            results = build_quantile_portfolio_returns(
                weighted,
                daily,
                rebalance_dates,
                signals,
                n_quantiles=5,
                requested_quantiles=(1, 5),
                include_universe=False,
                weighting=weighting,
                weight_column="total_mv" if weighting == "value" else None,
            )
            raw_results[(float(exclusion), weighting)] = results
            summary_input = {
                name: {
                    "long_short": result["long_short"],
                    "long": result["long"],
                    "short": result["short"],
                }
                for name, result in results.items()
            }
            summary = compute_summary(summary_input)
            for record in summary.to_dict("records"):
                rows.append(
                    {
                        "factor": record["factor"],
                        "exclusion_percentile": float(exclusion),
                        "weighting": weighting,
                        "annual_return": record["annual_ret"],
                        "sharpe": record["sharpe"],
                        "max_drawdown": record["max_drawdown"],
                        "observations": record["days"],
                    }
                )
    return pd.DataFrame(rows), raw_results


def build_candidate_panels_for_variants(
    controls: pd.DataFrame,
    turnover: pd.DataFrame,
    variants: dict[float, pd.DataFrame],
    *,
    turnover_column: str = "turnover_lagged_mean_60d",
    minimum_sample: int = 30,
) -> dict[float, pd.DataFrame]:
    """Recompute candidate cross-sectional scores inside each universe variant."""
    panels: dict[float, pd.DataFrame] = {}
    for exclusion, variant in variants.items():
        keys = variant[["trade_date", "symbol"]].drop_duplicates()
        filtered_controls = controls.merge(
            keys,
            on=["trade_date", "symbol"],
            how="inner",
            validate="one_to_one",
        )
        panels[exclusion] = build_candidate_signal_panel(
            filtered_controls,
            turnover,
            turnover_column=turnover_column,
            minimum_sample=minimum_sample,
        )
    return panels


def _simulate_formation_target_plan(
    *,
    name: str,
    signal_column: str,
    formation_targets: dict[pd.Timestamp, dict[str, float]],
    eligible_rows: int,
    context: object,
    terminal_return: float,
) -> LongOnlySimulation | None:
    execution_targets = map_targets_to_execution_dates(
        formation_targets,
        context.trading_dates,  # type: ignore[attr-defined]
    )
    if not execution_targets:
        return None
    leg = simulate_leg(
        context.return_matrix,  # type: ignore[attr-defined]
        context.matrix_tuple,  # type: ignore[attr-defined]
        execution_targets,
        context.terminal_events,  # type: ignore[attr-defined]
        side="long",
        terminal_return=terminal_return,
        max_trade_weight=context.capacity_matrix,  # type: ignore[attr-defined]
    )
    return LongOnlySimulation(
        name=name,
        signal_column=signal_column,
        targets=execution_targets,
        leg=leg,
        active_dates=context.active_dates,  # type: ignore[attr-defined]
        eligible_rows=eligible_rows,
    )


def build_microcap_long_only_matrix(
    candidate_panels: dict[float, pd.DataFrame],
    formation_caps: dict[float, pd.DataFrame],
    *,
    formation_dates: pd.DatetimeIndex,
    daily_clean: pd.DataFrame,
    instruments: pd.DataFrame,
    candidates: dict[str, str],
    target_count: int,
    buffered_count: int,
    transaction_cost_bps: float,
    initial_capital: float,
    terminal_return: float = -0.50,
) -> tuple[
    pd.DataFrame,
    dict[tuple[str, float, str, str], LongOnlySimulation],
    dict[tuple[str, float, str, str], dict[pd.Timestamp, dict[str, float]]],
]:
    """Compare candidate buffers under EW/VW using one shared execution context."""
    if buffered_count < target_count:
        raise ValueError("buffered_count must be at least target_count")
    context = _build_long_only_execution_context(
        daily_clean,
        instruments,
        formation_dates,
        initial_capital=None,
        participation_rate=None,
        returns=None,
        matrices=None,
    )
    rows: list[dict[str, object]] = []
    simulations: dict[tuple[str, float, str, str], LongOnlySimulation] = {}
    target_plans: dict[
        tuple[str, float, str, str], dict[pd.Timestamp, dict[str, float]]
    ] = {}
    buffer_settings = (("no_buffer", target_count), ("buffered", buffered_count))

    for exclusion, panel in candidate_panels.items():
        if exclusion not in formation_caps:
            raise ValueError(f"formation caps missing exclusion variant: {exclusion}")
        for candidate, signal_column in candidates.items():
            for buffer_name, buffer_count in buffer_settings:
                selected = build_buffered_targets(
                    panel,
                    formation_dates,
                    signal_column=signal_column,
                    target_count=target_count,
                    buffer_count=buffer_count,
                )
                for weighting in ("equal", "value"):
                    targets = reweight_formation_targets(
                        selected,
                        formation_caps[exclusion],
                        weighting=weighting,
                    )
                    key = (candidate, float(exclusion), weighting, buffer_name)
                    target_plans[key] = targets
                    simulation = _simulate_formation_target_plan(
                        name="__microcap_candidate__",
                        signal_column=signal_column,
                        formation_targets=targets,
                        eligible_rows=len(panel),
                        context=context,
                        terminal_return=terminal_return,
                    )
                    if simulation is None:
                        continue
                    simulations[key] = simulation
                    summary, _daily = summarize_long_only_simulations(
                        {"__microcap_candidate__": simulation},
                        transaction_cost_bps=transaction_cost_bps,
                    )
                    if summary.empty:
                        continue
                    record = summary.iloc[0].to_dict()
                    rows.append(
                        {
                            **record,
                            "candidate": candidate,
                            "exclusion_percentile": float(exclusion),
                            "weighting": weighting,
                            "buffer_setting": buffer_name,
                            "initial_capital_reference": initial_capital,
                            "cost_drag": record["gross_annual_return"]
                            - record["net_annual_return"],
                        }
                    )
    return pd.DataFrame(rows), simulations, target_plans


def build_microcap_daily_returns(
    factor_results: dict[tuple[float, str], dict[str, dict[str, object]]],
    long_only_results: dict[tuple[str, float, str, str], LongOnlySimulation],
    *,
    transaction_cost_bps: float,
) -> pd.DataFrame:
    """Normalize factor and candidate daily series into one research table."""
    rows: list[dict[str, object]] = []
    for (exclusion, weighting), results in factor_results.items():
        for name, result in results.items():
            series = result["long_short"]
            if not isinstance(series, pd.Series):
                continue
            for date, value in series.dropna().items():
                rows.append(
                    {
                        "trade_date": pd.Timestamp(date),
                        "source_type": "factor",
                        "name": name,
                        "exclusion_percentile": exclusion,
                        "weighting": weighting,
                        "buffer_setting": "n/a",
                        "return_type": "gross",
                        "return": float(value),
                        "turnover": np.nan,
                    }
                )

    for key, simulation in long_only_results.items():
        candidate, exclusion, weighting, buffer_setting = key
        active = simulation.active_dates
        gross = simulation.leg.returns.loc[simulation.leg.returns.index.isin(active)]
        turnover = simulation.leg.traded_notional.loc[
            simulation.leg.traded_notional.index.isin(active)
        ]
        net = gross - turnover * transaction_cost_bps / 10_000.0
        for return_type, series in (("gross", gross), ("net", net)):
            for date, value in series.dropna().items():
                rows.append(
                    {
                        "trade_date": pd.Timestamp(date),
                        "source_type": "candidate",
                        "name": candidate,
                        "exclusion_percentile": exclusion,
                        "weighting": weighting,
                        "buffer_setting": buffer_setting,
                        "return_type": return_type,
                        "return": float(value),
                        "turnover": float(turnover.get(date, np.nan)),
                    }
                )
    return pd.DataFrame(rows)


def _period_metrics(group: pd.DataFrame) -> dict[str, float | int]:
    values = pd.to_numeric(group["return"], errors="coerce").dropna()
    if values.empty:
        return {
            "observations": 0,
            "period_return": np.nan,
            "annual_return": np.nan,
            "sharpe": np.nan,
            "max_drawdown": np.nan,
            "average_turnover": np.nan,
        }
    cumulative = float((1.0 + values).prod() - 1.0)
    annual = float((1.0 + cumulative) ** (252 / len(values)) - 1.0)
    volatility = float(values.std())
    curve = (1.0 + values).cumprod()
    drawdown = float((curve / curve.cummax() - 1.0).min())
    turnover = pd.to_numeric(group["turnover"], errors="coerce")
    return {
        "observations": len(values),
        "period_return": cumulative * 100.0,
        "annual_return": annual * 100.0,
        "sharpe": (
            float(values.mean() / volatility * np.sqrt(252)) if volatility > 0 else np.nan
        ),
        "max_drawdown": drawdown * 100.0,
        "average_turnover": float(turnover.mean()) if turnover.notna().any() else np.nan,
    }


def _summarize_daily_groups(daily_returns: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for keys, group in daily_returns.groupby(group_columns, dropna=False, sort=True):
        key_values = keys if isinstance(keys, tuple) else (keys,)
        rows.append(
            {
                **dict(zip(group_columns, key_values, strict=True)),
                **_period_metrics(group),
            }
        )
    return pd.DataFrame(rows)


def build_microcap_yearly(daily_returns: pd.DataFrame) -> pd.DataFrame:
    """Summarize normalized microcap return series by calendar year."""
    if daily_returns.empty:
        return pd.DataFrame()
    work = daily_returns.copy()
    work["year"] = pd.to_datetime(work["trade_date"]).dt.year
    groups = [
        "year",
        "source_type",
        "name",
        "exclusion_percentile",
        "weighting",
        "buffer_setting",
        "return_type",
    ]
    return _summarize_daily_groups(work, groups)


def build_microcap_regimes(daily_returns: pd.DataFrame) -> pd.DataFrame:
    """Summarize normalized return series by descriptive registration regime."""
    if daily_returns.empty:
        return pd.DataFrame()
    work = daily_returns.copy()
    work["regime"] = pd.to_datetime(work["trade_date"]).map(assign_registration_regime)
    groups = [
        "regime",
        "source_type",
        "name",
        "exclusion_percentile",
        "weighting",
        "buffer_setting",
        "return_type",
    ]
    return _summarize_daily_groups(work, groups)


def build_microcap_weighting_matrix(factor_matrix: pd.DataFrame) -> pd.DataFrame:
    """Compare factor annual returns under value versus equal weighting."""
    required = {"factor", "exclusion_percentile", "weighting", "annual_return"}
    _require_columns(factor_matrix, required, label="factor_matrix")
    pivot = factor_matrix.pivot_table(
        index=["factor", "exclusion_percentile"],
        columns="weighting",
        values="annual_return",
        aggfunc="first",
    ).reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(
        columns={"equal": "equal_annual_return", "value": "value_annual_return"}
    )
    if "equal_annual_return" not in pivot:
        pivot["equal_annual_return"] = np.nan
    if "value_annual_return" not in pivot:
        pivot["value_annual_return"] = np.nan
    pivot["value_minus_equal_annual_return"] = (
        pivot["value_annual_return"] - pivot["equal_annual_return"]
    )
    return pivot


def assign_registration_regime(date: pd.Timestamp) -> str:
    """Map a date to the pre-registered descriptive registration-regime slice."""
    value = pd.Timestamp(date).normalize()
    if value < pd.Timestamp("2019-07-22"):
        return "pre_registration_pilot"
    if value < pd.Timestamp("2023-02-17"):
        return "registration_pilot"
    return "full_registration"


def write_microcap_artifacts(
    outdir: Path,
    *,
    universe_diagnostics: pd.DataFrame,
    factor_matrix: pd.DataFrame,
    weighting_matrix: pd.DataFrame,
    buffer_matrix: pd.DataFrame,
    capacity_matrix: pd.DataFrame,
    yearly: pd.DataFrame,
    regimes: pd.DataFrame,
    summary: dict[str, object],
) -> Path:
    """Write the stable microcap robustness artifact set."""
    outdir.mkdir(parents=True, exist_ok=True)
    universe_diagnostics.to_csv(outdir / MICROCAP_ARTIFACTS["universe"], index=False)
    factor_matrix.to_csv(outdir / MICROCAP_ARTIFACTS["factors"], index=False)
    weighting_matrix.to_csv(outdir / MICROCAP_ARTIFACTS["weighting"], index=False)
    buffer_matrix.to_csv(outdir / MICROCAP_ARTIFACTS["buffer"], index=False)
    capacity_matrix.to_csv(outdir / MICROCAP_ARTIFACTS["capacity"], index=False)
    yearly.to_csv(outdir / MICROCAP_ARTIFACTS["yearly"], index=False)
    regimes.to_csv(outdir / MICROCAP_ARTIFACTS["regimes"], index=False)
    (outdir / MICROCAP_ARTIFACTS["summary"]).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return outdir


__all__ = [
    "MICROCAP_ARTIFACTS",
    "assign_registration_regime",
    "build_candidate_panels_for_variants",
    "build_hard_eligible_reference_universe",
    "build_microcap_daily_returns",
    "build_microcap_factor_matrix",
    "build_microcap_long_only_matrix",
    "build_microcap_regimes",
    "build_microcap_universe_variants",
    "build_microcap_weighting_matrix",
    "build_microcap_yearly",
    "reweight_formation_targets",
    "write_microcap_artifacts",
]
