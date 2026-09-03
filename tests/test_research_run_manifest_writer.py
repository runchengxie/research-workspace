from __future__ import annotations

import json
from typing import Any

import pytest

from research_contracts import build_research_run_manifest, validate_research_run_manifest


def _clock() -> dict[str, str]:
    return {
        "schema_version": "research.clock.v1",
        "timezone": "UTC",
        "information_cutoff_at": "2026-01-05T15:00:00+00:00",
        "signal_at": "2026-01-05T15:00:00+00:00",
        "decision_at": "2026-01-05T15:00:00+00:00",
        "earliest_order_at": "2026-01-06T09:30:00+00:00",
        "execution_window_start_at": "2026-01-06T09:30:00+00:00",
        "execution_window_end_at": "2026-01-06T15:00:00+00:00",
        "valuation_at": "2026-01-06T15:00:00+00:00",
        "timing_policy_id": "example.close_to_next_open.v1",
        "trading_calendar_ref": "example.exchange.v1",
    }


def _write_run(tmp_path) -> None:
    (tmp_path / "config.used.yml").write_text("example: true\n", encoding="utf-8")
    (tmp_path / "signals.parquet").write_bytes(b"signal")
    (tmp_path / "inputs.lock.json").write_text("{}\n", encoding="utf-8")
    bundle = tmp_path / "backtest_bundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_text('{"schema_version": 1}\n', encoding="utf-8")


def test_build_and_validate_research_run_manifest(tmp_path) -> None:
    _write_run(tmp_path)
    path = build_research_run_manifest(
        tmp_path,
        run_id="demo-001",
        strategy_ref="example.v1",
        research_purpose="promotion_evidence",
        evidence_tier="execution_aware",
        clock=_clock(),
        producer_versions=[{"repository": "example-owner", "commit": "abc123"}],
        data_refs=[{"artifact_id": "inputs.lock", "path": "inputs.lock.json"}],
        signal_refs=[{"artifact_id": "signals", "path": "signals.parquet"}],
    )

    manifest = validate_research_run_manifest(path)

    assert manifest.evidence_tier == "execution_aware"
    assert manifest.signal_refs[0].sha256
    assert (
        json.loads(path.read_text(encoding="utf-8"))["schema_version"] == "research.backtest-run.v1"
    )


def test_execution_aware_manifest_requires_complete_clock(tmp_path) -> None:
    _write_run(tmp_path)
    clock = _clock()
    del clock["execution_window_end_at"]

    with pytest.raises(ValueError, match="execution_window_end_at is required"):
        build_research_run_manifest(
            tmp_path,
            run_id="demo-002",
            strategy_ref="example.v1",
            research_purpose="diagnostic",
            evidence_tier="execution_aware",
            clock=clock,
            producer_versions=[{"repository": "example-owner", "commit": "abc123"}],
            data_refs=[],
            signal_refs=[],
        )


def test_manifest_is_append_only(tmp_path) -> None:
    _write_run(tmp_path)
    kwargs: dict[str, Any] = {
        "run_id": "demo-003",
        "strategy_ref": "example.v1",
        "research_purpose": "diagnostic",
        "evidence_tier": "diagnostic",
        "clock": _clock(),
        "producer_versions": [{"repository": "example-owner", "commit": "abc123"}],
        "data_refs": [],
        "signal_refs": [],
    }

    build_research_run_manifest(tmp_path, **kwargs)
    with pytest.raises(FileExistsError):
        build_research_run_manifest(tmp_path, **kwargs)
