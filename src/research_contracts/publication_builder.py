"""Build filesystem publication bundles from explicitly declared projection files."""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from .file_receipts import file_sha256
from .platform_publication import PlatformPublicationArtifact, PlatformPublicationManifest


def _required_text(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    return text


def _consumer_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("consumers must be a list")
    consumers = tuple(_required_text(item, "consumers[]") for item in value)
    if not consumers:
        raise ValueError("consumers must not be empty")
    return consumers


def build_platform_publication(
    *,
    artifacts: Sequence[Mapping[str, Any]],
    output_root: str | Path,
    generated_at: datetime,
    producer_repository: str,
    producer_commit: str,
    run_id: str,
) -> PlatformPublicationManifest:
    """Create a clean publication directory and canonical manifest.

    ``source_path`` is a build-only field. It is used to copy one approved
    projection into the bundle and is never serialized into the publication
    manifest, which prevents local filesystem details from crossing the handoff.
    """

    if not artifacts:
        raise ValueError("artifacts must not be empty")
    destination = Path(output_root).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.staging-",
            dir=destination.parent,
        )
    )
    try:
        manifest_artifacts: list[PlatformPublicationArtifact] = []
        for index, spec in enumerate(artifacts):
            if not isinstance(spec, Mapping):
                raise ValueError(f"artifacts[{index}] must be an object")
            source = Path(spec.get("source_path", "")).expanduser().resolve()
            if not source.is_file():
                raise FileNotFoundError(f"publication source is missing: {source}")

            provisional = PlatformPublicationArtifact(
                artifact_id=_required_text(spec.get("artifact_id"), "artifact_id"),
                relative_path=_required_text(spec.get("relative_path"), "relative_path"),
                schema_version=_required_text(spec.get("schema_version"), "schema_version"),
                sha256="0" * 64,
                media_type=_required_text(spec.get("media_type"), "media_type"),
                audience=_required_text(spec.get("audience"), "audience"),
                consumers=_consumer_tuple(spec.get("consumers")),
            )
            target = staging / provisional.relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest_artifacts.append(
                PlatformPublicationArtifact(
                    artifact_id=provisional.artifact_id,
                    relative_path=provisional.relative_path,
                    schema_version=provisional.schema_version,
                    sha256=file_sha256(target),
                    media_type=provisional.media_type,
                    audience=provisional.audience,
                    consumers=provisional.consumers,
                )
            )

        manifest = PlatformPublicationManifest(
            generated_at=generated_at,
            producer_repository=producer_repository,
            producer_commit=producer_commit,
            run_id=run_id,
            artifacts=tuple(manifest_artifacts),
        )
        (staging / "platform-publication.json").write_text(
            json.dumps(manifest.to_mapping(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if destination.exists():
            shutil.rmtree(destination)
        staging.replace(destination)
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)


__all__ = ["build_platform_publication"]
