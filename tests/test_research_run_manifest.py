from datetime import datetime

import pytest

from research_contracts.research_run_manifest import (
    ArtifactRef,
    ProducerVersion,
    ResearchRunManifest,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def clock_payload():
    return {
        "schema_version": "research.clock.v1",
        "timezone": "Asia/Shanghai",
        "information_cutoff_at": "2026-09-02T15:00:00+08:00",
        "signal_at": "2026-09-02T15:01:00+08:00",
        "decision_at": "2026-09-02T15:02:00+08:00",
        "earliest_order_at": "2026-09-03T09:15:00+08:00",
        "execution_window_start_at": "2026-09-03T09:30:00+08:00",
        "execution_window_end_at": "2026-09-03T10:00:00+08:00",
        "valuation_at": "2026-09-03T15:00:00+08:00",
        "timing_policy_id": "a-share.close-next-open.v1",
        "trading_calendar_ref": "sse-szse-20260902",
    }


def valid_payload():
    return {
        "schema_version": "research.backtest-run.v1",
        "run_id": "run-20260902-001",
        "strategy_ref": "daily-watch20",
        "research_purpose": "promotion_evidence",
        "evidence_tier": "execution_aware",
        "clock": clock_payload(),
        "configuration_sha256": SHA_A,
        "producer_versions": [
            {"repository": "alpha-research", "commit": "abc123", "version": "2.0.0"},
            {"repository": "portfolio-backtester", "commit": "def456"},
        ],
        "data_refs": [
            {
                "artifact_id": "dataset:a-share-daily",
                "sha256": SHA_B,
                "path": "metadata/daily.json",
            }
        ],
        "signal_refs": [{"artifact_id": "signals:canonical", "sha256": SHA_C}],
        "portfolio_result_ref": {
            "artifact_id": "backtest:canonical",
            "sha256": SHA_A,
            "path": "backtest_result/manifest.json",
        },
        "benchmark_ref": {"artifact_id": "benchmark:csi500", "sha256": SHA_B},
        "evidence_refs": [{"artifact_id": "capacity:receipt", "sha256": SHA_C}],
        "created_at": "2026-09-03T16:00:00+08:00",
    }


def test_research_run_manifest_round_trip():
    manifest = ResearchRunManifest.from_mapping(valid_payload())
    restored = ResearchRunManifest.from_mapping(manifest.to_mapping())
    assert restored == manifest
    assert isinstance(manifest.created_at, datetime)
    assert isinstance(manifest.portfolio_result_ref, ArtifactRef)
    assert isinstance(manifest.producer_versions[0], ProducerVersion)


def test_manifest_rejects_non_sha256_ref():
    payload = valid_payload()
    payload["signal_refs"][0]["sha256"] = "deadbeef"
    with pytest.raises(
        ValueError,
        match="signal_refs.sha256 must be a lowercase SHA-256 digest",
    ):
        ResearchRunManifest.from_mapping(payload)


def test_manifest_rejects_duplicate_artifact_refs():
    payload = valid_payload()
    payload["data_refs"].append(dict(payload["data_refs"][0]))
    with pytest.raises(ValueError, match="data_refs contains duplicate artifact_id"):
        ResearchRunManifest.from_mapping(payload)


def test_manifest_rejects_duplicate_producer_repository():
    payload = valid_payload()
    payload["producer_versions"].append({"repository": "alpha-research", "commit": "other"})
    with pytest.raises(ValueError, match="producer_versions contains duplicate repository"):
        ResearchRunManifest.from_mapping(payload)


def test_manifest_rejects_unknown_evidence_tier():
    payload = valid_payload()
    payload["evidence_tier"] = "looks_good_to_me"
    with pytest.raises(ValueError, match="unsupported evidence_tier"):
        ResearchRunManifest.from_mapping(payload)


def test_manifest_rejects_naive_created_at():
    payload = valid_payload()
    payload["created_at"] = "2026-09-03T16:00:00"
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        ResearchRunManifest.from_mapping(payload)
