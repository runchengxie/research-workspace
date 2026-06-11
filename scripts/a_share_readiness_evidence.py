"""Evidence aggregation for A-share readiness reports."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from a_share_readiness_common import (
    COMPLETE_PIT_ASSETS,
    HISTORICAL_INDUSTRY_RULES,
    PIT_FUNDAMENTALS_RULES,
    READINESS_LEVELS,
    RESEARCH_REPORT_KEYS,
    SIDE_AWARE_RULES,
    _all_pass,
    _check,
    _date_token,
    _mapping,
    _read_json,
    _resolve_path,
    _status,
)
from a_share_readiness_contract import _contract_checks, _registry_check


def _load_evidence_manifest(path: Path | None) -> tuple[dict[str, Any], Path | None]:
    if path is None:
        return {}, None
    return _read_json(path), path.parent


def _evidence_json(
    evidence: Mapping[str, Any],
    key: str,
    *,
    base_dir: Path | None,
) -> tuple[Path | None, dict[str, Any] | None, str | None]:
    path = _resolve_path(evidence.get(key), base_dir=base_dir)
    if path is None:
        return None, None, f"{key} is not configured"
    if not path.is_file():
        return path, None, f"{key} does not exist: {path}"
    try:
        return path, _read_json(path), None
    except ValueError as exc:
        return path, None, str(exc)


def _validation_check(
    evidence: Mapping[str, Any],
    key: str,
    *,
    base_dir: Path | None,
) -> dict[str, Any]:
    path, payload, error = _evidence_json(evidence, key, base_dir=base_dir)
    passed = payload is not None and str(payload.get("status") or "").lower() == "passed"
    details = {"path": str(path)} if path else {}
    if payload is not None:
        details["status"] = payload.get("status")
        details["totals"] = payload.get("totals")
    return _check(
        key,
        passed=passed,
        message=error or ("validation passed" if passed else "validation report did not pass"),
        details=details,
    )


def _run_output_check(
    evidence: Mapping[str, Any],
    *,
    base_dir: Path | None,
) -> dict[str, Any]:
    run_dir = _resolve_path(evidence.get("research_run_dir"), base_dir=base_dir)
    if run_dir is None or not run_dir.is_dir():
        return _check(
            "research_run_outputs",
            passed=False,
            message=f"Research run directory is missing: {run_dir}",
        )
    required = ("summary.json", "config.used.yml", "inputs.lock.json")
    missing = [filename for filename in required if not (run_dir / filename).is_file()]
    positions = sorted(path.name for path in run_dir.glob("positions_current*.csv"))
    if not positions:
        missing.append("positions_current*.csv")
    return _check(
        "research_run_outputs",
        passed=not missing,
        message=(
            "research run outputs are present"
            if not missing
            else "research run outputs are incomplete"
        ),
        details={"run_dir": str(run_dir), "missing": missing, "positions": positions},
    )


def _targets_check(
    evidence: Mapping[str, Any],
    *,
    base_dir: Path | None,
) -> dict[str, Any]:
    targets_path = _resolve_path(evidence.get("targets_file"), base_dir=base_dir)
    lineage_path = _resolve_path(evidence.get("targets_lineage_file"), base_dir=base_dir)
    details = {
        "targets_file": str(targets_path) if targets_path else None,
        "targets_lineage_file": str(lineage_path) if lineage_path else None,
    }
    if targets_path is None or not targets_path.is_file():
        return _check(
            "targets_lineage",
            passed=False,
            message="targets_file is missing",
            details=details,
        )
    if lineage_path is None or not lineage_path.is_file():
        return _check(
            "targets_lineage",
            passed=False,
            message="targets lineage file is missing",
            details=details,
        )
    try:
        targets = _read_json(targets_path)
        lineage = _read_json(lineage_path)
    except ValueError as exc:
        return _check("targets_lineage", passed=False, message=str(exc), details=details)
    rows = targets.get("targets")
    valid_targets = isinstance(rows, list) and bool(rows)
    lineage_valid = bool(lineage)
    details["targets"] = len(rows) if isinstance(rows, list) else 0
    return _check(
        "targets_lineage",
        passed=valid_targets and lineage_valid,
        message=(
            "targets and lineage are present"
            if valid_targets and lineage_valid
            else "targets array or lineage payload is empty"
        ),
        details=details,
    )


def _qexec_check(
    evidence: Mapping[str, Any],
    *,
    base_dir: Path | None,
) -> dict[str, Any]:
    path, payload, error = _evidence_json(evidence, "qexec_dry_run_report", base_dir=base_dir)
    details = {"path": str(path)} if path else {}
    if payload is not None:
        details.update(
            {
                "status": payload.get("status"),
                "dry_run": payload.get("dry_run"),
                "execute": payload.get("execute"),
                "market": payload.get("market"),
            }
        )
    passed = (
        payload is not None
        and str(payload.get("status") or "").lower() == "passed"
        and payload.get("dry_run") is True
        and payload.get("execute") is not True
        and str(payload.get("market") or "").upper() == "CN"
    )
    return _check(
        "qexec_cn_dry_run",
        passed=passed,
        message=error
        or ("CN dry-run evidence passed" if passed else "CN dry-run evidence is invalid"),
        details=details,
    )


def _window_check(contract_state: Mapping[str, Any], profile: Mapping[str, Any]) -> dict[str, Any]:
    effective_start = _date_token(contract_state.get("effective_start_date"))
    configured_start = _date_token(profile.get("configured_start_date"))
    passed = bool(effective_start and configured_start and configured_start >= effective_start)
    return _check(
        "research_window",
        passed=passed,
        message=(
            "configured research window is covered by required assets"
            if passed
            else "configured research start date is missing or predates required asset coverage"
        ),
        details={
            "configured_start_date": configured_start,
            "effective_start_date": effective_start,
            "effective_end_date": contract_state.get("effective_end_date"),
        },
    )


def _contract_asset_checks(
    contract_state: Mapping[str, Any],
    asset_keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    assets = _mapping(contract_state.get("assets"))
    checks: list[dict[str, Any]] = []
    for asset_key in asset_keys:
        asset = _mapping(assets.get(asset_key))
        passed = (
            bool(asset.get("exists"))
            and bool(asset.get("manifest_path"))
            and str(asset.get("manifest_status") or "") == "completed"
        )
        checks.append(
            _check(
                f"asset:{asset_key}",
                passed=passed,
                message=(
                    f"{asset_key} canonical asset and completed manifest are present"
                    if passed
                    else f"{asset_key} canonical asset or completed manifest is missing"
                ),
                details=asset,
            )
        )
    return checks


def _profile_checks(
    profile: Mapping[str, Any],
    *,
    require_complete: bool = False,
) -> list[dict[str, Any]]:
    universe = _mapping(profile.get("universe"))
    fundamentals = _mapping(profile.get("fundamentals"))
    industry = _mapping(profile.get("industry"))
    trading = _mapping(profile.get("trading_rules"))

    universe_passed = (
        str(universe.get("mode") or "") in {"by_date", "pit"}
        and universe.get("point_in_time") is True
    )
    if fundamentals.get("statement_features_enabled") is False:
        missing_fundamentals = ["statement_features_enabled"] if require_complete else []
        fundamentals_message = (
            "PIT fundamentals are disabled for this profile; complete fundamental "
            "strategy support remains pending"
        )
    else:
        missing_fundamentals = [
            rule for rule in PIT_FUNDAMENTALS_RULES if fundamentals.get(rule) is not True
        ]
        fundamentals_message = (
            "point-in-time fundamentals semantics are declared"
            if not missing_fundamentals
            else "point-in-time fundamentals semantics are incomplete"
        )
    if industry.get("historical_backtest_enabled") is False:
        missing_industry = ["historical_backtest_enabled"] if require_complete else []
        industry_message = (
            "historical industry membership is disabled for this profile; "
            "industry-backed historical research remains pending"
        )
    else:
        missing_industry = [
            rule for rule in HISTORICAL_INDUSTRY_RULES if industry.get(rule) is not True
        ]
        industry_message = (
            "historical industry semantics are declared"
            if not missing_industry
            else "historical industry semantics are incomplete"
        )
    missing_rules = [rule for rule in SIDE_AWARE_RULES if trading.get(rule) is not True]
    return [
        _check(
            "profile:pit_universe",
            passed=universe_passed,
            message=(
                "point-in-time by-date universe is declared"
                if universe_passed
                else "point-in-time by-date universe is not declared"
            ),
            details=universe,
        ),
        _check(
            "profile:pit_fundamentals",
            passed=not missing_fundamentals,
            message=fundamentals_message,
            details={**fundamentals, "missing_rules": missing_fundamentals},
        ),
        _check(
            "profile:historical_industry",
            passed=not missing_industry,
            message=industry_message,
            details={**industry, "missing_rules": missing_industry},
        ),
        _check(
            "profile:side_aware_trading",
            passed=not missing_rules,
            message=(
                "side-aware trading policies are declared"
                if not missing_rules
                else "side-aware trading policies are incomplete"
            ),
            details={"missing_rules": missing_rules},
        ),
    ]


def _research_report_checks(
    evidence: Mapping[str, Any],
    *,
    base_dir: Path | None,
) -> list[dict[str, Any]]:
    return [_validation_check(evidence, key, base_dir=base_dir) for key in RESEARCH_REPORT_KEYS]


def _broker_checks(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    broker = _mapping(evidence.get("broker_trading"))
    fields = (
        "adapter_supported",
        "account_permissions_verified",
        "supervised_smoke_evidence",
        "operational_approval",
    )
    return [
        _check(
            f"broker:{field}",
            passed=broker.get(field) is True,
            message=f"{field} is {'verified' if broker.get(field) is True else 'not verified'}",
        )
        for field in fields
    ]


def _gate_check(
    check_id: str,
    checks: list[dict[str, Any]],
    *,
    passed_message: str,
    failed_message: str,
) -> dict[str, Any]:
    passed = _all_pass(checks)
    return _check(
        check_id,
        passed=passed,
        message=passed_message if passed else failed_message,
    )


def _baseline_checks(
    root: Path,
    evidence: Mapping[str, Any],
    *,
    evidence_base: Path | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    contract_checks, contract_state = _contract_checks(root)
    checks = [
        *contract_checks,
        _registry_check(root / "metadata" / "dataset_registry.csv"),
        _validation_check(evidence, "daily_clean_validation_report", base_dir=evidence_base),
        _validation_check(evidence, "universe_validation_report", base_dir=evidence_base),
        _run_output_check(evidence, base_dir=evidence_base),
        _targets_check(evidence, base_dir=evidence_base),
        _qexec_check(evidence, base_dir=evidence_base),
    ]
    return checks, contract_state


def _complete_data_checks(
    baseline_checks: list[dict[str, Any]],
    contract_state: Mapping[str, Any],
    profile: Mapping[str, Any],
    profile_checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        _gate_check(
            "baseline_reproducible",
            baseline_checks,
            passed_message="baseline evidence passed",
            failed_message="baseline evidence is incomplete",
        ),
        _window_check(contract_state, profile),
        *_contract_asset_checks(contract_state, COMPLETE_PIT_ASSETS),
        *profile_checks[:3],
    ]


def _strategy_checks(
    complete_data_checks: list[dict[str, Any]],
    profile_checks: list[dict[str, Any]],
    evidence: Mapping[str, Any],
    *,
    evidence_base: Path | None,
) -> list[dict[str, Any]]:
    return [
        _gate_check(
            "complete_pit_research_data",
            complete_data_checks,
            passed_message="complete PIT research data passed",
            failed_message="complete PIT research data is incomplete",
        ),
        profile_checks[3],
        *_research_report_checks(evidence, base_dir=evidence_base),
    ]


def _broker_level_checks(
    baseline_checks: list[dict[str, Any]],
    evidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        _gate_check(
            "baseline_reproducible",
            baseline_checks,
            passed_message="baseline evidence passed",
            failed_message="baseline evidence is incomplete",
        ),
        *_broker_checks(evidence),
    ]


def _readiness_levels(
    *,
    baseline_checks: list[dict[str, Any]],
    complete_data_checks: list[dict[str, Any]],
    strategy_checks: list[dict[str, Any]],
    broker_checks: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    levels = {
        "baseline_reproducible": _status("baseline_reproducible", baseline_checks),
        "complete_pit_research_data": _status("complete_pit_research_data", complete_data_checks),
        "production_strategy_evidence": _status(
            "production_strategy_evidence",
            strategy_checks,
        ),
        "broker_trading_enabled": _status("broker_trading_enabled", broker_checks),
    }
    levels["research_default_promotable"] = _status(
        "research_default_promotable",
        strategy_checks,
    )
    return levels


def _readiness_summary(
    levels: Mapping[str, Mapping[str, Any]],
    contract_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "passed_levels": [name for name in READINESS_LEVELS if levels[name]["passed"]],
        "failed_levels": [name for name in READINESS_LEVELS if not levels[name]["passed"]],
        "legacy_cn_alias_present": bool(contract_state.get("legacy_cn_alias")),
    }


def build_readiness_report(
    artifacts_root: str | Path,
    *,
    evidence_manifest: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(artifacts_root).expanduser().resolve()
    evidence_path = (
        Path(evidence_manifest).expanduser().resolve() if evidence_manifest is not None else None
    )
    evidence, evidence_base = _load_evidence_manifest(evidence_path)

    baseline_checks, contract_state = _baseline_checks(root, evidence, evidence_base=evidence_base)
    profile = _mapping(evidence.get("research_profile"))
    profile_checks = _profile_checks(profile, require_complete=True)
    complete_data_checks = _complete_data_checks(
        baseline_checks,
        contract_state,
        profile,
        profile_checks,
    )
    strategy_checks = _strategy_checks(
        complete_data_checks,
        profile_checks,
        evidence,
        evidence_base=evidence_base,
    )
    broker_checks = _broker_level_checks(baseline_checks, evidence)
    levels = _readiness_levels(
        baseline_checks=baseline_checks,
        complete_data_checks=complete_data_checks,
        strategy_checks=strategy_checks,
        broker_checks=broker_checks,
    )

    return {
        "schema_version": 1,
        "market": "a_share",
        "artifacts_root": str(root),
        "evidence_manifest": str(evidence_path) if evidence_path else None,
        "contract": contract_state,
        "levels": levels,
        "summary": _readiness_summary(levels, contract_state),
    }
