"""Pre-declared promotion gate for full-history constrained factor evidence."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .robustness_types import RobustnessConfig

CORE_FACTORS = (
    "size",
    "value",
    "momentum",
    "quality",
    "earnings_yield",
    "lowvol",
    "growth",
    "leverage",
    "beta",
    "liquidity",
)
MAX_DRAWDOWN_DEGRADATION_PCT = 10.0
MIN_COVERAGE_RATIO = 0.80
STRESS_COST_BPS = 30.0


def _sign(value: float) -> int:
    if not np.isfinite(value) or abs(value) < 1e-12:
        return 0
    return 1 if value > 0 else -1


def _profile_row(comparison: pd.DataFrame, factor: str, profile: str) -> pd.Series | None:
    match = comparison.loc[comparison["factor"].eq(factor) & comparison["profile"].eq(profile)]
    return None if match.empty else match.iloc[0]


def _stress_row(
    scenarios: pd.DataFrame,
    factor: str,
    *,
    config: RobustnessConfig,
) -> pd.Series | None:
    match = scenarios.loc[
        scenarios["factor"].eq(factor)
        & np.isclose(scenarios["terminal_return"], config.delist_terminal_return)
        & np.isclose(scenarios["cost_bps"], STRESS_COST_BPS)
    ]
    return None if match.empty else match.iloc[0]


def _missing_row(factor: str, reason: str) -> dict[str, Any]:
    return {
        "factor": factor,
        "coverage_pass": False,
        "direction_pass": False,
        "drawdown_pass": False,
        "cost_pass": False,
        "factor_pass": False,
        "failure_reason": reason,
    }


def _factor_gate_row(
    factor: str,
    comparison: pd.DataFrame,
    scenarios: pd.DataFrame,
    *,
    maximum_days: float,
    config: RobustnessConfig,
) -> dict[str, Any]:
    raw = _profile_row(comparison, factor, "raw_gross_matched_window")
    gross = _profile_row(comparison, factor, "constrained_gross")
    net = _profile_row(comparison, factor, "constrained_net")
    stress = _stress_row(scenarios, factor, config=config)
    if raw is None or gross is None or net is None or stress is None:
        return _missing_row(factor, "missing required profile or 30 bps scenario")

    raw_return = float(raw["geometric_annual_ret"])
    gross_return = float(gross["geometric_annual_ret"])
    net_return = float(net["geometric_annual_ret"])
    stress_return = float(stress["geometric_annual_ret"])
    raw_drawdown = float(raw["max_drawdown"])
    net_drawdown = float(net["max_drawdown"])
    coverage_ratio = float(net["days"]) / maximum_days if maximum_days else 0.0
    signs = {_sign(value) for value in (raw_return, gross_return, net_return)}
    direction_pass = len(signs) == 1 and 0 not in signs
    cost_pass = (
        _sign(gross_return) == _sign(net_return) == _sign(stress_return)
        and _sign(gross_return) != 0
    )
    drawdown_degradation = raw_drawdown - net_drawdown
    drawdown_pass = drawdown_degradation <= MAX_DRAWDOWN_DEGRADATION_PCT
    coverage_pass = coverage_ratio >= MIN_COVERAGE_RATIO
    factor_pass = coverage_pass and direction_pass and drawdown_pass and cost_pass
    failures = [
        label
        for label, passed in (
            ("coverage", coverage_pass),
            ("direction", direction_pass),
            ("drawdown", drawdown_pass),
            ("cost", cost_pass),
        )
        if not passed
    ]
    return {
        "factor": factor,
        "days": int(net["days"]),
        "coverage_ratio": coverage_ratio,
        "raw_annual_pct": raw_return,
        "constrained_gross_annual_pct": gross_return,
        "constrained_net_10bps_annual_pct": net_return,
        "constrained_net_30bps_annual_pct": stress_return,
        "raw_max_drawdown_pct": raw_drawdown,
        "constrained_net_max_drawdown_pct": net_drawdown,
        "drawdown_degradation_pct": drawdown_degradation,
        "coverage_pass": coverage_pass,
        "direction_pass": direction_pass,
        "drawdown_pass": drawdown_pass,
        "cost_pass": cost_pass,
        "factor_pass": factor_pass,
        "failure_reason": ",".join(failures),
    }


def evaluate_promotion_gate(
    comparison: pd.DataFrame,
    scenarios: pd.DataFrame,
    *,
    config: RobustnessConfig,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Require all core factors to pass coverage, sign, drawdown and 30 bps checks."""
    raw_days = comparison.loc[
        comparison["profile"].eq("raw_gross_matched_window")
        & comparison["factor"].isin(CORE_FACTORS),
        "days",
    ]
    maximum_days = float(raw_days.max()) if not raw_days.empty else 0.0
    rows = [
        _factor_gate_row(
            factor,
            comparison,
            scenarios,
            maximum_days=maximum_days,
            config=config,
        )
        for factor in CORE_FACTORS
    ]
    frame = pd.DataFrame(rows)
    passed = bool(len(frame) == len(CORE_FACTORS) and frame["factor_pass"].all())
    decision = {
        "schema_version": "style_factor_robustness_promotion_gate.v1",
        "promotion_eligible": passed,
        "decision": "promote" if passed else "hold",
        "core_factors_required": list(CORE_FACTORS),
        "core_factors_passed": int(frame["factor_pass"].sum()),
        "core_factors_failed": int((~frame["factor_pass"]).sum()),
        "criteria": {
            "minimum_matched_coverage_ratio": MIN_COVERAGE_RATIO,
            "direction": "raw/gross, constrained/gross and constrained/net signs agree",
            "maximum_drawdown_degradation_percentage_points": (MAX_DRAWDOWN_DEGRADATION_PCT),
            "cost_stability": "constrained sign survives 10 bps and 30 bps",
            "delist_terminal_return": config.delist_terminal_return,
        },
        "official_latest_action": "eligible_to_update" if passed else "keep_current_latest",
        "main_reports_action": "eligible_to_update" if passed else "keep_current_reports",
    }
    return frame, decision
