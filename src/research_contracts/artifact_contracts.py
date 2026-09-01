from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARTIFACT_CONTRACT_SCHEMA_VERSION = "artifact_contracts.v1"
ARTIFACT_ENVELOPE_SCHEMA_VERSION = "research.artifact-envelope.v2"
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
    artifact_envelope: Mapping[str, Any]
    artifacts: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ArtifactContractManifest:
        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, list):
            artifacts = []
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            artifact_envelope=(
                payload["artifact_envelope"]
                if isinstance(payload.get("artifact_envelope"), Mapping)
                else {}
            ),
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


def _load_contract_docs(docs_path: Path) -> str:
    """Load the main contract page and owner-focused contract extensions."""

    documents = [docs_path]
    extension_dir = docs_path.parent / "contracts.d"
    if extension_dir.is_dir():
        documents.extend(sorted(extension_dir.glob("*.md")))
    return "\n\n".join(path.read_text(encoding="utf-8") for path in documents)


def _docs_sync_issues(record: Mapping[str, Any], docs_text: str) -> list[str]:
    issues: list[str] = []
    artifact = str(record.get("artifact", "")).strip()
    contract = str(record.get("contract", "")).strip()
    owner = str(record.get("owner", "")).strip()
    expected_tokens = [
        (artifact, f"{artifact}: missing from docs/contracts.md or docs/contracts.d"),
        (contract, f"{artifact}: contract {contract!r} missing from contract docs"),
        (owner, f"{artifact}: owner {owner!r} missing from contract docs"),
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


def _exactly_one_group_issues(artifact: str, record: Mapping[str, Any]) -> list[str]:
    raw_groups = record.get("exactly_one_of_fields")
    if raw_groups is None:
        return []
    if not isinstance(raw_groups, list) or not raw_groups:
        return [f"{artifact}: exactly_one_of_fields must be a non-empty list"]

    required = set(_strings(record.get("required_fields")))
    issues: list[str] = []
    for raw_group in raw_groups:
        fields = _strings(raw_group)
        if len(fields) < 2:
            issues.append(f"{artifact}: exactly_one_of_fields groups need at least two fields")
            continue
        if len(fields) != len(set(fields)):
            issues.append(f"{artifact}: exactly_one_of_fields groups must not contain duplicates")
        overlap = sorted(required.intersection(fields))
        if overlap:
            issues.append(
                f"{artifact}: exactly_one_of_fields overlap required_fields: {', '.join(overlap)}"
            )
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
    issues.extend(_exactly_one_group_issues(artifact, record))
    issues.extend(_docs_sync_issues(record, docs_text))
    issues.extend(_entrypoint_issues(root, artifact, record.get("entrypoints")))
    return issues


def _manifest_issues(manifest: ArtifactContractManifest) -> list[str]:
    if manifest.schema_version != ARTIFACT_CONTRACT_SCHEMA_VERSION:
        return ["unexpected schema_version"]
    if not manifest.artifacts:
        return ["artifacts must be non-empty"]
    envelope = manifest.artifact_envelope
    issues: list[str] = []
    if envelope.get("schema_version") != ARTIFACT_ENVELOPE_SCHEMA_VERSION:
        issues.append("unexpected artifact envelope schema_version")
    if envelope.get("write_mode") != "opt_in":
        issues.append("artifact envelope write_mode must be opt_in")
    if envelope.get("container_key") != "artifact_envelope":
        issues.append("artifact envelope container_key must be artifact_envelope")
    if not _strings(envelope.get("required_fields")):
        issues.append("artifact envelope required_fields must be non-empty")
    return issues


def validate_artifact_contract_manifest(
    *,
    root: Path,
    manifest_path: Path,
    docs_path: Path,
    required_artifacts: Sequence[str] = tuple(CORE_ARTIFACTS),
) -> ContractValidationResult:
    try:
        manifest = load_artifact_contract_manifest(manifest_path)
        docs_text = _load_contract_docs(docs_path)
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
