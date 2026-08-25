"""Canonical strategy promotion evidence validation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .promotion_evidence_checks import check_errors
from .promotion_evidence_common import append_unique, mapping, read_json, safe_relative
from .promotion_evidence_lineage import profile_for_strategy, validate_lineage

_SCHEMA_VERSION = "strategy_promotion_evidence.v2"
SourceLoader = Callable[[str], tuple[dict[str, Any] | None, list[str]]]


@dataclass(frozen=True)
class PromotionValidation:
    profile_id: str | None
    validated_checks: list[str] = field(default_factory=list)
    invalid_evidence: dict[str, list[str]] = field(default_factory=dict)
    profile_failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.invalid_evidence and not self.profile_failures


def _receipt_path(root: Path, value: object) -> tuple[Path | None, str | None]:
    path, relative = safe_relative(root, value)
    if path is None or relative is None:
        return None, None
    if not relative.startswith("strategy-research/evidence/promotion/"):
        return None, None
    return path, relative


def _identity_errors(
    receipt: Mapping[str, Any],
    *,
    strategy_id: str,
    profile_id: str,
) -> list[str]:
    errors: list[str] = []
    if receipt.get("schema_version") != _SCHEMA_VERSION:
        errors.append("schema_mismatch")
    if receipt.get("strategy_id") != strategy_id:
        errors.append("strategy_mismatch")
    if receipt.get("profile_id") != profile_id:
        errors.append("profile_mismatch")
    if receipt.get("status") != "passed":
        errors.append("receipt_not_passed")
    return errors


def _load_source(
    *,
    root: Path,
    source_value: object,
    strategy_id: str,
    profile_id: str,
    profile: Mapping[str, Any],
    data_platform_root: Path | None,
    gitlinks: Mapping[str, str] | None,
    cache: dict[str, tuple[dict[str, Any] | None, list[str]]],
) -> tuple[dict[str, Any] | None, list[str]]:
    if not isinstance(source_value, str) or not source_value.strip():
        return None, ["missing_promotion_evidence"]
    receipt_path, relative = _receipt_path(root, source_value)
    if receipt_path is None or relative is None:
        return None, ["evidence_path_invalid"]
    if relative in cache:
        return cache[relative]
    receipt = read_json(receipt_path)
    if receipt is None:
        result = (None, ["evidence_not_found"])
        cache[relative] = result
        return result

    errors = _identity_errors(
        receipt,
        strategy_id=strategy_id,
        profile_id=profile_id,
    )
    for error in validate_lineage(
        receipt,
        root=root,
        data_platform_root=data_platform_root,
        profile=profile,
        gitlinks=gitlinks,
    ):
        append_unique(errors, error)
    result = (receipt, errors)
    cache[relative] = result
    return result


def _validate_lifecycle_sources(
    *,
    required_checks: list[str],
    bundle_checks: Mapping[str, Any],
    load_source: SourceLoader,
) -> tuple[list[str], dict[str, list[str]]]:
    validated: list[str] = []
    invalid: dict[str, list[str]] = {}
    for check_id in required_checks:
        if mapping(bundle_checks.get(check_id)).get("outcome") != "pass":
            continue
        receipt, errors = load_source(check_id)
        semantic_errors = check_errors(receipt, check_id) if receipt is not None else []
        combined = list(dict.fromkeys([*errors, *semantic_errors]))
        if combined:
            invalid[check_id] = combined
        else:
            validated.append(check_id)
    return validated, invalid


def _validate_profile_sources(
    *,
    profile: Mapping[str, Any],
    validated: list[str],
    load_source: SourceLoader,
) -> list[str]:
    failures: list[str] = []
    raw_checks = profile.get("required_profile_checks")
    profile_checks = raw_checks if isinstance(raw_checks, list) else []
    for raw_check_id in profile_checks:
        check_id = str(raw_check_id)
        receipt, errors = load_source(check_id)
        semantic_errors = check_errors(receipt, check_id) if receipt is not None else []
        if errors or semantic_errors:
            for error in [*errors, *semantic_errors, f"{check_id}_not_passed"]:
                append_unique(failures, error)
        elif check_id not in validated:
            validated.append(check_id)
    return failures


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
    profile_id, profile = profile_for_strategy(profiles, strategy_id)
    if profile_id is None:
        return PromotionValidation(profile_id=None)

    bundle_map = mapping(bundle)
    bundle_checks = mapping(bundle_map.get("checks"))
    sources = mapping(bundle_map.get("promotion_evidence"))
    cache: dict[str, tuple[dict[str, Any] | None, list[str]]] = {}

    def load_source(check_id: str) -> tuple[dict[str, Any] | None, list[str]]:
        return _load_source(
            root=root,
            source_value=sources.get(check_id),
            strategy_id=strategy_id,
            profile_id=profile_id,
            profile=profile,
            data_platform_root=data_platform_root,
            gitlinks=gitlinks,
            cache=cache,
        )

    validated, invalid = _validate_lifecycle_sources(
        required_checks=required_checks,
        bundle_checks=bundle_checks,
        load_source=load_source,
    )
    profile_failures = _validate_profile_sources(
        profile=profile,
        validated=validated,
        load_source=load_source,
    )
    return PromotionValidation(
        profile_id=profile_id,
        validated_checks=validated,
        invalid_evidence=invalid,
        profile_failures=profile_failures,
    )
