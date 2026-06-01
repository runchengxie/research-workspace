#!/usr/bin/env python3
"""Read-only A-share readiness report for the integrated workspace."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


READINESS_LEVELS = (
    "baseline_reproducible",
    "research_default_promotable",
    "broker_trading_enabled",
)
BASELINE_ASSETS = (
    "instruments",
    "daily_clean",
    "universe_by_date",
    "universe_symbols",
    "universe_meta",
)
RESEARCH_REPORT_KEYS = (
    "benchmark_ladder_report",
    "cpcv_report",
    "feature_evidence_report",
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


def _manifest_date(asset: Mapping[str, Any], key: str) -> str | None:
    manifest = _mapping(asset.get("manifest"))
    query = _mapping(manifest.get("query"))
    aliases = {
        "start": ("query_start_date", "start_date"),
        "end": ("query_end_date", "end_date"),
    }
    for field in aliases[key]:
        token = _date_token(manifest.get(field))
        if token:
            return token
        token = _date_token(query.get(field.removeprefix("query_")))
        if token:
            return token
    return None


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


def _registry_check(registry_path: Path) -> dict[str, Any]:
    if not registry_path.is_file():
        return _check(
            "dataset_registry",
            passed=False,
            message=f"Missing dataset registry: {registry_path}",
        )
    try:
        rows = list(csv.DictReader(
            line for line in registry_path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("#")
        ))
    except OSError as exc:
        return _check("dataset_registry", passed=False, message=str(exc))
    names = {str(row.get("dataset_name") or "") for row in rows}
    passed = "a_share_current_contract" in names
    return _check(
        "dataset_registry",
        passed=passed,
        message=(
            "registry contains a_share_current_contract"
            if passed
            else "registry does not contain a_share_current_contract"
        ),
        details={"path": str(registry_path), "rows": len(rows)},
    )


def _contract_checks(artifacts_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    contract_path = artifacts_root / "metadata" / "current_assets" / "a_share_current.json"
    legacy_alias = artifacts_root / "metadata" / "current_assets" / "cn_current.json"
    checks: list[dict[str, Any]] = []
    state: dict[str, Any] = {
        "path": str(contract_path),
        "legacy_cn_alias": str(legacy_alias) if legacy_alias.exists() else None,
        "assets": {},
        "effective_start_date": None,
        "effective_end_date": None,
    }
    if not contract_path.is_file():
        checks.append(
            _check(
                "a_share_current_contract",
                passed=False,
                message=f"Missing canonical A-share contract: {contract_path}",
            )
        )
        return checks, state
    try:
        contract = _read_json(contract_path)
    except ValueError as exc:
        checks.append(_check("a_share_current_contract", passed=False, message=str(exc)))
        return checks, state

    meta = _mapping(contract.get("contract"))
    market = str(meta.get("market") or "")
    checks.append(
        _check(
            "a_share_current_contract",
            passed=market == "a_share",
            message=(
                "canonical A-share contract is present"
                if market == "a_share"
                else f"canonical contract has unexpected market={market!r}"
            ),
            details={
                "path": str(contract_path),
                "provider": meta.get("provider"),
                "target_date": meta.get("target_date"),
                "legacy_cn_alias": state["legacy_cn_alias"],
            },
        )
    )

    assets = _mapping(contract.get("assets"))
    starts: list[str] = []
    ends: list[str] = []
    for asset_key in BASELINE_ASSETS:
        asset = _mapping(assets.get(asset_key))
        manifest = _mapping(asset.get("manifest"))
        start_date = _manifest_date(asset, "start")
        end_date = _manifest_date(asset, "end") or _date_token(asset.get("as_of"))
        if start_date:
            starts.append(start_date)
        if end_date:
            ends.append(end_date)
        state["assets"][asset_key] = {
            "exists": bool(asset.get("exists")),
            "manifest_path": asset.get("manifest_path"),
            "manifest_status": manifest.get("status"),
            "start_date": start_date,
            "end_date": end_date,
            "totals": manifest.get("totals"),
        }
        passed = (
            bool(asset.get("exists"))
            and bool(asset.get("manifest_path"))
            and str(manifest.get("status") or "") == "completed"
        )
        checks.append(
            _check(
                f"asset:{asset_key}",
                passed=passed,
                message=(
                    f"{asset_key} asset and completed manifest are present"
                    if passed
                    else f"{asset_key} asset or completed manifest is missing"
                ),
                details=state["assets"][asset_key],
            )
        )
    state["effective_start_date"] = max(starts) if starts else None
    state["effective_end_date"] = min(ends) if ends else None
    return checks, state


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
        message="research run outputs are present" if not missing else "research run outputs are incomplete",
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
        return _check("targets_lineage", passed=False, message="targets_file is missing", details=details)
    if lineage_path is None or not lineage_path.is_file():
        return _check("targets_lineage", passed=False, message="targets lineage file is missing", details=details)
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
        message=error or ("CN dry-run evidence passed" if passed else "CN dry-run evidence is invalid"),
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


def _profile_checks(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    universe = _mapping(profile.get("universe"))
    fundamentals = _mapping(profile.get("fundamentals"))
    industry = _mapping(profile.get("industry"))
    trading = _mapping(profile.get("trading_rules"))

    universe_passed = (
        str(universe.get("mode") or "") in {"by_date", "pit"}
        and universe.get("point_in_time") is True
    )
    missing_fundamentals = [
        rule for rule in PIT_FUNDAMENTALS_RULES if fundamentals.get(rule) is not True
    ]
    missing_industry = [
        rule for rule in HISTORICAL_INDUSTRY_RULES if industry.get(rule) is not True
    ]
    missing_rules = [rule for rule in SIDE_AWARE_RULES if trading.get(rule) is not True]
    return [
        _check(
            "profile:pit_universe",
            passed=universe_passed,
            message="point-in-time by-date universe is declared" if universe_passed else "point-in-time by-date universe is not declared",
            details=universe,
        ),
        _check(
            "profile:pit_fundamentals",
            passed=not missing_fundamentals,
            message=(
                "point-in-time fundamentals semantics are declared"
                if not missing_fundamentals
                else "point-in-time fundamentals semantics are incomplete"
            ),
            details={**fundamentals, "missing_rules": missing_fundamentals},
        ),
        _check(
            "profile:historical_industry",
            passed=not missing_industry,
            message=(
                "historical industry semantics are declared"
                if not missing_industry
                else "historical industry semantics are incomplete"
            ),
            details={**industry, "missing_rules": missing_industry},
        ),
        _check(
            "profile:side_aware_trading",
            passed=not missing_rules,
            message="side-aware trading policies are declared" if not missing_rules else "side-aware trading policies are incomplete",
            details={"missing_rules": missing_rules},
        ),
    ]


def _research_report_checks(
    evidence: Mapping[str, Any],
    *,
    base_dir: Path | None,
) -> list[dict[str, Any]]:
    return [
        _validation_check(evidence, key, base_dir=base_dir)
        for key in RESEARCH_REPORT_KEYS
    ]


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


def build_readiness_report(
    artifacts_root: str | Path,
    *,
    evidence_manifest: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(artifacts_root).expanduser().resolve()
    evidence_path = (
        Path(evidence_manifest).expanduser().resolve()
        if evidence_manifest is not None
        else None
    )
    evidence, evidence_base = _load_evidence_manifest(evidence_path)

    contract_checks, contract_state = _contract_checks(root)
    baseline_checks = [
        *contract_checks,
        _registry_check(root / "metadata" / "dataset_registry.csv"),
        _validation_check(evidence, "daily_clean_validation_report", base_dir=evidence_base),
        _validation_check(evidence, "universe_validation_report", base_dir=evidence_base),
        _run_output_check(evidence, base_dir=evidence_base),
        _targets_check(evidence, base_dir=evidence_base),
        _qexec_check(evidence, base_dir=evidence_base),
    ]

    profile = _mapping(evidence.get("research_profile"))
    research_checks = [
        _check(
            "baseline_reproducible",
            passed=_all_pass(baseline_checks),
            message="baseline evidence passed" if _all_pass(baseline_checks) else "baseline evidence is incomplete",
        ),
        _window_check(contract_state, profile),
        *_profile_checks(profile),
        *_research_report_checks(evidence, base_dir=evidence_base),
    ]
    broker_checks = [
        _check(
            "baseline_reproducible",
            passed=_all_pass(baseline_checks),
            message="baseline evidence passed" if _all_pass(baseline_checks) else "baseline evidence is incomplete",
        ),
        *_broker_checks(evidence),
    ]

    levels = {
        "baseline_reproducible": _status("baseline_reproducible", baseline_checks),
        "research_default_promotable": _status("research_default_promotable", research_checks),
        "broker_trading_enabled": _status("broker_trading_enabled", broker_checks),
    }
    return {
        "schema_version": 1,
        "market": "a_share",
        "artifacts_root": str(root),
        "evidence_manifest": str(evidence_path) if evidence_path else None,
        "contract": contract_state,
        "levels": levels,
        "summary": {
            "passed_levels": [name for name in READINESS_LEVELS if levels[name]["passed"]],
            "failed_levels": [name for name in READINESS_LEVELS if not levels[name]["passed"]],
            "legacy_cn_alias_present": bool(contract_state.get("legacy_cn_alias")),
        },
    }


def _write_report(report: Mapping[str, Any], output: Path | None, *, pretty: bool) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=2 if pretty else None)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect no-write A-share workspace readiness.")
    parser.add_argument(
        "--artifacts-root",
        default=os.environ.get("DATA_PLATFORM_ROOT"),
        help="Shared data-platform root. Defaults to DATA_PLATFORM_ROOT.",
    )
    parser.add_argument("--evidence-manifest")
    parser.add_argument("--out")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--require", choices=READINESS_LEVELS)
    args = parser.parse_args(argv)

    if not args.artifacts_root:
        parser.error("--artifacts-root or DATA_PLATFORM_ROOT is required")
    try:
        report = build_readiness_report(
            args.artifacts_root,
            evidence_manifest=args.evidence_manifest,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _write_report(report, Path(args.out) if args.out else None, pretty=args.pretty)
    if args.require and not report["levels"][args.require]["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
