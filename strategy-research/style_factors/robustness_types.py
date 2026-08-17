"""Shared configuration and output types for constrained robustness analysis."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


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
    margin_net_results: dict[str, dict[str, pd.Series]]
    comparison: pd.DataFrame
    margin_comparison: pd.DataFrame
    scenarios: pd.DataFrame
    diagnostics: pd.DataFrame
    margin_diagnostics: pd.DataFrame
