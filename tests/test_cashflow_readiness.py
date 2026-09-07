from __future__ import annotations

import hashlib
import json

from research_contracts.cashflow_readiness import (
    build_cashflow_readiness_payload,
    evaluate_cashflow_readiness,
    main,
)


def _payload(*, outcomes: dict[str, str] | None = None) -> dict[str, object]:
    names = (
        "pit",
        "walk_forward",
        "benchmark_matrix",
        "cost",
        "final_oos",
        "cpcv",
        "regime",
        "capacity",
    )
    values = {name: "pass" for name in names}
    values.update(outcomes or {})
    entries: dict[str, dict[str, object]] = {
        "pit": {
            "pit_universe": True,
            "pit_fundamentals": True,
            "pit_industry_membership": True,
        },
        "walk_forward": {"window_count": 2, "metric": "net_excess"},
        "benchmark_matrix": {
            "cells": [
                {"universe": "top50", "horizon": "quarter", "regime": "mixed", "cost_bps": 0},
                {"universe": "csi800", "horizon": "quarter", "regime": "mixed", "cost_bps": 25},
            ]
        },
        "cost": {
            "turnover": 1.0,
            "scenarios": [
                {"cost_bps": 0, "metric": "net_return", "value": 0.1},
                {"cost_bps": 25, "metric": "net_return", "value": 0.05},
            ],
        },
        "final_oos": {
            "oos_start": "20250101",
            "metric": "net_excess",
            "frozen_before_evaluation": True,
            "retuned_after_freeze": False,
        },
        "cpcv": {"n_groups": 5, "test_groups": 2, "metric": "median_sharpe"},
        "regime": {
            "metric": "net_excess",
            "regimes": [
                {"id": "bull", "value": 0.1},
                {"id": "bear", "value": -0.1},
                {"id": "sideways", "value": 0.0},
            ],
        },
        "capacity": {
            "portfolio_values": [1_000_000, 10_000_000],
            "participation_rates": [0.05, 0.1],
            "primary_participation_rate": 0.05,
            "recommended_capacity": 1_000_000,
        },
    }
    return {
        "strategy_id": "cashflow_quality_top50_v1",
        "evidence_attestation": {"status": "verified", "bundle_sha256": "a" * 64},
        "checks": {
            name: {
                **entries[name],
                "outcome": values.get(name, "pending"),
                "evidence": f"{name}.json",
            }
            for name in names
        },
    }


def test_cashflow_readiness_passes_only_when_all_gray_gates_pass() -> None:
    decision = evaluate_cashflow_readiness(_payload())

    assert decision.decision == "candidate_for_gray_push"
    assert decision.eligible_for_gray_push is True
    assert decision.production_eligible is False
    assert decision.failed_gates == ()


def test_cashflow_readiness_requires_verified_evidence_attestation() -> None:
    payload = _payload()
    payload["evidence_attestation"] = {
        "status": "unverified",
        "bundle_sha256": "a" * 64,
    }

    decision = evaluate_cashflow_readiness(payload)

    assert decision.eligible_for_gray_push is False
    assert "evidence_integrity" in decision.failed_gates


def test_cashflow_readiness_rejects_outcome_pass_without_gate_fields() -> None:
    payload = _payload()
    payload["checks"] = dict(payload["checks"])
    payload["checks"]["capacity"] = {"outcome": "pass", "evidence": "capacity.json"}

    decision = evaluate_cashflow_readiness(payload)

    assert decision.eligible_for_gray_push is False
    assert "capacity" in decision.failed_gates


def test_cashflow_readiness_fails_closed_for_missing_or_nonpassing_gates() -> None:
    payload = _payload(outcomes={"pit": "partial", "capacity": "pending"})
    payload["checks"] = dict(payload["checks"])
    del payload["checks"]["regime"]

    decision = evaluate_cashflow_readiness(payload)

    assert decision.decision == "continue_shadow"
    assert decision.eligible_for_gray_push is False
    assert decision.production_eligible is False
    assert decision.failed_gates == ("pit", "regime", "capacity")


