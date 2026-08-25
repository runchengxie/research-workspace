"""Lineage validation for canonical strategy promotion receipts."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .promotion_evidence_common import (
    SHA40,
    append_unique,
    date_token,
    hash_matches,
    mapping,
    read_json,
    safe_relative,
)


def profile_for_strategy(
    profiles: Mapping[str, Any],
    strategy_id: str,
) -> tuple[str | None, dict[str, Any]]:
    profile_id = mapping(profiles.get("strategy_profiles")).get(strategy_id)
    if not isinstance(profile_id, str) or not profile_id:
        return None, {}
    return profile_id, mapping(mapping(profiles.get("profiles")).get(profile_id))


def _manifest_date(asset: Mapping[str, Any], key: str) -> str | None:
    manifest = mapping(asset.get("manifest"))
    query = mapping(manifest.get("query"))
    aliases = {
        "start": ("query_start_date", "start_date"),
        "end": ("query_end_date", "end_date"),
    }
    for field in aliases[key]:
        token = date_token(manifest.get(field))
        if token:
            return token
        token = date_token(query.get(field.removeprefix("query_")))
        if token:
            return token
    return None


def _normalize_data_path(root: Path, value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    base = root.expanduser().resolve()
    if path.is_absolute():
        resolved = path.resolve()
        try:
            return resolved.relative_to(base).as_posix()
        except ValueError:
            return None
    resolved, relative = safe_relative(base, path)
    return relative if resolved is not None else None


def _current_gitlinks(root: Path, names: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in names:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "ls-tree", "HEAD", name],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        fields = result.stdout.split() if result.returncode == 0 else []
        if len(fields) >= 3 and fields[0] == "160000" and SHA40.fullmatch(fields[2]):
            out[name] = fields[2]
    return out


def _repository_errors(
    lineage: Mapping[str, Any],
    *,
    root: Path,
    gitlinks: Mapping[str, str] | None,
) -> list[str]:
    producer = str(lineage.get("producer_repository") or "").strip()
    repositories = mapping(lineage.get("repositories"))
    errors: list[str] = []
    if not producer or producer not in repositories:
        errors.append("repository_commit_mismatch")
    names = {str(name) for name in repositories}
    current = dict(gitlinks) if gitlinks is not None else _current_gitlinks(root, names)
    for name, raw_sha in repositories.items():
        sha = str(raw_sha or "").strip()
        if not SHA40.fullmatch(sha) or current.get(name) != sha:
            append_unique(errors, "repository_commit_mismatch")
    return errors


def _load_current_contract(
    lineage: Mapping[str, Any],
    *,
    data_root: Path,
    profile: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    declared = mapping(lineage.get("current_contract"))
    expected_path = str(profile.get("current_contract_path") or "").strip()
    if declared.get("path") != expected_path or not hash_matches(declared, root=data_root):
        return None, ["current_contract_mismatch"]
    path, _relative = safe_relative(data_root, expected_path)
    contract = read_json(path) if path is not None else None
    if contract is None or mapping(contract.get("contract")).get("market") != "a_share":
        return None, ["current_contract_mismatch"]
    return contract, []


def _manifest_rows(lineage: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = lineage.get("data_manifests")
    if not isinstance(rows, list):
        return {}
    return {
        str(mapping(item).get("asset_key") or ""): mapping(item)
        for item in rows
        if isinstance(item, Mapping)
    }


def _asset_errors(
    contract: Mapping[str, Any],
    lineage: Mapping[str, Any],
    *,
    data_root: Path,
    profile: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    assets = mapping(contract.get("assets"))
    declared = _manifest_rows(lineage)
    required = profile.get("required_current_assets")
    required_assets = required if isinstance(required, list) else []
    for raw_key in required_assets:
        asset_key = str(raw_key)
        asset = mapping(assets.get(asset_key))
        manifest = mapping(asset.get("manifest"))
        manifest_path = _normalize_data_path(data_root, asset.get("manifest_path"))
        if asset.get("exists") is not True or manifest.get("status") != "completed":
            append_unique(errors, "current_contract_mismatch")
            continue
        if not manifest_path:
            append_unique(errors, "current_contract_mismatch")
            continue
        row = declared.get(asset_key, {})
        if row.get("path") != manifest_path or not hash_matches(row, root=data_root):
            append_unique(errors, "data_manifest_mismatch")
    return errors


def _window_errors(
    receipt: Mapping[str, Any],
    contract: Mapping[str, Any],
    *,
    profile: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    window = mapping(receipt.get("research_window"))
    configured_start = date_token(profile.get("configured_start_date"))
    receipt_start = date_token(window.get("configured_start_date"))
    receipt_end = date_token(window.get("end_date"))
    if not configured_start or receipt_start != configured_start:
        errors.append("historical_coverage_insufficient")
    daily = mapping(mapping(contract.get("assets")).get("daily_clean"))
    daily_start = _manifest_date(daily, "start")
    daily_end = _manifest_date(daily, "end") or date_token(daily.get("as_of"))
    if configured_start and (not daily_start or daily_start > configured_start):
        append_unique(errors, "historical_coverage_insufficient")
    if not receipt_end or not daily_end or daily_end > receipt_end:
        append_unique(errors, "evidence_window_stale")
    return errors


def _source_errors(
    lineage: Mapping[str, Any],
    *,
    root: Path,
    data_root: Path,
) -> list[str]:
    sources = lineage.get("source_artifacts")
    if not isinstance(sources, list) or not sources:
        return ["source_hash_mismatch"]
    for item in sources:
        source = mapping(item)
        location = source.get("location")
        if location not in {"workspace", "data_platform"}:
            return ["source_hash_mismatch"]
        source_root = root if location == "workspace" else data_root
        if not hash_matches(source, root=source_root):
            return ["source_hash_mismatch"]
    return []


def validate_lineage(
    receipt: Mapping[str, Any],
    *,
    root: Path,
    data_platform_root: Path | None,
    profile: Mapping[str, Any],
    gitlinks: Mapping[str, str] | None,
) -> list[str]:
    lineage = mapping(receipt.get("lineage"))
    errors = _repository_errors(lineage, root=root, gitlinks=gitlinks)
    if not hash_matches(lineage.get("config"), root=root):
        append_unique(errors, "config_hash_mismatch")
    if data_platform_root is None:
        append_unique(errors, "data_root_unavailable")
        return errors

    data_root = data_platform_root.expanduser().resolve()
    contract, contract_errors = _load_current_contract(
        lineage,
        data_root=data_root,
        profile=profile,
    )
    for error in contract_errors:
        append_unique(errors, error)
    if contract is None:
        return errors

    for error in _asset_errors(
        contract,
        lineage,
        data_root=data_root,
        profile=profile,
    ):
        append_unique(errors, error)
    for error in _window_errors(receipt, contract, profile=profile):
        append_unique(errors, error)
    for error in _source_errors(lineage, root=root, data_root=data_root):
        append_unique(errors, error)
    return errors
