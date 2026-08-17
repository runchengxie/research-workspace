"""Data-quality gates for the constrained robustness profile."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _key_checks(data: dict[str, Any]) -> list[tuple[str, Any, str, bool]]:
    return [
        (
            "daily_key_duplicates",
            data["duplicate_daily_keys"],
            "= 0",
            data["duplicate_daily_keys"] == 0,
        ),
        (
            "universe_key_duplicates",
            data["duplicate_universe_keys"],
            "= 0",
            data["duplicate_universe_keys"] == 0,
        ),
        (
            "margin_key_duplicates",
            data["duplicate_margin_keys"],
            "= 0",
            data["duplicate_margin_keys"] == 0,
        ),
        (
            "reported_borrow_activity_key_duplicates",
            data["duplicate_reported_borrow_activity_keys"],
            "= 0",
            data["duplicate_reported_borrow_activity_keys"] == 0,
        ),
        (
            "reported_borrow_activity_date_coverage",
            data["reported_borrow_activity_date_coverage"],
            ">= 95% of margin formation dates",
            data["reported_borrow_activity_date_coverage"] >= 0.95,
        ),
        (
            "pit_netprofit_yoy_coverage",
            data["pit_field_coverage"]["netprofit_yoy"],
            ">= 50%",
            data["pit_field_coverage"]["netprofit_yoy"] >= 0.50,
        ),
        (
            "pit_or_yoy_coverage",
            data["pit_field_coverage"]["or_yoy"],
            ">= 50%",
            data["pit_field_coverage"]["or_yoy"] >= 0.50,
        ),
        (
            "pit_panel_key_duplicates",
            data["duplicate_pit_panel_keys"],
            "= 0",
            data["duplicate_pit_panel_keys"] == 0,
        ),
    ]


def _coverage_checks(data: dict[str, Any]) -> list[tuple[str, Any, str, bool]]:
    return [
        (
            "early_daily_basic_join_rate",
            data["early_daily_basic_join_rate"],
            ">= 99%",
            data["early_daily_basic_join_rate"] >= 0.99,
        ),
        (
            "early_adj_factor_join_rate",
            data["early_adj_factor_join_rate"],
            "= 100%",
            data["early_adj_factor_join_rate"] == 1.0,
        ),
        (
            "early_limit_status_join_rate",
            data["early_limit_status_join_rate"],
            ">= 99%",
            data["early_limit_status_join_rate"] >= 0.99,
        ),
        (
            "universe_daily_join_rate",
            data["universe_daily_join_rate"],
            ">= 99% (formation-date suspensions retained)",
            data["universe_daily_join_rate"] >= 0.99,
        ),
    ]


def _historical_checks(data: dict[str, Any]) -> list[tuple[str, Any, str, bool]]:
    cross_validation = data["st_cross_validation"]
    return [
        (
            "adjustment_bridge_p99_abs_error_pct",
            data["adjustment_bridge_p99_abs_error_pct"],
            "<= 0.10 percentage point",
            data["adjustment_bridge_p99_abs_error_pct"] <= 0.10,
        ),
        (
            "st_reconstruction_precision",
            cross_validation["precision"],
            ">= 99%",
            cross_validation["precision"] >= 0.99,
        ),
        (
            "st_reconstruction_recall",
            cross_validation["recall"],
            ">= 99%",
            cross_validation["recall"] >= 0.99,
        ),
    ]


def data_quality_frame(data: dict[str, Any]) -> pd.DataFrame:
    """Render predeclared source and join checks as machine-readable rows."""
    checks = _key_checks(data) + _coverage_checks(data) + _historical_checks(data)
    return pd.DataFrame(checks, columns=pd.Index(["check", "observed", "threshold", "passed"]))
