from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import export_hk_legacy_archive  # noqa: E402
import hk_archive_gate  # noqa: E402


def test_private_archive_manifest_is_pinned_and_retains_execution_runtime() -> None:
    manifest = hk_archive_gate.load_manifest()

    validation = hk_archive_gate.validate_manifest(manifest)

    assert validation["status"] == "passed"
    assert all(len(revision) == 40 for revision in manifest["source_revisions"].values())
    retained = {
        record["id"]: record
        for record in manifest["records"]
        if record["archive_action"] == "retain_active"
    }
    assert "quant-execution-engine-shared-market-runtime" in retained
    assert any(
        "longport" in path
        for path in retained["quant-execution-engine-shared-market-runtime"]["paths"]
    )
    assert "market-data-platform-hk-restore-control-plane" in retained


def test_private_archive_gate_reports_pending_audits_without_failing_manifest() -> None:
    report = hk_archive_gate.build_report(hk_archive_gate.load_manifest())

    assert report["status"] == "passed"
    assert report["removal_review_status"] == "blocked_pending_audit"
    blocked = {
        row["id"]: row["blockers"]
        for row in report["records"]
        if row["archive_action"] == "include"
    }
    assert "consumer_audit" in blocked["market-data-platform-hk-provider-legacy"]
    assert "private_archive_reference" not in blocked["market-data-platform-hk-provider-legacy"]
    assert "zero_usage_release_window" in blocked["cross-sectional-trees-hk-research-legacy"]
    retained = [row for row in report["records"] if row["archive_action"] == "retain_active"]
    assert all(not row["eligible_for_removal_review"] for row in retained)


def test_private_archive_gate_can_report_eligible_follow_up_review() -> None:
    manifest = copy.deepcopy(hk_archive_gate.load_manifest())
    for record in manifest["records"]:
        gate = record["deletion_gate"]
        if gate["status"] == "not_applicable":
            continue
        gate.update(
            {
                "status": "ready",
                "source_tag": "hk_legacy_archive_source_v1",
                "restore_evidence": "recorded",
                "consumer_audit": "completed",
                "replacement_docs": "recorded",
                "rollback_notes": "recorded",
                "focused_tests": "passed",
                "private_archive_reference": "private://immutable/archive-reference",
                "private_archive_export_evidence": "recorded",
                "zero_usage_release_window": "completed",
            }
        )

    report = hk_archive_gate.build_report(manifest)

    assert report["status"] == "passed"
    assert report["removal_review_status"] == "eligible_for_removal_review"


def test_private_archive_export_stages_checksums_and_excludes_retained_runtime(
    tmp_path: Path,
) -> None:
    stage = tmp_path / "hk-quant-legacy-archive"

    manifest = export_hk_legacy_archive.export_archive(
        manifest_path=hk_archive_gate.DEFAULT_MANIFEST,
        out_dir=stage,
    )

    assert manifest["scan"]["status"] == "passed"
    assert manifest["archive_sha256"]
    assert manifest["included_files"]
    assert not (stage / ".git").exists()
    assert not (stage / "quant-execution-engine").exists()
    written = json.loads((stage / "archive-export-manifest.json").read_text(encoding="utf-8"))
    report = hk_archive_gate.build_report(hk_archive_gate.load_manifest(), export_manifest=written)
    assert report["export_validation"]["status"] == "passed"


def test_private_archive_scan_rejects_runtime_files(tmp_path: Path) -> None:
    stage = tmp_path / "unsafe"
    stage.mkdir()
    (stage / ".env.local").write_text("ACCESS_TOKEN='private-value'\n", encoding="utf-8")
    (stage / "prices.parquet").write_text("not source\n", encoding="utf-8")

    scan = export_hk_legacy_archive.scan_archive_tree(stage)

    assert scan["status"] == "failed"
    issues = {(row["path"], row["check"]) for row in scan["issues"]}
    assert (".env.local", "forbidden_path") in issues
    assert (".env.local", "credential_literal") in issues
    assert ("prices.parquet", "runtime_or_archive_suffix") in issues
