"""Artifact producer/consumer projection for workspace architecture."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from workspace_architecture_model import ArchitectureModel, Graph, load_mapping, strings


def _known_reference(model: ArchitectureModel, identifier: str) -> bool:
    return identifier in model.by_id or identifier in model.external_components


def _reference_error(
    model: ArchitectureModel,
    artifact: str,
    identifier: str,
    field: str,
) -> str | None:
    if not identifier or _known_reference(model, identifier):
        return None
    return f"{artifact}: unknown {field} component {identifier!r}"


def _producer_edges(
    model: ArchitectureModel,
    artifact: str,
    artifact_node: str,
    raw: Mapping[str, Any],
) -> tuple[list[dict[str, str]], list[str]]:
    edges: list[dict[str, str]] = []
    errors: list[str] = []
    producer = str(raw.get("producer", "")).strip()
    error = _reference_error(model, artifact, producer, "producer")
    if error:
        errors.append(error)
    if producer:
        edges.append({"source": producer, "target": artifact_node, "kind": "produces"})
    for identifier in strings(raw.get("external_producers")):
        error = _reference_error(model, artifact, identifier, "external producer")
        if error:
            errors.append(error)
        edges.append({"source": identifier, "target": artifact_node, "kind": "produces"})
    return edges, errors


def _consumer_edges(
    model: ArchitectureModel,
    artifact: str,
    artifact_node: str,
    raw: Mapping[str, Any],
) -> tuple[list[dict[str, str]], list[str]]:
    edges: list[dict[str, str]] = []
    errors: list[str] = []
    for identifier in strings(raw.get("consumers")):
        error = _reference_error(model, artifact, identifier, "consumer")
        if error:
            errors.append(error)
        edges.append({"source": artifact_node, "target": identifier, "kind": "consumes"})
    return edges, errors


def _artifact_record(
    model: ArchitectureModel,
    raw: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, str]], list[str]]:
    artifact = str(raw.get("artifact", "")).strip()
    if not artifact:
        return None, [], []
    artifact_node = f"artifact:{artifact}"
    owner = str(raw.get("owner", "")).strip()
    errors: list[str] = []
    owner_error = _reference_error(model, artifact, owner, "owner")
    if owner_error:
        errors.append(owner_error)
    producer_edges, producer_errors = _producer_edges(model, artifact, artifact_node, raw)
    consumer_edges, consumer_errors = _consumer_edges(model, artifact, artifact_node, raw)
    node = {
        "id": artifact_node,
        "artifact": artifact,
        "owner": owner,
        "contract": str(raw.get("contract", "")).strip(),
        "schema_version": raw.get("schema_version"),
    }
    return (
        node,
        [*producer_edges, *consumer_edges],
        [
            *errors,
            *producer_errors,
            *consumer_errors,
        ],
    )


def build_artifact_graph(
    root: Path,
    model: ArchitectureModel,
    *,
    manifest_path: Path | None = None,
) -> Graph:
    path = manifest_path or root / "docs" / "artifact-contracts.yml"
    if not path.exists():
        return {
            "schema_version": model.schema_version,
            "kind": "artifact_graph",
            "nodes": [],
            "edges": [],
            "errors": [],
            "warnings": [f"missing artifact manifest: {path}"],
        }
    payload = load_mapping(path)
    raw_records = payload.get("artifacts")
    records = raw_records if isinstance(raw_records, list) else []
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    errors: list[str] = []
    for raw in records:
        if not isinstance(raw, Mapping):
            continue
        node, record_edges, record_errors = _artifact_record(model, raw)
        if node:
            nodes.append(node)
        edges.extend(record_edges)
        errors.extend(record_errors)
    nodes.sort(key=lambda node: str(node["id"]))
    edges.sort(key=lambda edge: (edge["source"], edge["target"], edge["kind"]))
    return {
        "schema_version": model.schema_version,
        "kind": "artifact_graph",
        "nodes": nodes,
        "edges": edges,
        "errors": sorted(set(errors)),
        "warnings": [],
    }
