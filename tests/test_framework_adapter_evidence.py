from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "framework_adapter_evidence.py"
if str(SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT.parent))

spec = importlib.util.spec_from_file_location("framework_adapter_evidence", SCRIPT)
framework_adapter_evidence = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = framework_adapter_evidence
spec.loader.exec_module(framework_adapter_evidence)


def _write(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _alpha() -> dict[str, object]:
    return {
        "schema": "backend_comparison_replay_receipt.v1",
        "source_schema": "backend_comparison.v1",
        "source_report": {
            "artifact_type": "backend_comparison",
            "schema_version": "v1",
            "path": "/tmp/comparison.json",
            "sha256": "a" * 64,
            "media_type": "application/json",
        },
        "source_report_sha256": "a" * 64,
        "verification_method": "artifact-digest-and-decision-replay",
        "comparison": {
            "native_backend_id": "native",
            "candidate_backend_id": "qlib",
        },
        "decision": {"status": "promotable", "failures": []},
        "thresholds": {"min_overlap_ratio": 1.0},
        "replay_verified": True,
    }


def _backtest() -> dict[str, object]:
    return {
        "schema": "backtest_differential.v1",
        "reference_backend": "native-a-share-replay",
        "candidate_backend": "qlib-backtest",
        "accepted": True,
        "comparisons": [
            {
                "dimension": dimension,
                "status": "matched",
                "details": {},
                "explanation": None,
            }
            for dimension in ("dates", "positions", "turnover", "cost", "pnl")
        ],
    }


def _execution() -> dict[str, object]:
    expected_state = {
        "submission_state": "ACCEPTED",
        "order_status": "ACCEPTED",
        "broker_order_id": "broker-order-001",
        "filled_quantity": "0",
        "remaining_quantity": "10",
        "submission_attempt_count": 1,
        "order_event_count": 1,
        "fill_count": 0,
        "journal_sequence": 4,
        "transport_submit_calls": 1,
        "idempotent_retry_blocked": True,
        "state_monotonic": True,
    }
    reconciliation = {
        "status": "resolved",
        "result": "owner_verified",
        "action": "no_action",
        "evidence_count": 1,
        "kill_switch": False,
        "position_drift": None,
    }
    return {
        "schema": "execution_recovery_matrix.v1",
        "mode": "shadow",
        "deterministic": True,
        "live_broker_access": False,
        "scenarios": [
            {
                "id": identifier,
                "status": "passed",
                "expected_state": expected_state,
                "reconciliation": reconciliation,
            }
            for identifier in framework_adapter_evidence.RECOVERY_SCENARIOS
        ],
    }


def _release_manifest() -> dict[str, object]:
    return {
        "schema_version": "framework_adapter_release.v1",
        "release_id": "framework-adapters-test",
        "components": [
            {
                "repository": repository,
                "candidate_commit": identifier * 40,
                "merge_state": "draft",
                "merged_commit": None,
            }
            for repository, identifier in (
                ("market-data-platform", "a"),
                ("alpha-research", "b"),
                ("portfolio-backtester", "c"),
                ("strategy-pipeline", "d"),
                ("quant-execution-engine", "e"),
            )
        ],
    }


def test_build_evidence_envelope_accepts_framework_neutral_receipts(tmp_path: Path) -> None:
    alpha = _write(tmp_path / "alpha.json", _alpha())
    backtest = _write(tmp_path / "backtest.json", _backtest())
    execution = _write(tmp_path / "execution.json", _execution())
    release = _write(tmp_path / "release.json", _release_manifest())

    envelope = framework_adapter_evidence.build_evidence_envelope(
        alpha,
        backtest,
        execution,
        release,
    )

    assert envelope["schema"] == "framework_adapter_integration_evidence.v1"
    assert envelope["status"] == "accepted"
    assert envelope["issues"] == []
    assert envelope["release"]["release_id"] == "framework-adapters-test"
    assert set(envelope["evidence"]) == {"alpha", "backtest", "execution"}
    assert all(len(item["sha256"]) == 64 for item in envelope["evidence"].values())
    assert {item["name"] for item in envelope["evidence"].values()} == {
        "alpha.json",
        "backtest.json",
        "execution.json",
    }


def test_evidence_requires_owner_replay_and_every_recovery_scenario(tmp_path: Path) -> None:
    alpha_payload = _alpha()
    alpha_payload["replay_verified"] = False
    execution_payload = _execution()
    execution_payload["scenarios"] = execution_payload["scenarios"][:-1]

    envelope = framework_adapter_evidence.build_evidence_envelope(
        _write(tmp_path / "alpha.json", alpha_payload),
        _write(tmp_path / "backtest.json", _backtest()),
        _write(tmp_path / "execution.json", execution_payload),
        _write(tmp_path / "release.json", _release_manifest()),
    )

    assert envelope["status"] == "rejected"
    assert "alpha: owner replay receipt must set replay_verified=true" in envelope["issues"]
    assert (
        "execution: scenarios must be the complete canonical matrix in order" in envelope["issues"]
    )


def test_evidence_rejects_serialized_framework_runtime_types(tmp_path: Path) -> None:
    alpha_payload = _alpha()
    alpha_payload["leaked_type"] = "qlib.data.dataset.DatasetH"

    envelope = framework_adapter_evidence.build_evidence_envelope(
        _write(tmp_path / "alpha.json", alpha_payload),
        _write(tmp_path / "backtest.json", _backtest()),
        _write(tmp_path / "execution.json", _execution()),
        _write(tmp_path / "release.json", _release_manifest()),
    )

    assert envelope["status"] == "rejected"
    assert envelope["issues"] == [
        "alpha: framework runtime type leaked at $.leaked_type: qlib.data.dataset.DatasetH"
    ]


def test_cli_writes_byte_stable_sorted_evidence(tmp_path: Path) -> None:
    alpha = _write(tmp_path / "alpha.json", _alpha())
    backtest = _write(tmp_path / "backtest.json", _backtest())
    execution = _write(tmp_path / "execution.json", _execution())
    release = _write(tmp_path / "release.json", _release_manifest())
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    first_status = framework_adapter_evidence.main(
        [
            "--alpha",
            str(alpha),
            "--backtest",
            str(backtest),
            "--execution",
            str(execution),
            "--release-manifest",
            str(release),
            "--output",
            str(first),
        ]
    )
    second_status = framework_adapter_evidence.main(
        [
            "--alpha",
            str(alpha),
            "--backtest",
            str(backtest),
            "--execution",
            str(execution),
            "--release-manifest",
            str(release),
            "--output",
            str(second),
        ]
    )

    assert first_status == second_status == 0
    assert first.read_bytes() == second.read_bytes()


def test_execution_evidence_rejects_minimal_or_noncanonical_owner_payload(
    tmp_path: Path,
) -> None:
    execution = _execution()
    execution["scenarios"][0]["expected_state"] = {"order_status": "known"}
    execution["scenarios"].append(execution["scenarios"][0])

    envelope = framework_adapter_evidence.build_evidence_envelope(
        _write(tmp_path / "alpha.json", _alpha()),
        _write(tmp_path / "backtest.json", _backtest()),
        _write(tmp_path / "execution.json", execution),
        _write(tmp_path / "release.json", _release_manifest()),
    )

    assert envelope["status"] == "rejected"
    assert any("expected_state: keys differ" in issue for issue in envelope["issues"])
    assert (
        "execution: scenarios must be the complete canonical matrix in order" in envelope["issues"]
    )


def test_backtest_evidence_is_bound_to_native_and_qlib_backends(tmp_path: Path) -> None:
    backtest = _backtest()
    backtest["candidate_backend"] = "other-engine"

    envelope = framework_adapter_evidence.build_evidence_envelope(
        _write(tmp_path / "alpha.json", _alpha()),
        _write(tmp_path / "backtest.json", backtest),
        _write(tmp_path / "execution.json", _execution()),
        _write(tmp_path / "release.json", _release_manifest()),
    )

    assert envelope["status"] == "rejected"
    assert "backtest: candidate_backend must be qlib-backtest" in envelope["issues"]
