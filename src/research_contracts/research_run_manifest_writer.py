"""Build the immutable research run manifest for a pipeline run."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .file_receipts import canonical_json_sha256, file_sha256
from .research_clock import validate_research_clock
from .research_run_manifest import ArtifactRef, ProducerVersion, ResearchRunManifest

MANIFEST_FILENAME = "research-run.manifest.json"


def _resolve_artifact_ref(run_dir: Path, item: Mapping[str, Any]) -> ArtifactRef:
    path_value = item.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError("artifact references require a non-empty path")
    path = (
        (run_dir / path_value).resolve() if not Path(path_value).is_absolute() else Path(path_value)
    )
    if not path.is_file():
        raise FileNotFoundError(f"artifact reference does not exist: {path}")
    artifact_id = str(item.get("artifact_id") or path.name).strip()
    return ArtifactRef(artifact_id=artifact_id, sha256=file_sha256(path), path=path_value)


def build_research_run_manifest(
    run_dir: Path,
    *,
    run_id: str,
    strategy_ref: str,
    research_purpose: str,
    evidence_tier: str,
    clock: Mapping[str, Any],
    producer_versions: Sequence[Mapping[str, Any]],
    data_refs: Sequence[Mapping[str, Any]],
    signal_refs: Sequence[Mapping[str, Any]],
    portfolio_result_path: str = "backtest_bundle/manifest.json",
    benchmark_ref: Mapping[str, Any] | None = None,
    evidence_refs: Sequence[Mapping[str, Any]] = (),
    output_path: Path | None = None,
) -> Path:
    """Create and atomically publish a validated run manifest.

    Paths in artifact references are relative to ``run_dir``.  Their hashes are
    always calculated from the files on disk, so callers cannot accidentally
    publish stale or caller-supplied digests.
    """

    root = run_dir.resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    config_path = root / "config.used.yml"
    if not config_path.is_file():
        raise FileNotFoundError(config_path)

    portfolio_path = (root / portfolio_result_path).resolve()
    if not portfolio_path.is_file():
        raise FileNotFoundError(portfolio_path)
    payload = ResearchRunManifest(
        run_id=run_id,
        strategy_ref=strategy_ref,
        research_purpose=research_purpose,
        evidence_tier=evidence_tier,
        clock=validate_research_clock(clock, require_execution=evidence_tier == "execution_aware"),
        configuration_sha256=file_sha256(config_path),
        producer_versions=tuple(ProducerVersion.from_mapping(item) for item in producer_versions),
        data_refs=tuple(_resolve_artifact_ref(root, item) for item in data_refs),
        signal_refs=tuple(_resolve_artifact_ref(root, item) for item in signal_refs),
        portfolio_result_ref=ArtifactRef(
            artifact_id="portfolio.backtest.bundle",
            sha256=file_sha256(portfolio_path),
            path=portfolio_result_path,
        ),
        benchmark_ref=(
            _resolve_artifact_ref(root, benchmark_ref) if benchmark_ref is not None else None
        ),
        evidence_refs=tuple(_resolve_artifact_ref(root, item) for item in evidence_refs),
        created_at=datetime.now(UTC),
    )
    destination = (output_path or root / MANIFEST_FILENAME).resolve()
    if destination.exists():
        raise FileExistsError(f"research run manifest already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload.to_mapping(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, destination)
    return destination


def validate_research_run_manifest(path: Path) -> ResearchRunManifest:
    """Load a manifest and validate its schema and evidence tier."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("research run manifest must contain a JSON object")
    manifest = ResearchRunManifest.from_mapping(payload)
    if canonical_json_sha256(manifest.to_mapping()) != canonical_json_sha256(payload):
        raise ValueError("research run manifest is not canonical JSON")
    return manifest


__all__ = ["MANIFEST_FILENAME", "build_research_run_manifest", "validate_research_run_manifest"]
