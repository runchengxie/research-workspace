from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from research_contracts import (  # noqa: E402
    ArtifactEnvelopeV2,
    LegacyArtifactMetadata,
    attach_artifact_envelope_v2,
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
