from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .artifact_contracts import ContractValidationResult

CONTRACT_OWNERSHIP_SCHEMA_VERSION = "contract_ownership.v1"
_STRING_FIELDS = (
    "name",
    "schema",
    "producer",
    "versioning",
    "compatibility",
    "test_command",
    "rollback",
)


@dataclass(frozen=True, slots=True)
class ContractOwnership:
    name: str
    schema: str
    producer: str
    consumers: tuple[str, ...]
    versioning: str
    compatibility: str
    test_command: str
    rollback: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ContractOwnership:
        consumers = cast(list[str], payload["consumers"])
        return cls(
            name=cast(str, payload["name"]).strip(),
            schema=cast(str, payload["schema"]).strip(),
            producer=cast(str, payload["producer"]).strip(),
            consumers=tuple(value.strip() for value in consumers),
            versioning=cast(str, payload["versioning"]).strip(),
            compatibility=cast(str, payload["compatibility"]).strip(),
            test_command=cast(str, payload["test_command"]).strip(),
            rollback=cast(str, payload["rollback"]).strip(),
        )


def _load_payload(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("contract ownership registry must be a JSON object")
    return payload


def _record_type_issues(record: object, record_index: int) -> list[str]:
    prefix = f"contracts[{record_index}]"
    if not isinstance(record, Mapping):
        return [f"{prefix}: must be an object"]
    issues: list[str] = []
    for field in _STRING_FIELDS:
        if not isinstance(record.get(field), str):
            issues.append(f"{prefix}.{field}: must be a string")
    consumers = record.get("consumers")
    if not isinstance(consumers, list):
        issues.append(f"{prefix}.consumers: must be a list")
        return issues
    for consumer_index, consumer in enumerate(consumers):
        if not isinstance(consumer, str):
            issues.append(f"{prefix}.consumers[{consumer_index}]: must be a string")
        elif not consumer.strip():
            issues.append(f"{prefix}.consumers[{consumer_index}]: must not be blank")
    return issues


def _ownership_type_issues(payload: Mapping[str, Any]) -> list[str]:
    records = payload.get("contracts")
    if not isinstance(records, list):
        return ["contracts: must be a list"]
    return [
        issue
        for record_index, record in enumerate(records)
        for issue in _record_type_issues(record, record_index)
    ]


def _construct_contract_ownership(payload: Mapping[str, Any]) -> tuple[ContractOwnership, ...]:
    records = cast(list[Mapping[str, Any]], payload["contracts"])
    return tuple(ContractOwnership.from_mapping(record) for record in records)


def load_contract_ownership(path: Path) -> tuple[ContractOwnership, ...]:
    payload = _load_payload(path)
    issues = _ownership_type_issues(payload)
    if issues:
        raise ValueError("; ".join(issues))
    return _construct_contract_ownership(payload)


def _record_issues(item: ContractOwnership, seen: set[str]) -> list[str]:
    label = item.name or "contract"
    issues: list[str] = []
    if not item.name:
        issues.append("contract: name is required")
    elif item.name in seen:
        issues.append(f"{item.name}: duplicate name")
    seen.add(item.name)
    for field in ("schema", "producer", "versioning", "compatibility", "test_command", "rollback"):
        if not getattr(item, field):
            issues.append(f"{label}: {field} is required")
    if not item.consumers:
        issues.append(f"{label}: consumers must be non-empty")
    if len(item.consumers) != len(set(item.consumers)):
        issues.append(f"{label}: consumers must not contain duplicates")
    return issues


def _artifact_manifest_issues(
    ownership: tuple[ContractOwnership, ...], artifact_manifest_path: Path
) -> list[str]:
    payload = _load_payload(artifact_manifest_path)
    raw_records = payload.get("artifacts")
    if not isinstance(raw_records, list):
        return ["artifact manifest artifacts must be a list"]
    artifacts = {
        str(record.get("artifact", "")).strip(): record
        for record in raw_records
        if isinstance(record, Mapping)
    }
    issues: list[str] = []
    for item in ownership:
        artifact = artifacts.get(item.name)
        if artifact is None:
            continue
        expected = {
            "schema": str(artifact.get("contract", "")).strip(),
            "producer": str(artifact.get("producer", "")).strip(),
            "consumers": tuple(
                value.strip()
                for value in artifact.get("consumers", [])
                if isinstance(value, str) and value.strip()
            ),
        }
        actual = {
            "schema": item.schema,
            "producer": item.producer,
            "consumers": item.consumers,
        }
        for field in expected:
            if actual[field] != expected[field]:
                issues.append(f"{item.name}: {field} differs from artifact manifest")
    return issues


def validate_contract_ownership(
    *,
    registry_path: Path,
    artifact_manifest_path: Path | None = None,
) -> ContractValidationResult:
    try:
        payload = _load_payload(registry_path)
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        return ContractValidationResult((str(exc),))

    issues: list[str] = []
    if payload.get("schema_version") != CONTRACT_OWNERSHIP_SCHEMA_VERSION:
        issues.append("unexpected contract ownership schema_version")
    type_issues = _ownership_type_issues(payload)
    if type_issues:
        issues.extend(type_issues)
        return ContractValidationResult(tuple(issues))
    ownership = _construct_contract_ownership(payload)
    if not ownership:
        issues.append("contracts must be non-empty")
    seen: set[str] = set()
    for item in ownership:
        issues.extend(_record_issues(item, seen))
    if artifact_manifest_path is not None:
        try:
            issues.extend(_artifact_manifest_issues(ownership, artifact_manifest_path))
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
            issues.append(str(exc))
    return ContractValidationResult(tuple(issues))
