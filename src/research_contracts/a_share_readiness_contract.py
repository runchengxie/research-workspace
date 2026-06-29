"""A-share current-contract and registry checks."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from a_share_readiness_common import (
    BASELINE_ASSETS,
    COMPLETE_PIT_ASSETS,
    _check,
    _date_token,
    _mapping,
    _read_json,
)


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


def _registry_check(registry_path: Path) -> dict[str, Any]:
    if not registry_path.is_file():
        return _check(
            "dataset_registry",
            passed=False,
            message=f"Missing dataset registry: {registry_path}",
        )
    try:
        rows = list(
            csv.DictReader(
                line
                for line in registry_path.read_text(encoding="utf-8").splitlines()
                if not line.startswith("#")
            )
        )
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


def _empty_contract_state(contract_path: Path, legacy_alias: Path) -> dict[str, Any]:
    return {
        "path": str(contract_path),
        "legacy_cn_alias": str(legacy_alias) if legacy_alias.exists() else None,
        "assets": {},
        "effective_start_date": None,
        "effective_end_date": None,
    }


def _load_current_contract(
    contract_path: Path,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not contract_path.is_file():
        return None, (
            _check(
                "a_share_current_contract",
                passed=False,
                message=f"Missing canonical A-share contract: {contract_path}",
            )
        )
    try:
        return _read_json(contract_path), None
    except ValueError as exc:
        return None, _check("a_share_current_contract", passed=False, message=str(exc))


def _current_contract_check(
    contract_path: Path,
    contract: Mapping[str, Any],
    *,
    legacy_alias: str | None,
) -> dict[str, Any]:
    meta = _mapping(contract.get("contract"))
    market = str(meta.get("market") or "")
    return _check(
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
            "legacy_cn_alias": legacy_alias,
        },
    )


def _contract_asset_state(asset: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _mapping(asset.get("manifest"))
    start_date = _manifest_date(asset, "start")
    end_date = _manifest_date(asset, "end") or _date_token(asset.get("as_of"))
    return {
        "exists": bool(asset.get("exists")),
        "manifest_path": asset.get("manifest_path"),
        "manifest_status": manifest.get("status"),
        "start_date": start_date,
        "end_date": end_date,
        "totals": manifest.get("totals"),
    }


def _asset_completed(asset_state: Mapping[str, Any]) -> bool:
    return (
        bool(asset_state.get("exists"))
        and bool(asset_state.get("manifest_path"))
        and str(asset_state.get("manifest_status") or "") == "completed"
    )


def _baseline_asset_check(asset_key: str, asset_state: Mapping[str, Any]) -> dict[str, Any]:
    passed = _asset_completed(asset_state)
    return _check(
        f"asset:{asset_key}",
        passed=passed,
        message=(
            f"{asset_key} asset and completed manifest are present"
            if passed
            else f"{asset_key} asset or completed manifest is missing"
        ),
        details=asset_state,
    )


def _current_contract_asset_checks(
    contract: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    assets = _mapping(contract.get("assets"))
    state_assets: dict[str, Any] = {}
    starts: list[str] = []
    ends: list[str] = []

    for asset_key in (*BASELINE_ASSETS, *COMPLETE_PIT_ASSETS):
        asset_state = _contract_asset_state(_mapping(assets.get(asset_key)))
        state_assets[asset_key] = asset_state
        if asset_state.get("start_date"):
            starts.append(str(asset_state["start_date"]))
        if asset_state.get("end_date"):
            ends.append(str(asset_state["end_date"]))
        if asset_key in BASELINE_ASSETS:
            checks.append(_baseline_asset_check(asset_key, asset_state))

    return checks, {
        "assets": state_assets,
        "effective_start_date": max(starts) if starts else None,
        "effective_end_date": min(ends) if ends else None,
    }


def _contract_checks(artifacts_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    contract_path = artifacts_root / "metadata" / "current_assets" / "a_share_current.json"
    legacy_alias = artifacts_root / "metadata" / "current_assets" / "cn_current.json"
    state = _empty_contract_state(contract_path, legacy_alias)
    contract, error_check = _load_current_contract(contract_path)
    if contract is None:
        assert error_check is not None
        return [error_check], state

    checks = [
        _current_contract_check(
            contract_path,
            contract,
            legacy_alias=state["legacy_cn_alias"],
        )
    ]
    asset_checks, asset_state = _current_contract_asset_checks(contract)
    checks.extend(asset_checks)
    state.update(asset_state)
    return checks, state
