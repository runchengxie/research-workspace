"""Shared primitives for A-share readiness checks."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

READINESS_LEVELS = (
    "baseline_reproducible",
    "complete_pit_research_data",
    "production_strategy_evidence",
    "broker_trading_enabled",
)
BASELINE_ASSETS = (
    "instruments",
    "daily_clean",
    "universe_by_date",
    "universe_symbols",
    "universe_meta",
)
COMPLETE_PIT_ASSETS = (
    "pit_fundamentals",
    "industry_changes",
)
RESEARCH_REPORT_KEYS = (
    "benchmark_ladder_report",
    "cpcv_report",
    "feature_evidence_report",
    "final_oos_or_substitute_report",
    "turnover_cost_report",
    "capacity_report",
    "promotion_gate_report",
)
SIDE_AWARE_RULES = (
    "t_plus_one",
    "st_state",
    "suspension",
    "listing_age",
    "board_lot",
    "board_specific",
    "limit_up_buy",
    "limit_down_sell",
)
PIT_FUNDAMENTALS_RULES = (
    "statement_features_enabled",
    "point_in_time",
    "report_period",
    "disclosure_date",
    "availability_delay",
    "field_mapping",
)
HISTORICAL_INDUSTRY_RULES = (
    "historical_backtest_enabled",
    "historical_membership",
    "effective_date",
)


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Failed to read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload


def _resolve_path(value: object, *, base_dir: Path | None = None) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text).expanduser()
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    return path.resolve()


def _date_token(value: object) -> str | None:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    return digits[:8] if len(digits) >= 8 else None


def _check(
    check_id: str,
    *,
    passed: bool,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": check_id,
        "passed": bool(passed),
        "message": message,
    }
    if details:
        result["details"] = dict(details)
    return result


def _all_pass(checks: list[dict[str, Any]]) -> bool:
    return all(bool(check.get("passed")) for check in checks)


def _status(name: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["id"] for check in checks if not bool(check.get("passed"))]
    return {
        "name": name,
        "passed": not failed,
        "failed_checks": failed,
        "checks": checks,
    }
