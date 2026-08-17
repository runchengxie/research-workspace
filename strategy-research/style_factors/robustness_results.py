"""Result summaries for constrained style-factor robustness simulations."""

from __future__ import annotations

from typing import Any

import pandas as pd

from portfolio_backtester.style_factors_backtest import compute_summary

from .robustness_execution import LegSimulation, profile_results


def comparison_frame(
    baseline_results: dict[str, dict[str, pd.Series]],
    gross_results: dict[str, dict[str, pd.Series]],
    net_results: dict[str, dict[str, pd.Series]],
) -> pd.DataFrame:
    """Summarize baseline and constrained profiles on their common dates."""
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


def scenario_rows(
    factor: str,
    long_leg: LegSimulation,
    short_leg: LegSimulation,
    *,
    terminal_return: float,
    cost_scenarios: tuple[float, ...],
    active_dates: pd.DatetimeIndex,
) -> list[dict[str, Any]]:
    """Summarize one execution simulation across transaction-cost assumptions."""
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
        row.update({"terminal_return": terminal_return, "cost_bps": cost_bps})
        rows.append(row)
    return rows


def diagnostic_row(
    factor: str,
    simulation: Any,
    formation_diagnostics: dict[str, int],
) -> dict[str, Any]:
    """Return execution and formation diagnostics for one factor simulation."""
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