def test_cashflow_readiness_rejects_production_request_even_after_gray_gates() -> None:
    decision = evaluate_cashflow_readiness(_payload(), require_production=True)

    assert decision.decision == "continue_shadow"
    assert decision.eligible_for_gray_push is True
    assert decision.production_eligible is False
    assert "production_authorization" in decision.failed_gates


def test_build_readiness_receipt_attests_only_existing_complete_evidence(tmp_path) -> None:
    evidence = tmp_path / "evidence.json"
    evidence_path = tmp_path / "pit.md"
    evidence_path.write_text("verified evidence\n", encoding="utf-8")
    payload = _payload()
    payload["checks"] = {
        name: {**dict(entry), "outcome": "pass", "evidence": "pit.md"}
        for name, entry in payload["checks"].items()
    }
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    readiness = build_cashflow_readiness_payload(evidence, root=tmp_path)

    assert readiness["evidence_attestation"]["status"] == "verified"
    assert len(readiness["evidence_attestation"]["bundle_sha256"]) == 64
    assert readiness["eligible_for_gray_push"] is True


def test_build_readiness_receipt_marks_missing_evidence_unverified(tmp_path) -> None:
    evidence = tmp_path / "evidence.json"
    payload = _payload()
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    readiness = build_cashflow_readiness_payload(evidence, root=tmp_path)

    assert readiness["evidence_attestation"]["status"] == "unverified"
    assert readiness["eligible_for_gray_push"] is False
    assert "evidence_integrity" in readiness["failed_gates"]


def test_build_readiness_receipt_rejects_tampered_source_artifact(tmp_path) -> None:
    evidence = tmp_path / "evidence.json"
    source = tmp_path / "source.csv"
    source.write_text("version-one\n", encoding="utf-8")
    payload = _payload()
    payload["source_artifacts"] = [
        {"path": "source.csv", "sha256": "a" * 64}
    ]
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    readiness = build_cashflow_readiness_payload(evidence, root=tmp_path)

    assert readiness["evidence_attestation"]["status"] == "unverified"
    assert readiness["evidence_attestation"]["source_artifact_errors"]
    assert "evidence_integrity" in readiness["failed_gates"]


def test_readiness_cli_writes_blocked_receipt_and_exit_code(tmp_path) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps(_payload()), encoding="utf-8")
    output = tmp_path / "readiness.json"

    exit_code = main(
        [
            "--evidence-bundle",
            str(evidence),
            "--root",
            str(tmp_path),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 20
    assert json.loads(output.read_text(encoding="utf-8"))["eligible_for_gray_push"] is False


def test_runtime_pit_audit_overrides_stale_bundle_reference_and_blocks(tmp_path) -> None:
    evidence = tmp_path / "evidence.json"
    runtime_audit = tmp_path / "runtime-pit.json"
    runtime_audit.write_text(
        json.dumps(
            {
                "status": "blocked",
                "historical_revision_safe": False,
                "blockers": ["historical_revision_not_safe"],
            }
        ),
        encoding="utf-8",
    )
    payload = _payload()
    for entry in payload["checks"].values():
        entry["evidence"] = "runtime-pit.json"
    payload["source_artifacts"] = [
        {
            "path": "runtime-pit.json",
            "sha256": hashlib.sha256(runtime_audit.read_bytes()).hexdigest(),
        }
    ]
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    readiness = build_cashflow_readiness_payload(
        evidence,
        root=tmp_path,
        pit_audit_path=runtime_audit,
    )

    assert readiness["checks"]["pit"]["evidence"] == str(runtime_audit.resolve())
    assert readiness["checks"]["pit"]["outcome"] == "partial"
    assert "pit" in readiness["failed_gates"]
    assert readiness["evidence_attestation"]["source_artifact_errors"] == []
