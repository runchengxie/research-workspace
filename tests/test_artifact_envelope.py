from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from research_contracts import (  # noqa: E402
    ArtifactEnvelopeV2,
    LegacyArtifactMetadata,
    LineageInput,
    ProducerIdentity,
    attach_artifact_envelope_v2,
    canonical_json_sha256,
    file_sha256,
    read_artifact_envelope,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> dict[str, object]:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_v1_metadata_remains_readable_without_migration() -> None:
    payload = _fixture("artifact_envelope_v1.json")

    result = read_artifact_envelope(payload)

    assert isinstance(result, LegacyArtifactMetadata)
    assert result.payload == payload


def test_v2_envelope_round_trips_with_target_context() -> None:
    payload = _fixture("artifact_envelope_v2.json")

    result = read_artifact_envelope(payload)

    assert isinstance(result, ArtifactEnvelopeV2)
    assert result.created_at.utcoffset() is not None
    assert result.producer.backend == "native"
    assert result.lineage[0].artifact_id == "positions-demo"
    assert result.target_handoff is not None
    assert result.target_handoff.account_scope == "paper"
    assert ArtifactEnvelopeV2.from_mapping(result.to_mapping()) == result


def test_v2_migration_is_additive_and_does_not_mutate_legacy_payload() -> None:
    legacy = _fixture("artifact_envelope_v1.json")
    envelope_payload = _fixture("artifact_envelope_v2.json")["artifact_envelope"]
    assert isinstance(envelope_payload, dict)
    envelope = ArtifactEnvelopeV2.from_mapping(envelope_payload)

    migrated = attach_artifact_envelope_v2(legacy, envelope)

    assert "artifact_envelope" not in legacy
    assert migrated["contract"] == legacy["contract"]
    assert read_artifact_envelope(migrated) == envelope


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("created_at", "2026-07-13T09:30:00", "timezone-aware"),
        ("configuration_sha256", "not-a-hash", "SHA-256"),
        ("content_sha256", "A" * 64, "lowercase SHA-256"),
    ],
)
def test_v2_rejects_non_canonical_provenance(field: str, value: str, message: str) -> None:
    payload = _fixture("artifact_envelope_v2.json")["artifact_envelope"]
    assert isinstance(payload, dict)
    payload[field] = value

    with pytest.raises(ValueError, match=message):
        ArtifactEnvelopeV2.from_mapping(payload)


def test_target_validity_must_be_ordered_and_timezone_aware() -> None:
    payload = _fixture("artifact_envelope_v2.json")["artifact_envelope"]
    assert isinstance(payload, dict)
    target_handoff = payload["target_handoff"]
    assert isinstance(target_handoff, dict)
    target_handoff["expires_at"] = target_handoff["valid_from"]

    with pytest.raises(ValueError, match="must be after"):
        ArtifactEnvelopeV2.from_mapping(payload)


def test_datetime_objects_are_accepted_only_when_timezone_aware() -> None:
    payload = _fixture("artifact_envelope_v2.json")["artifact_envelope"]
    assert isinstance(payload, dict)
    payload["created_at"] = datetime(2026, 7, 13, 9, 30)

    with pytest.raises(ValueError, match="timezone-aware"):
        ArtifactEnvelopeV2.from_mapping(payload)


def _demo_envelope(
    *,
    content_sha256: str = "b" * 64,
    configuration_sha256: str = "a" * 64,
) -> ArtifactEnvelopeV2:
    return ArtifactEnvelopeV2(
        schema_version="research.artifact-envelope.v2",
        artifact_id="signals-demo",
        artifact_type="signals.parquet",
        run_id="run-demo",
        created_at=datetime(2026, 7, 13, 9, 30, tzinfo=timezone(timedelta(hours=8))),
        producer=ProducerIdentity(
            repository="alpha-research",
            version="0.4.0",
            commit="0123456789abcdef",
            backend="native",
        ),
        configuration_sha256=configuration_sha256,
        content_sha256=content_sha256,
        lineage=(LineageInput("research_features.parquet", "c" * 64),),
    )


