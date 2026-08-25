"""Canonical strategy promotion evidence validation."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SCHEMA_VERSION = "strategy_promotion_evidence.v2"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_BENCHMARK_AXES = ("universe", "horizon", "regime", "cost_bps")


@dataclass(frozen=True)
class PromotionValidation:
    profile_id: str | None
    validated_checks: list[str] = field(default_factory=list)
    invalid_evidence: dict[str, list[str]] = field(default_factory=dict)
    profile_failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.invalid_evidence and not self.profile_failures


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _date_token(value: object) -> str | None:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    return digits[:8] if len(digits) >= 8 else None


def _safe_relative(root: Path, value: object) -> tuple[Path | None, str | None]:
    text = str(value or "").strip()
    if not text:
        return None, None
    relative = Path(text)
    if relative.is_absolute():
        return None, None
    base = root.expanduser().resolve()
    resolved = (base / relative).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        return None, None
    return resolved, relative.as_posix()


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _hash_matches(entry: object, *, root: Path) -> bool:
    payload = _mapping(entry)
    path, _relative = _safe_relative(root, payload.get("path"))
    expected = str(payload.get("sha256") or "").strip()
    return bool(
        path is not None
        and _SHA256.fullmatch(expected)
        and _sha256_file(path) == expected
    )


def _append_unique(target: list[str], value: str) -> None:
    if value not in target:
        target.append(value)


def _profile_for_strategy(
    profiles: Mapping[str, Any],
    strategy_id: str,
) -> tuple[str | None, dict[str, Any]]:
    mappings = _mapping(profiles.get("strategy_profiles"))
    profile_id = mappings.get(strategy_id)
    if not isinstance(profile_id, str) or not profile_id:
        return None, {}
    table = _mapping(profiles.get("profiles"))
    return profile_id, _mapping(table.get(profile_id))


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
    resolved, relative = _safe_relative(base, path)
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
        if result.returncode != 0 or not result.stdout.strip():
            continue
        fields = result.stdout.split()
        if len(fields) >= 3 and fields[0] == "160000" and _SHA40.fullmatch(fields[2]):
            out[name] = fields[2]
    return out


def _lineage_errors(
    receipt: Mapping[str, Any],
    *,
    root: Path,
    data_platform_root: Path | None,
    profile: Mapping[str, Any],
    gitlinks: Mapping[str, str] | None,
) -> list[str]:
    errors: list[str] = []
    lineage = _mapping(receipt.get("lineage"))
    producer = str(lineage.get("producer_repository") or "").strip()
    repositories = _mapping(lineage.get("repositories"))
    if not producer or producer not in repositories:
        _append_unique(errors, "repository_commit_mismatch")
    names = {str(name) for name in repositories}
    current_gitlinks = dict(gitlinks) if gitlinks is not None else _current_gitlinks(root, names)
    for name, value in repositories.items():
        sha = str(value or "").strip()
        if not _SHA40.fullmatch(sha) or current_gitlinks.get(name) != sha:
            _append_unique(errors, "repository_commit_mismatch")

    if not _hash_matches(lineage.get("config"), root=root):
        _append_unique(errors, "config_hash_mismatch")

    if data_platform_root is None:
        _append_unique(errors, "data_root_unavailable")
        return errors
    data_root = data_platform_root.expanduser().resolve()
    current_contract = _mapping(lineage.get("current_contract"))
    expected_contract = str(profile.get("current_contract_path") or "").strip()
    if current_contract.get("path") != expected_contract or not _hash_matches(
        current_contract,
        root=data_root,
    ):
        _append_unique(errors, "current_contract_mismatch")
        return errors

    contract_path, _relative = _safe_relative(data_root, expected_contract)
    contract = _read_json(contract_path) if contract_path is not None else None
    if contract is None or _mapping(contract.get("contract")).get("market") != "a_share":
        _append_unique(errors, "current_contract_mismatch")
        return errors

    research_window = _mapping(receipt.get("research_window"))
    configured_start = _date_token(profile.get("configured_start_date"))
    receipt_start = _date_token(research_window.get("configured_start_date"))
    receipt_end = _date_token(research_window.get("end_date"))
    if not configured_start or receipt_start != configured_start:
        _append_unique(errors, "historical_coverage_insufficient")

    assets = _mapping(contract.get("assets"))
    required_assets = profile.get("required_current_assets")
    required = required_assets if isinstance(required_assets, list) else []
    manifest_rows = lineage.get("data_manifests")
    manifests = manifest_rows if isinstance(manifest_rows, list) else []
    by_asset = {
        str(_mapping(item).get("asset_key") or ""): _mapping(item)
        for item in manifests
        if isinstance(item, Mapping)
    }
    for raw_key in required:
        asset_key = str(raw_key)
        asset = _mapping(assets.get(asset_key))
        manifest = _mapping(asset.get("manifest"))
        manifest_path = _normalize_data_path(data_root, asset.get("manifest_path"))
        if (
            asset.get("exists") is not True
            or manifest.get("status") != "completed"
            or not manifest_path
        ):
            _append_unique(errors, "current_contract_mismatch")
            continue
        declared = by_asset.get(asset_key, {})
        if declared.get("path") != manifest_path or not _hash_matches(declared, root=data_root):
            _append_unique(errors, "data_manifest_mismatch")

    daily = _mapping(assets.get("daily_clean"))
    daily_start = _manifest_date(daily, "start")
    daily_end = _manifest_date(daily, "end") or _date_token(daily.get("as_of"))
    if configured_start and (not daily_start or daily_start > configured_start):
        _append_unique(errors, "historical_coverage_insufficient")
    if receipt_end and (not daily_end or daily_end > receipt_end):
        _append_unique(errors, "evidence_window_stale")

    sources = lineage.get("source_artifacts")
    if not isinstance(sources, list) or not sources:
        _append_unique(errors, "source_hash_mismatch")
    else:
        for item in sources:
            source = _mapping(item)
            location = source.get("location")
            source_root = root if location == "workspace" else data_root
            if location not in {"workspace", "data_platform"} or not _hash_matches(
                source,
                root=source_root,
            ):
                _append_unique(errors, "source_hash_mismatch")
    return errors


def _finite_number(value: object, *, positive: bool = False) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    number = float(value)
    return math.isfinite(number) and (number > 0 if positive else number >= 0)


def _check_fields_valid(check_id: str, entry: Mapping[str, Any]) -> bool:
    if check_id == "pit":
        return all(
            entry.get(key) is True
            for key in ("pit_universe", "pit_fundamentals", "pit_industry_membership")
        )
    if check_id == "walk_forward":
        return (
            isinstance(entry.get("window_count"), int)
            and not isinstance(entry.get("window_count"), bool)
            and int(entry["window_count"]) >= 2
            and bool(str(entry.get("metric") or "").strip())
        )
    if check_id == "benchmark_matrix":
        cells = entry.get("cells")
        if not isinstance(cells, list) or len(cells) < 2:
            return False
        span = sum(
            1
            for axis in _BENCHMARK_AXES
            if len({_mapping(cell).get(axis) for cell in cells if isinstance(cell, Mapping)}) > 1
        )
        return span >= 2
    if check_id == "cost":
        scenarios = entry.get("scenarios")
        if not _finite_number(entry.get("turnover")) or not isinstance(scenarios, list):
            return False
        costs: set[float] = set()
        for item in scenarios:
            row = _mapping(item)
            if (
                not _finite_number(row.get("cost_bps"))
                or not str(row.get("metric") or "").strip()
                or not _finite_number(row.get("value"))
            ):
                return False
            costs.add(float(row["cost_bps"]))
        return len(scenarios) >= 2 and len(costs) >= 2
    if check_id == "final_oos":
        return (
            _date_token(entry.get("oos_start")) is not None
            and bool(str(entry.get("metric") or "").strip())
            and entry.get("frozen_before_evaluation") is True
            and entry.get("retuned_after_freeze") is False
        )
    if check_id == "cpcv":
        groups = entry.get("n_groups")
        test_groups = entry.get("test_groups")
        return (
            isinstance(groups, int)
            and not isinstance(groups, bool)
            and isinstance(test_groups, int)
            and not isinstance(test_groups, bool)
            and 0 < test_groups < groups
            and bool(str(entry.get("metric") or "").strip())
        )
    if check_id == "regime":
        regimes = entry.get("regimes")
        if not str(entry.get("metric") or "").strip() or not isinstance(regimes, list):
            return False
        by_id = {_mapping(item).get("id"): _mapping(item) for item in regimes}
        return all(
            regime_id in by_id and _finite_number(by_id[regime_id].get("value"))
            for regime_id in ("bull", "bear", "sideways")
        )
    if check_id == "capacity":
        portfolio_values = entry.get("portfolio_values")
        participation_rates = entry.get("participation_rates")
        return (
            isinstance(portfolio_values, list)
            and len(portfolio_values) >= 2
            and all(_finite_number(value, positive=True) for value in portfolio_values)
            and isinstance(participation_rates, list)
            and len(participation_rates) >= 2
            and all(_finite_number(value, positive=True) for value in participation_rates)
            and _finite_number(entry.get("primary_participation_rate"), positive=True)
            and _finite_number(entry.get("recommended_capacity"), positive=True)
        )
    return True


def _check_errors(receipt: Mapping[str, Any], check_id: str) -> list[str]:
    checks = _mapping(receipt.get("checks"))
    entry = _mapping(checks.get(check_id))
    if entry.get("status") != "passed":
        return ["check_not_passed"]
    if not _check_fields_valid(check_id, entry):
        return ["check_fields_invalid"]
    return []


def _receipt_path(root: Path, value: object) -> tuple[Path | None, str | None]:
    path, relative = _safe_relative(root, value)
    if path is None or relative is None:
        return None, None
    prefix = "strategy-research/evidence/promotion/"
    if not relative.startswith(prefix):
        return None, None
    return path, relative


def validate_strategy_promotion(
    *,
    root: Path,
    strategy_id: str,
    required_checks: list[str],
    bundle: Mapping[str, Any] | None,
    profiles: Mapping[str, Any],
    data_platform_root: Path | None,
    gitlinks: Mapping[str, str] | None = None,
) -> PromotionValidation:
    profile_id, profile = _profile_for_strategy(profiles, strategy_id)
    if profile_id is None:
        return PromotionValidation(profile_id=None)

    bundle_map = _mapping(bundle)
    bundle_checks = _mapping(bundle_map.get("checks"))
    sources = _mapping(bundle_map.get("promotion_evidence"))
    invalid: dict[str, list[str]] = {}
    profile_failures: list[str] = []
    validated: list[str] = []
    cache: dict[str, tuple[dict[str, Any] | None, list[str]]] = {}

    def load_for(check_id: str) -> tuple[dict[str, Any] | None, list[str]]:
        source_value = sources.get(check_id)
        if not isinstance(source_value, str) or not source_value.strip():
            return None, ["missing_promotion_evidence"]
        receipt_path, relative = _receipt_path(root, source_value)
        if receipt_path is None or relative is None:
            return None, ["evidence_path_invalid"]
        if relative in cache:
            return cache[relative]
        receipt = _read_json(receipt_path)
        if receipt is None:
            result = (None, ["evidence_not_found"])
            cache[relative] = result
            return result
        errors: list[str] = []
        if receipt.get("schema_version") != _SCHEMA_VERSION:
            errors.append("schema_mismatch")
        if receipt.get("strategy_id") != strategy_id:
            errors.append("strategy_mismatch")
        if receipt.get("profile_id") != profile_id:
            errors.append("profile_mismatch")
        if receipt.get("status") != "passed":
            errors.append("receipt_not_passed")
        for error in _lineage_errors(
            receipt,
            root=root,
            data_platform_root=data_platform_root,
            profile=profile,
            gitlinks=gitlinks,
        ):
            _append_unique(errors, error)
        result = (receipt, errors)
        cache[relative] = result
        return result

    for check_id in required_checks:
        legacy_entry = _mapping(bundle_checks.get(check_id))
        if legacy_entry.get("outcome") != "pass":
            continue
        receipt, errors = load_for(check_id)
        check_errors = _check_errors(receipt, check_id) if receipt is not None else []
        all_errors = [*errors, *check_errors]
        if all_errors:
            invalid[check_id] = list(dict.fromkeys(all_errors))
        else:
            validated.append(check_id)

    raw_profile_checks = profile.get("required_profile_checks")
    profile_checks = raw_profile_checks if isinstance(raw_profile_checks, list) else []
    for raw_check_id in profile_checks:
        check_id = str(raw_check_id)
        receipt, errors = load_for(check_id)
        check_errors = _check_errors(receipt, check_id) if receipt is not None else []
        if errors or check_errors:
            for error in errors:
                _append_unique(profile_failures, error)
            for error in check_errors:
                _append_unique(profile_failures, error)
            _append_unique(profile_failures, f"{check_id}_not_passed")
        elif check_id not in validated:
            validated.append(check_id)

    return PromotionValidation(
        profile_id=profile_id,
        validated_checks=validated,
        invalid_evidence=invalid,
        profile_failures=profile_failures,
    )
