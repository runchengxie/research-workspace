"""Constrained style-factor robustness simulation with explicit execution frictions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .factor_backtest import available_factor_names, compute_summary
from .robustness_execution import (
    LegSimulation,
    daily_return_matrix,
    execution_matrices,
    profile_results,
    simulate_leg,
    terminal_event_positions,
)


@dataclass(frozen=True)
class RobustnessConfig:
    min_listed_days: int = 180
    transaction_cost_bps: float = 10.0
    delist_terminal_return: float = -0.50
    cost_scenarios_bps: tuple[float, ...] = (0.0, 10.0, 20.0, 30.0)
    delist_scenarios: tuple[float, ...] = (-0.30, -0.50, -1.00)
    n_quantiles: int = 5


@dataclass(frozen=True)
class ConstrainedBacktestArtifacts:
    gross_results: dict[str, dict[str, pd.Series]]
    net_results: dict[str, dict[str, pd.Series]]
    comparison: pd.DataFrame
    scenarios: pd.DataFrame
    diagnostics: pd.DataFrame


@dataclass(frozen=True)
class _FactorSimulation:
    active_dates: pd.DatetimeIndex
    long_targets: dict[pd.Timestamp, dict[str, float]]
    short_targets: dict[pd.Timestamp, dict[str, float]]
    long_leg: LegSimulation
    short_leg: LegSimulation
    target_diagnostics: dict[str, float]


def load_baseline_factor_results(
    artifacts_dir: Path,
    *,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> dict[str, dict[str, pd.Series]]:
    """Load raw/gross factor returns from a previously generated full run."""
    results: dict[str, dict[str, pd.Series]] = {}
    for path in sorted(artifacts_dir.glob("factor_*_daily.csv")):
        name = path.name.removeprefix("factor_").removesuffix("_daily.csv")
        frame = pd.read_csv(path, parse_dates=["trade_date"])
        if name not in frame.columns:
            continue
        series = frame.set_index("trade_date")[name].astype(float).sort_index()
        series = series.loc[(series.index >= start_date) & (series.index <= end_date)]
        if not series.empty:
            results[name] = {"long_short": series}
    if not results:
        raise ValueError(f"No factor daily CSVs found in baseline artifacts: {artifacts_dir}")
    return results


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
) -> tuple[dict[str, float], dict[str, float], int] | None:
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
    if not long_symbols or not short_symbols:
        return None
    return (
        {symbol: 1.0 / len(long_symbols) for symbol in long_symbols},
        {symbol: 1.0 / len(short_symbols) for symbol in short_symbols},
        len(ranked),
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
    for formation_date, group in eligible.groupby("trade_date", sort=True):
        target = _ranked_formation_target(
            group,
            factor_column=factor_column,
            n_quantiles=n_quantiles,
        )
        if target is None:
            continue
        execution_date = _next_trading_date(pd.Timestamp(formation_date), trading_dates)
        if execution_date is None:
            continue
        long_target, short_target, eligible_count = target
        valid_formations.add(pd.Timestamp(formation_date).normalize())
        targets[execution_date] = (long_target, short_target)
        eligible_counts.append(eligible_count)
        long_counts.append(len(long_target))
        short_counts.append(len(short_target))
    diagnostics = {
        "rebalance_count": float(len(valid_formations)),
        "mean_eligible": float(np.mean(eligible_counts)) if eligible_counts else 0.0,
        "mean_long_names": float(np.mean(long_counts)) if long_counts else 0.0,
        "mean_short_names": float(np.mean(short_counts)) if short_counts else 0.0,
    }
    active_dates = _active_exposure_dates(formation_dates, valid_formations, trading_dates)
    return targets, active_dates, diagnostics


def _comparison_frame(
    baseline_results: dict[str, dict[str, pd.Series]],
    gross_results: dict[str, dict[str, pd.Series]],
    net_results: dict[str, dict[str, pd.Series]],
) -> pd.DataFrame:
    rows = []
    aligned_profiles: dict[str, dict[str, dict[str, pd.Series]]] = {
        "raw_gross_matched_window": {},
        "constrained_gross": {},
        "constrained_net": {},
    }
    raw_profile = aligned_profiles["raw_gross_matched_window"]
    for factor, baseline_result in baseline_results.items():
        if factor not in gross_results or factor not in net_results:
            continue
        baseline = baseline_result["long_short"]
        gross = gross_results[factor]["long_short"]
        net = net_results[factor]["long_short"]
        common = baseline.index.intersection(gross.index).intersection(net.index)
        if common.empty:
            continue
        raw_profile[factor] = {"long_short": baseline.loc[common]}
        aligned_profiles["constrained_gross"][factor] = {"long_short": gross.loc[common]}
        aligned_profiles["constrained_net"][factor] = {"long_short": net.loc[common]}
    for profile, results in aligned_profiles.items():
        summary = compute_summary(results)
        summary.insert(1, "profile", profile)
        rows.append(summary)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def _scenario_rows(
    factor: str,
    long_leg: LegSimulation,
    short_leg: LegSimulation,
    *,
    terminal_return: float,
    cost_scenarios: tuple[float, ...],
    active_dates: pd.DatetimeIndex,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cost_bps in cost_scenarios:
        result = {
            factor: profile_results(
                long_leg,
                short_leg,
                cost_bps=cost_bps,
                active_dates=active_dates,
            )
        }
        summary = compute_summary(result)
        if summary.empty:
            continue
        row = summary.iloc[0].to_dict()
        row.update(
            {
                "terminal_return": terminal_return,
                "cost_bps": cost_bps,
            }
        )
        rows.append(row)
    return rows


def _simulate_factor(
    factor: str,
    eligible: pd.DataFrame,
    returns: pd.DataFrame,
    trading_dates: pd.DatetimeIndex,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray],
    terminal_events: dict[pd.Timestamp, np.ndarray],
    config: RobustnessConfig,
) -> _FactorSimulation | None:
    targets, active_dates, target_diagnostics = _factor_targets(
        eligible,
        trading_dates,
        factor,
        n_quantiles=config.n_quantiles,
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
    rows = _scenario_rows(
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
            _scenario_rows(
                factor,
                long_leg,
                short_leg,
                terminal_return=terminal_return,
                cost_scenarios=(config.transaction_cost_bps,),
                active_dates=simulation.active_dates,
            )
        )
    return rows


def _diagnostic_row(
    factor: str,
    simulation: _FactorSimulation,
    formation_diagnostics: dict[str, int],
) -> dict[str, Any]:
    return {
        "factor": factor,
        **formation_diagnostics,
        **simulation.target_diagnostics,
        "long_traded_notional": float(simulation.long_leg.traded_notional.sum()),
        "short_traded_notional": float(simulation.short_leg.traded_notional.sum()),
        "long_blocked_entry_days": simulation.long_leg.blocked_entry_days,
        "long_blocked_exit_days": simulation.long_leg.blocked_exit_days,
        "short_blocked_entry_days": simulation.short_leg.blocked_entry_days,
        "short_blocked_exit_days": simulation.short_leg.blocked_exit_days,
        "long_terminal_events": simulation.long_leg.terminal_events,
        "short_terminal_events": simulation.short_leg.terminal_events,
    }


def build_constrained_robustness(
    factors: pd.DataFrame,
    daily_clean: pd.DataFrame,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    instruments: pd.DataFrame,
    baseline_results: dict[str, dict[str, pd.Series]],
    *,
    config: RobustnessConfig,
) -> ConstrainedBacktestArtifacts:
    """Run matched-window constrained gross/net profiles and cost/delist scenarios."""
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

    gross_results: dict[str, dict[str, pd.Series]] = {}
    net_results: dict[str, dict[str, pd.Series]] = {}
    scenario_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
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
        gross_results[factor] = profile_results(
            simulation.long_leg,
            simulation.short_leg,
            cost_bps=0.0,
            active_dates=simulation.active_dates,
        )
        net_results[factor] = profile_results(
            simulation.long_leg,
            simulation.short_leg,
            cost_bps=config.transaction_cost_bps,
            active_dates=simulation.active_dates,
        )
        scenario_rows.extend(
            _all_scenario_rows(
                factor,
                simulation,
                returns,
                matrices,
                terminal_events,
                config,
            )
        )
        diagnostic_rows.append(_diagnostic_row(factor, simulation, formation_diagnostics))

    return ConstrainedBacktestArtifacts(
        gross_results=gross_results,
        net_results=net_results,
        comparison=_comparison_frame(baseline_results, gross_results, net_results),
        scenarios=pd.DataFrame(scenario_rows),
        diagnostics=pd.DataFrame(diagnostic_rows),
    )
