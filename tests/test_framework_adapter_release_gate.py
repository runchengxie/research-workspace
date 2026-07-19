from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "framework_adapter_release_gate.py"

spec = importlib.util.spec_from_file_location("framework_adapter_release_gate", SCRIPT)
framework_adapter_release_gate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = framework_adapter_release_gate
spec.loader.exec_module(framework_adapter_release_gate)


def _manifest(merge_state: str = "draft") -> dict[str, object]:
    return {
        "schema_version": "framework_adapter_release.v1",
        "release_id": "framework-adapters-2026-07",
        "status": (
            "ready_to_validate" if merge_state == "merged" else "blocked_on_downstream_merge"
        ),
        "evidence_status": "pending",
        "pin_policy": "after_downstream_merge_only",
        "integration_evidence": {"path": "evidence.json", "sha256": None},
        "components": [
            {
                "repository": repository,
                "branch": f"feature/{repository}",
                "pr_url": f"https://github.com/example/{repository}/pull/1",
                "baseline_commit": "0" * 40,
                "candidate_commit": identifier * 40,
                "merge_state": merge_state,
                "merged_commit": identifier * 40 if merge_state == "merged" else None,
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


def test_draft_release_is_explicitly_blocked_without_premature_pins(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        framework_adapter_release_gate,
        "_gitlink_commit",
        lambda _root, _path: "0" * 40,
    )

    report = framework_adapter_release_gate.build_report(tmp_path, _manifest())

    assert report["status"] == "blocked"
    assert report["blocked_reason"] == "downstream PRs are not merged"
    assert report["issues"] == []
    assert report["all_downstream_merged"] is False


def test_gate_rejects_candidate_pin_before_downstream_merge(monkeypatch, tmp_path: Path) -> None:
    manifest = _manifest()
    candidate_by_repo = {
        item["repository"]: item["candidate_commit"] for item in manifest["components"]
    }
    monkeypatch.setattr(
        framework_adapter_release_gate,
        "_gitlink_commit",
        lambda _root, path: candidate_by_repo[path],
    )

    report = framework_adapter_release_gate.build_report(tmp_path, manifest)

    assert report["status"] == "failed"
    assert len(report["issues"]) == 5
    assert all("gitlink changed before downstream merge" in issue for issue in report["issues"])


def test_merged_release_requires_and_accepts_exact_merged_gitlinks(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manifest = _manifest("merged")
    merged_by_repo = {item["repository"]: item["merged_commit"] for item in manifest["components"]}
    monkeypatch.setattr(
        framework_adapter_release_gate,
        "_gitlink_commit",
        lambda _root, path: merged_by_repo[path],
    )

    report = framework_adapter_release_gate.build_report(tmp_path, manifest)

    assert report["status"] == "passed"
    assert report["issues"] == []
    assert report["all_downstream_merged"] is True
    assert report["all_merged_commits_pinned"] is True


def test_checked_in_release_manifest_is_valid_and_superseded(monkeypatch) -> None:
    manifest = framework_adapter_release_gate.load_manifest(
        ROOT / "docs" / "framework-adapter-release.yml"
    )
    baseline_by_repo = {
        item["repository"]: item["baseline_commit"] for item in manifest["components"]
    }
    monkeypatch.setattr(
        framework_adapter_release_gate,
        "_gitlink_commit",
        lambda _root, path: baseline_by_repo[path],
    )

    report = framework_adapter_release_gate.build_report(ROOT, manifest)

    assert report["status"] == "passed"
    assert report["issues"] == []
    assert report["release_state"] == "superseded"
    assert report["superseded_reason"]
    assert report["all_downstream_merged"] is False
    assert report["evidence_status"] == "pending"
    assert {component["repository"] for component in report["components"]} == (
        framework_adapter_release_gate.EXPECTED_COMPONENTS
    )


def _write_verified_evidence(tmp_path: Path, manifest: dict[str, object]) -> str:
    merged = {item["repository"]: item["merged_commit"] for item in manifest["components"]}
    payload = {
        "schema": "framework_adapter_integration_evidence.v1",
        "status": "accepted",
        "issues": [],
        "release": {
            "release_id": manifest["release_id"],
            "components": merged,
        },
        "evidence": {
            "alpha": {
                "name": "alpha.json",
                "sha256": "a" * 64,
                "schema": "backend_comparison_replay_receipt.v1",
            },
            "backtest": {
                "name": "backtest.json",
                "sha256": "b" * 64,
                "schema": "backtest_differential.v1",
            },
            "execution": {
                "name": "execution.json",
                "sha256": "c" * 64,
                "schema": "execution_recovery_matrix.v1",
            },
        },
    }
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return hashlib.sha256(evidence.read_bytes()).hexdigest()


def _create_verified_surfaces(tmp_path: Path) -> None:
    for relative in framework_adapter_release_gate.REQUIRED_VERIFIED_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# contract surface\n", encoding="utf-8")


def test_verified_release_binds_evidence_to_release_and_merged_commits(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manifest = _manifest("merged")
    manifest["status"] = "verified"
    manifest["evidence_status"] = "accepted"
    manifest["integration_evidence"]["sha256"] = _write_verified_evidence(tmp_path, manifest)
    _create_verified_surfaces(tmp_path)
    merged_by_repo = {item["repository"]: item["merged_commit"] for item in manifest["components"]}
    monkeypatch.setattr(
        framework_adapter_release_gate,
        "_gitlink_commit",
        lambda _root, path: merged_by_repo[path],
    )

    report = framework_adapter_release_gate.build_report(tmp_path, manifest)

    assert report["status"] == "passed"
    assert report["issues"] == []


def test_verified_release_rejects_stale_component_evidence(monkeypatch, tmp_path: Path) -> None:
    manifest = _manifest("merged")
    manifest["status"] = "verified"
    manifest["evidence_status"] = "accepted"
    manifest["integration_evidence"]["sha256"] = _write_verified_evidence(tmp_path, manifest)
    manifest["components"][0]["merged_commit"] = "f" * 40
    _create_verified_surfaces(tmp_path)
    merged_by_repo = {item["repository"]: item["merged_commit"] for item in manifest["components"]}
    monkeypatch.setattr(
        framework_adapter_release_gate,
        "_gitlink_commit",
        lambda _root, path: merged_by_repo[path],
    )

    report = framework_adapter_release_gate.build_report(tmp_path, manifest)

    assert report["status"] == "failed"
    assert "integration evidence component commits do not match merged commits" in report["issues"]
