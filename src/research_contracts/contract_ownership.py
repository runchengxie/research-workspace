from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifact_contracts import ContractValidationResult

CONTRACT_OWNERSHIP_SCHEMA_VERSION = "contract_ownership.v1"


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
        consumers = payload.get("consumers")
        return cls(
            name=str(payload.get("name", "")).strip(),
            schema=str(payload.get("schema", "")).strip(),
            producer=str(payload.get("producer", "")).strip(),
            consumers=tuple(
                value.strip() for value in consumers if isinstance(value, str) and value.strip()
            )
            if isinstance(consumers, list)
            else (),
            versioning=str(payload.get("versioning", "")).strip(),
            compatibility=str(payload.get("compatibility", "")).strip(),
            test_command=str(payload.get("test_command", "")).strip(),
            rollback=str(payload.get("rollback", "")).strip(),
        )


def _load_payload(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("contract ownership registry must be a JSON object")
    return payload


def load_contract_ownership(path: Path) -> tuple[ContractOwnership, ...]:
    payload = _load_payload(path)
    records = payload.get("contracts")
    if not isinstance(records, list):
        return ()
    return tuple(
        ContractOwnership.from_mapping(record) for record in records if isinstance(record, Mapping)
    )


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
        ownership = load_contract_ownership(registry_path)
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        return ContractValidationResult((str(exc),))

    issues: list[str] = []
    if payload.get("schema_version") != CONTRACT_OWNERSHIP_SCHEMA_VERSION:
        issues.append("unexpected contract ownership schema_version")
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
