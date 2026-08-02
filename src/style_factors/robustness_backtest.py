"""Constrained style-factor robustness simulation with explicit execution frictions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .factor_backtest import available_factor_names
from .robustness_execution import (
    LegSimulation,
    daily_return_matrix,
    execution_matrices,
    profile_results,
    simulate_leg,
    terminal_event_positions,
)
from .robustness_margin import margin_comparison_frame
from .robustness_results import comparison_frame, diagnostic_row, scenario_rows
from .robustness_types import ConstrainedBacktestArtifacts, RobustnessConfig

__all__ = ["ConstrainedBacktestArtifacts", "RobustnessConfig", "build_constrained_robustness"]


@dataclass(frozen=True)
class _FactorSimulation:
    active_dates: pd.DatetimeIndex
    long_targets: dict[pd.Timestamp, dict[str, float]]
    short_targets: dict[pd.Timestamp, dict[str, float]]
    long_leg: LegSimulation
    short_leg: LegSimulation
    target_diagnostics: dict[str, float]


def _formation_eligibility(
    factors: pd.DataFrame,
    daily_clean: pd.DataFrame,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    *,
    min_listed_days: int,
) -> tuple[pd.DataFrame, dict[str, int]]:
    formation_dates = pd.DatetimeIndex(universe["trade_date"].unique()).normalize()
    formation = daily_clean.loc[
        daily_clean["trade_date"].isin(formation_dates),
        ["trade_date", "symbol", "listed_days", "amount"],
    ]
    universe_keys = universe[["trade_date", "symbol"]].drop_duplicates()
    eligible = factors.merge(universe_keys, on=["trade_date", "symbol"], how="inner")
    eligible = eligible.merge(formation, on=["trade_date", "symbol"], how="left")
    eligible["is_st"] = eligible.set_index(["trade_date", "symbol"]).index.isin(
        st_history.set_index(["trade_date", "symbol"]).index
    )
    diagnostics = {
        "factor_rows_before_universe": len(factors),
        "factor_rows_in_universe": len(eligible),
        "excluded_immature": int(eligible["listed_days"].fillna(-1).lt(min_listed_days).sum()),
        "excluded_st_known_dates": int(eligible["is_st"].sum()),
        "excluded_not_trading_at_formation": int(eligible["amount"].fillna(0).le(0).sum()),
    }
    mask = (
        eligible["listed_days"].fillna(-1).ge(min_listed_days)
        & eligible["amount"].fillna(0).gt(0)
        & ~eligible["is_st"]
    )
    return eligible.loc[mask].copy(), diagnostics


def _next_trading_date(
    formation_date: pd.Timestamp,
    trading_dates: pd.DatetimeIndex,
) -> pd.Timestamp | None:
    position = int(trading_dates.searchsorted(formation_date, side="right"))
    if position >= len(trading_dates):
        return None
    return pd.Timestamp(trading_dates[position]).normalize()


def _ranked_formation_target(
    group: pd.DataFrame,
    *,
    factor_column: str,
    n_quantiles: int,
    short_allowed: set[str] | None = None,
) -> tuple[dict[str, float], dict[str, float], int, int] | None:
    ranked = group.dropna(subset=[factor_column]).sort_values(factor_column).copy()
    if len(ranked) < n_quantiles * 10:
        return None
    ranked["quantile"] = pd.qcut(
        ranked[factor_column],
        n_quantiles,
        labels=False,
        duplicates="drop",
    )
    if ranked["quantile"].nunique() < n_quantiles:
        return None
    long_symbols = ranked.loc[ranked["quantile"].eq(n_quantiles - 1), "symbol"].tolist()
    short_symbols = ranked.loc[ranked["quantile"].eq(0), "symbol"].tolist()
    unrestricted_short_count = len(short_symbols)
    if short_allowed is not None:
        short_symbols = [symbol for symbol in short_symbols if symbol in short_allowed]
    if not long_symbols or not short_symbols:
        return None
    return (
        {symbol: 1.0 / len(long_symbols) for symbol in long_symbols},
        {symbol: 1.0 / len(short_symbols) for symbol in short_symbols},
        len(ranked),
        unrestricted_short_count,
    )


def _active_exposure_dates(
    formation_dates: pd.DatetimeIndex,
    valid_formations: set[pd.Timestamp],
    trading_dates: pd.DatetimeIndex,
) -> pd.DatetimeIndex:
    dates: list[pd.Timestamp] = []
    for index, formation_date in enumerate(formation_dates[:-1]):
        if formation_date not in valid_formations:
            continue
        next_formation = formation_dates[index + 1]
        dates.extend(
            pd.Timestamp(date).normalize()
            for date in trading_dates[
                (trading_dates > formation_date) & (trading_dates <= next_formation)
            ]
        )
    return pd.DatetimeIndex(dates).drop_duplicates()


def _factor_targets(
    eligible: pd.DataFrame,
    trading_dates: pd.DatetimeIndex,
    factor_name: str,
    *,
    n_quantiles: int,
    short_eligibility: dict[pd.Timestamp, set[str]] | None = None,
) -> tuple[
    dict[pd.Timestamp, tuple[dict[str, float], dict[str, float]]],
    pd.DatetimeIndex,
    dict[str, float],
]:
    factor_column = f"factor_{factor_name}_z"
    targets: dict[pd.Timestamp, tuple[dict[str, float], dict[str, float]]] = {}
    formation_dates = pd.DatetimeIndex(sorted(eligible["trade_date"].unique())).normalize()
    for formation_date in formation_dates:
        execution_date = _next_trading_date(formation_date, trading_dates)
        if execution_date is not None:
            targets[execution_date] = ({}, {})
    valid_formations: set[pd.Timestamp] = set()
    eligible_counts: list[int] = []
    long_counts: list[int] = []
    short_counts: list[int] = []
    unrestricted_short_counts: list[int] = []
    for formation_date, group in eligible.groupby("trade_date", sort=True):
        normalized_formation = pd.Timestamp(formation_date).normalize()
        short_allowed = None
        if short_eligibility is not None:
            short_allowed = short_eligibility.get(normalized_formation)
            if short_allowed is None:
                continue
        target = _ranked_formation_target(
            group,
            factor_column=factor_column,
            n_quantiles=n_quantiles,
            short_allowed=short_allowed,
        )
        if target is None:
            continue
        execution_date = _next_trading_date(pd.Timestamp(formation_date), trading_dates)
        if execution_date is None:
            continue
        long_target, short_target, eligible_count, unrestricted_short_count = target
        valid_formations.add(pd.Timestamp(formation_date).normalize())
        targets[execution_date] = (long_target, short_target)
        eligible_counts.append(eligible_count)
        long_counts.append(len(long_target))
        short_counts.append(len(short_target))
        unrestricted_short_counts.append(unrestricted_short_count)
    diagnostics = {
        "rebalance_count": float(len(valid_formations)),
        "mean_eligible": float(np.mean(eligible_counts)) if eligible_counts else 0.0,
        "mean_long_names": float(np.mean(long_counts)) if long_counts else 0.0,
        "mean_short_names": float(np.mean(short_counts)) if short_counts else 0.0,
        "mean_short_qualification_rate": (
            float(np.mean(np.asarray(short_counts) / np.asarray(unrestricted_short_counts)))
            if short_counts
            else 0.0
        ),
    }
    active_dates = _active_exposure_dates(formation_dates, valid_formations, trading_dates)
    return targets, active_dates, diagnostics


def _simulate_factor(
    factor: str,
    eligible: pd.DataFrame,
    returns: pd.DataFrame,
    trading_dates: pd.DatetimeIndex,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray],
    terminal_events: dict[pd.Timestamp, np.ndarray],
    config: RobustnessConfig,
    short_eligibility: dict[pd.Timestamp, set[str]] | None = None,
) -> _FactorSimulation | None:
    targets, active_dates, target_diagnostics = _factor_targets(
        eligible,
        trading_dates,
        factor,
        n_quantiles=config.n_quantiles,
        short_eligibility=short_eligibility,
    )
    if not targets or active_dates.empty:
        return None
    long_targets = {date: pair[0] for date, pair in targets.items()}
    short_targets = {date: pair[1] for date, pair in targets.items()}
    long_leg = simulate_leg(
        returns,
        matrices,
        long_targets,
        terminal_events,
        side="long",
        terminal_return=config.delist_terminal_return,
    )
    short_leg = simulate_leg(
        returns,
        matrices,
        short_targets,
        terminal_events,
        side="short",
        terminal_return=config.delist_terminal_return,
    )
    return _FactorSimulation(
        active_dates=active_dates,
        long_targets=long_targets,
        short_targets=short_targets,
        long_leg=long_leg,
        short_leg=short_leg,
        target_diagnostics=target_diagnostics,
    )


def _all_scenario_rows(
    factor: str,
    simulation: _FactorSimulation,
    returns: pd.DataFrame,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray],
    terminal_events: dict[pd.Timestamp, np.ndarray],
    config: RobustnessConfig,
) -> list[dict[str, Any]]:
    rows = scenario_rows(
        factor,
        simulation.long_leg,
        simulation.short_leg,
        terminal_return=config.delist_terminal_return,
        cost_scenarios=config.cost_scenarios_bps,
        active_dates=simulation.active_dates,
    )
    for terminal_return in config.delist_scenarios:
        if terminal_return == config.delist_terminal_return:
            continue
        long_leg = simulate_leg(
            returns,
            matrices,
            simulation.long_targets,
            terminal_events,
            side="long",
            terminal_return=terminal_return,
        )
        short_leg = simulate_leg(
            returns,
            matrices,
            simulation.short_targets,
            terminal_events,
            side="short",
            terminal_return=terminal_return,
        )
        rows.extend(
            scenario_rows(
                factor,
                long_leg,
                short_leg,
                terminal_return=terminal_return,
                cost_scenarios=(config.transaction_cost_bps,),
                active_dates=simulation.active_dates,
            )
        )
    return rows


def _margin_eligibility_map(
    margin_eligibility: pd.DataFrame | None,
) -> dict[pd.Timestamp, set[str]]:
    if margin_eligibility is None or margin_eligibility.empty:
        return {}
    return {
        pd.Timestamp(date).normalize(): set(group["symbol"].astype(str))
        for date, group in margin_eligibility.groupby("trade_date", sort=True)
    }


def _standard_factor_outputs(
    factor: str,
    simulation: _FactorSimulation,
    returns: pd.DataFrame,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray],
    terminal_events: dict[pd.Timestamp, np.ndarray],
    formation_diagnostics: dict[str, int],
    config: RobustnessConfig,
) -> tuple[dict[str, pd.Series], dict[str, pd.Series], list[dict[str, Any]], dict[str, Any]]:
    gross = profile_results(
        simulation.long_leg,
        simulation.short_leg,
        cost_bps=0.0,
        active_dates=simulation.active_dates,
    )
    net = profile_results(
        simulation.long_leg,
        simulation.short_leg,
        cost_bps=config.transaction_cost_bps,
        active_dates=simulation.active_dates,
    )
    scenarios = _all_scenario_rows(
        factor,
        simulation,
        returns,
        matrices,
        terminal_events,
        config,
    )
    diagnostic = diagnostic_row(factor, simulation, formation_diagnostics)
    diagnostic["profile"] = "constrained_full_history"
    return gross, net, scenarios, diagnostic


def _margin_factor_outputs(
    factor: str,
    eligible: pd.DataFrame,
    returns: pd.DataFrame,
    trading_dates: pd.DatetimeIndex,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray],
    terminal_events: dict[pd.Timestamp, np.ndarray],
    margin_by_date: dict[pd.Timestamp, set[str]],
    formation_diagnostics: dict[str, int],
    config: RobustnessConfig,
) -> tuple[dict[str, pd.Series], dict[str, Any]] | None:
    if not margin_by_date:
        return None
    margin_start = min(margin_by_date)
    simulation = _simulate_factor(
        factor,
        eligible.loc[eligible["trade_date"] >= margin_start],
        returns,
        trading_dates,
        matrices,
        terminal_events,
        config,
        short_eligibility=margin_by_date,
    )
    if simulation is None:
        return None
    result = profile_results(
        simulation.long_leg,
        simulation.short_leg,
        cost_bps=config.transaction_cost_bps,
        active_dates=simulation.active_dates,
    )
    diagnostic = diagnostic_row(factor, simulation, formation_diagnostics)
    diagnostic["profile"] = "margin_qualification_upper_bound"
    return result, diagnostic


def _backtest_context(
    factors: pd.DataFrame,
    daily_clean: pd.DataFrame,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    instruments: pd.DataFrame,
    config: RobustnessConfig,
) -> tuple[
    pd.DataFrame,
    dict[str, int],
    pd.DataFrame,
    pd.DatetimeIndex,
    tuple[np.ndarray, np.ndarray, np.ndarray],
    dict[pd.Timestamp, np.ndarray],
]:
    returns = daily_return_matrix(daily_clean)
    trading_dates = pd.DatetimeIndex(returns.index).normalize()
    matrices = execution_matrices(daily_clean, returns)
    positions = {str(symbol): index for index, symbol in enumerate(returns.columns)}
    terminal_events = terminal_event_positions(instruments, trading_dates, positions)
    eligible, formation_diagnostics = _formation_eligibility(
        factors,
        daily_clean,
        universe,
        st_history,
        min_listed_days=config.min_listed_days,
    )
    return eligible, formation_diagnostics, returns, trading_dates, matrices, terminal_events


def build_constrained_robustness(
    factors: pd.DataFrame,
    daily_clean: pd.DataFrame,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    instruments: pd.DataFrame,
    baseline_results: dict[str, dict[str, pd.Series]],
    margin_eligibility: pd.DataFrame | None = None,
    *,
    config: RobustnessConfig,
) -> ConstrainedBacktestArtifacts:
    eligible, formation_diagnostics, returns, trading_dates, matrices, terminal_events = (
        _backtest_context(
            factors,
            daily_clean,
            universe,
            st_history,
            instruments,
            config,
        )
    )

    gross_results: dict[str, dict[str, pd.Series]] = {}
    net_results: dict[str, dict[str, pd.Series]] = {}
    scenario_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    margin_diagnostic_rows: list[dict[str, Any]] = []
    margin_results: dict[str, dict[str, pd.Series]] = {}
    margin_by_date = _margin_eligibility_map(margin_eligibility)
    for factor in available_factor_names(eligible):
        simulation = _simulate_factor(
            factor,
            eligible,
            returns,
            trading_dates,
            matrices,
            terminal_events,
            config,
        )
        if simulation is None:
            continue
        gross, net, scenarios, diagnostic = _standard_factor_outputs(
            factor,
            simulation,
            returns,
            matrices,
            terminal_events,
            formation_diagnostics,
            config,
        )
        gross_results[factor] = gross
        net_results[factor] = net
        scenario_rows.extend(scenarios)
        diagnostic_rows.append(diagnostic)
        margin_outputs = _margin_factor_outputs(
            factor,
            eligible,
            returns,
            trading_dates,
            matrices,
            terminal_events,
            margin_by_date,
            formation_diagnostics,
            config,
        )
        if margin_outputs is not None:
            margin_results[factor], margin_diagnostic = margin_outputs
            margin_diagnostic_rows.append(margin_diagnostic)

    return ConstrainedBacktestArtifacts(
        gross_results=gross_results,
        net_results=net_results,
        margin_net_results=margin_results,
        comparison=comparison_frame(baseline_results, gross_results, net_results),
        margin_comparison=margin_comparison_frame(net_results, margin_results),
        scenarios=pd.DataFrame(scenario_rows),
        diagnostics=pd.DataFrame(diagnostic_rows),
        margin_diagnostics=pd.DataFrame(margin_diagnostic_rows),
    )
