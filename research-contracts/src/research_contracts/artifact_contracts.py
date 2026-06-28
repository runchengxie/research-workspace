from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARTIFACT_CONTRACT_SCHEMA_VERSION = "artifact_contracts.v1"
CORE_ARTIFACTS = frozenset(
    {
        "signals.parquet",
        "signals.meta.json",
        "positions_by_rebalance.csv",
        "targets.json",
    }
)
KNOWN_REPOS = frozenset(
    {
        "alpha-research",
        "market-data-platform",
        "portfolio-backtester",
        "strategy-pipeline",
        "quant-execution-engine",
    }
)


@dataclass(frozen=True)
class ArtifactContractManifest:
    schema_version: str
    artifacts: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ArtifactContractManifest:
        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, list):
            artifacts = []
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            artifacts=tuple(record for record in artifacts if isinstance(record, Mapping)),
        )


@dataclass(frozen=True)
class ContractValidationResult:
    issues: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.issues


def load_artifact_contract_manifest(path: Path) -> ArtifactContractManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("artifact contract manifest must be a JSON object")
    return ArtifactContractManifest.from_mapping(payload)


def _strings(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and value.strip()]


def _docs_sync_issues(record: Mapping[str, Any], docs_text: str) -> list[str]:
    issues: list[str] = []
    artifact = str(record.get("artifact", "")).strip()
    contract = str(record.get("contract", "")).strip()
    owner = str(record.get("owner", "")).strip()
    expected_tokens = [
        (artifact, f"{artifact}: missing from docs/contracts.md"),
        (contract, f"{artifact}: contract {contract!r} missing from docs/contracts.md"),
        (owner, f"{artifact}: owner {owner!r} missing from docs/contracts.md"),
    ]
    for token, message in expected_tokens:
        if token and token not in docs_text:
            issues.append(message)
    for file_name in _strings(record.get("canonical_files")):
        if file_name not in docs_text:
            issues.append(f"{artifact}: canonical file {file_name!r} missing from docs")
    return issues


def _entrypoint_issues(root: Path, artifact: str, entrypoints: object) -> list[str]:
    if not isinstance(entrypoints, list) or not entrypoints:
        return [f"{artifact}: entrypoints must be non-empty"]

    issues: list[str] = []
    for entrypoint in entrypoints:
        if not isinstance(entrypoint, Mapping):
            issues.append(f"{artifact}: entrypoint must be an object")
            continue
        repo = str(entrypoint.get("repo", "")).strip()
        path = str(entrypoint.get("path", "")).strip()
        if repo not in KNOWN_REPOS:
            issues.append(f"{artifact}: unknown entrypoint repo {repo!r}")
        if not path:
            issues.append(f"{artifact}: entrypoint path is required")
        elif repo in KNOWN_REPOS and not (root / repo / path).is_file():
            issues.append(f"{artifact}: missing entrypoint path {repo}/{path}")
    return issues


def _artifact_record_issues(
    root: Path,
    record: Mapping[str, Any],
    docs_text: str,
    seen: set[str],
) -> list[str]:
    artifact = str(record.get("artifact", "")).strip()
    contract = str(record.get("contract", "")).strip()
    owner = str(record.get("owner", "")).strip()
    if not artifact:
        return ["artifact is required"]

    issues: list[str] = []
    if artifact in seen:
        issues.append(f"{artifact}: duplicate artifact")
    seen.add(artifact)
    if not contract:
        issues.append(f"{artifact}: contract is required")
    if owner not in KNOWN_REPOS:
        issues.append(f"{artifact}: unknown owner {owner!r}")
    if not _strings(record.get("required_fields")):
        issues.append(f"{artifact}: required_fields must be non-empty")
    issues.extend(_docs_sync_issues(record, docs_text))
    issues.extend(_entrypoint_issues(root, artifact, record.get("entrypoints")))
    return issues


def _manifest_issues(manifest: ArtifactContractManifest) -> list[str]:
    if manifest.schema_version != ARTIFACT_CONTRACT_SCHEMA_VERSION:
        return ["unexpected schema_version"]
    if not manifest.artifacts:
        return ["artifacts must be non-empty"]
    return []


def validate_artifact_contract_manifest(
    *,
    root: Path,
    manifest_path: Path,
    docs_path: Path,
    required_artifacts: Sequence[str] = tuple(CORE_ARTIFACTS),
) -> ContractValidationResult:
    try:
        manifest = load_artifact_contract_manifest(manifest_path)
        docs_text = docs_path.read_text(encoding="utf-8")
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        return ContractValidationResult((str(exc),))

    issues = _manifest_issues(manifest)
    seen: set[str] = set()
    for record in manifest.artifacts:
        issues.extend(_artifact_record_issues(root, record, docs_text, seen))
    missing = sorted(set(required_artifacts) - seen)
    if missing:
        issues.append("missing core artifacts: " + ", ".join(missing))
    return ContractValidationResult(tuple(issues))
