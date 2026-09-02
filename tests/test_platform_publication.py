from __future__ import annotations

from datetime import datetime, timezone

import pytest

from research_contracts import (
    PLATFORM_PUBLICATION_SCHEMA_VERSION,
    PlatformPublicationArtifact,
    PlatformPublicationManifest,
    load_platform_publication_manifest,
)


SHA = "a" * 64


def _manifest(*, audience: str = "public") -> PlatformPublicationManifest:
    return PlatformPublicationManifest(
        generated_at=datetime(2026, 9, 2, 5, 20, tzinfo=timezone.utc),
        producer_repository="runchengxie/research-workspace",
        producer_commit="abc123",
        run_id="research-20260902",
        artifacts=(
            PlatformPublicationArtifact(
                artifact_id="strategy.dailywatch20.evidence",
                relative_path="strategies/dailywatch20-evidence.json",
                schema_version="trading_research.strategy_evidence.v1",
                sha256=SHA,
                media_type="application/json",
                audience=audience,
                consumers=("trading-research-dashboard", "market-intel"),
            ),
        ),
    )


def test_platform_publication_round_trip_preserves_public_projection() -> None:
    manifest = _manifest()

    payload = manifest.to_mapping()
    loaded = load_platform_publication_manifest(payload)

    assert payload["schema_version"] == PLATFORM_PUBLICATION_SCHEMA_VERSION
    assert loaded == manifest
    assert loaded.artifacts[0].relative_path == "strategies/dailywatch20-evidence.json"


def test_platform_publication_rejects_path_escape() -> None:
    with pytest.raises(ValueError, match="relative_path"):
        PlatformPublicationArtifact(
            artifact_id="bad",
            relative_path="../private/model.pkl",
            schema_version="example.v1",
            sha256=SHA,
            media_type="application/octet-stream",
            audience="public",
            consumers=("trading-research-dashboard",),
        )


def test_platform_publication_rejects_bundle_root_as_artifact_path() -> None:
    with pytest.raises(ValueError, match="relative_path"):
        PlatformPublicationArtifact(
            artifact_id="bad-root",
            relative_path=".",
            schema_version="example.v1",
            sha256=SHA,
            media_type="application/json",
            audience="public",
            consumers=("trading-research-dashboard",),
        )


def test_dashboard_consumer_rejects_internal_artifact() -> None:
    payload = _manifest(audience="internal").to_mapping()

    with pytest.raises(ValueError, match="internal"):
        load_platform_publication_manifest(
            payload,
            consumer="trading-research-dashboard",
            allow_internal=False,
        )


def test_consumer_filter_returns_only_declared_artifacts() -> None:
    manifest = PlatformPublicationManifest(
        generated_at=datetime(2026, 9, 2, 5, 20, tzinfo=timezone.utc),
        producer_repository="runchengxie/research-workspace",
        producer_commit="abc123",
        run_id="research-20260902",
        artifacts=(
            PlatformPublicationArtifact(
                artifact_id="dashboard.strategy",
                relative_path="strategies/strategy.json",
                schema_version="strategy.v1",
                sha256=SHA,
                media_type="application/json",
                audience="public",
                consumers=("trading-research-dashboard",),
            ),
            PlatformPublicationArtifact(
                artifact_id="intel.digest",
                relative_path="intel/digest.json",
                schema_version="digest.v1",
                sha256="b" * 64,
                media_type="application/json",
                audience="internal",
                consumers=("market-intel",),
            ),
        ),
    )

    dashboard = manifest.for_consumer("trading-research-dashboard")

    assert [artifact.artifact_id for artifact in dashboard] == ["dashboard.strategy"]