def test_v2_content_hash_and_config_hash_round_trip_verified() -> None:
    core = {"contract": "alpha_research.signals metadata", "file": "signals.parquet", "rows": 2}
    content_hash = canonical_json_sha256(core)
    config_hash = canonical_json_sha256({"model_version": "ridge:demo"})

    migrated = attach_artifact_envelope_v2(
        core,
        _demo_envelope(content_sha256=content_hash, configuration_sha256=config_hash),
    )
    result = read_artifact_envelope(migrated)

    assert isinstance(result, ArtifactEnvelopeV2)
    assert result.content_sha256 == content_hash == canonical_json_sha256(core)
    assert result.configuration_sha256 == config_hash
    assert result.content_sha256 != result.configuration_sha256


def test_v2_timestamp_round_trips_iso8601_with_utc_offset() -> None:
    envelope = _demo_envelope()

    payload = envelope.to_mapping()
    result = ArtifactEnvelopeV2.from_mapping(payload)

    assert result.created_at == envelope.created_at
    assert result.created_at.tzinfo is not None
    assert result.created_at.utcoffset() == timedelta(hours=8)
    assert result.to_mapping()["created_at"] == "2026-07-13T09:30:00+08:00"


def test_v2_lineage_and_producer_identity_round_trip() -> None:
    envelope = _demo_envelope()

    result = ArtifactEnvelopeV2.from_mapping(envelope.to_mapping())

    assert result.lineage == (LineageInput("research_features.parquet", "c" * 64),)
    assert result.producer.repository == "alpha-research"
    assert result.producer.version == "0.4.0"
    assert result.producer.commit == "0123456789abcdef"
    assert result.producer.backend == "native"
    assert result.producer.backend_version is None


def test_v2_content_hash_matches_written_file(tmp_path) -> None:
    artifact_path = tmp_path / "signals.parquet"
    artifact_path.write_bytes(b"demo-parquet-bytes")

    envelope = _demo_envelope(content_sha256=file_sha256(artifact_path))
    migrated = attach_artifact_envelope_v2({"file": artifact_path.name}, envelope)

    result = read_artifact_envelope(migrated)
    assert isinstance(result, ArtifactEnvelopeV2)
    assert result.content_sha256 == file_sha256(artifact_path)


def test_v2_rejects_missing_or_invalid_lineage_entries() -> None:
    payload = _fixture("artifact_envelope_v2.json")["artifact_envelope"]
    assert isinstance(payload, dict)
    payload["lineage"] = "not-a-list"

    with pytest.raises(ValueError, match="lineage must be a list"):
        ArtifactEnvelopeV2.from_mapping(payload)

    payload["lineage"] = [{"artifact_id": "positions-demo", "sha256": "not-a-hash"}]
    with pytest.raises(ValueError, match="SHA-256"):
        ArtifactEnvelopeV2.from_mapping(payload)

    payload["lineage"] = [{"artifact_id": "positions-demo"}]
    with pytest.raises(ValueError, match="sha256"):
        ArtifactEnvelopeV2.from_mapping(payload)


def test_v2_producer_identity_requires_all_fields() -> None:
    payload = _fixture("artifact_envelope_v2.json")["artifact_envelope"]
    assert isinstance(payload, dict)
    producer = dict(payload["producer"])  # type: ignore[arg-type]

    for field in ("repository", "version", "commit", "backend"):
        broken = dict(producer)
        broken[field] = " "
        payload["producer"] = broken
        with pytest.raises(ValueError, match=field):
            ArtifactEnvelopeV2.from_mapping(payload)


def test_v2_missing_container_raises_when_legacy_disallowed() -> None:
    payload = _fixture("artifact_envelope_v1.json")

    with pytest.raises(ValueError, match="artifact_envelope is required"):
        read_artifact_envelope(payload, allow_legacy=False)
