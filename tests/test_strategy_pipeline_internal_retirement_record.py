from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT / "docs" / "evidence" / "strategy-pipeline-internal-retirement-cycle-1-20260905.json"
)
RECORD = ROOT / "docs" / "migrations" / "strategy-pipeline-internal-retirement-record.md"


def test_first_retirement_maintenance_cycle_has_recovery_and_consumer_evidence() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["maintenance_cycle"] == 1
    assert evidence["maintenance_cycles_required"] == 2
    assert evidence["freeze_tag_commit"] == evidence["internal_commit"]
    assert evidence["recovery_drill"] == {
        "archive_extracted": True,
        "readme_present": True,
        "internal_source_tree_present": True,
    }
    assert evidence["active_consumer_audit"]["workspace_internal_import_files"] == 0
    assert evidence["active_consumer_audit"]["public_pipeline_internal_import_files"] == 0
    assert evidence["active_consumer_audit"]["strategy_research_active_external_consumers"] == 0
    assert evidence["public_clean_room"]["pytest"] == "55 passed"

    record = RECORD.read_text(encoding="utf-8")
    assert "maintenance cycle 1 evidence" in record
    assert "维护周期计数为 2/2" in record


def test_second_retirement_maintenance_cycle_is_ready_for_formal_review() -> None:
    evidence_path = (
        ROOT / "docs" / "evidence" / "strategy-pipeline-internal-retirement-cycle-2-20260905.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["maintenance_cycle"] == 2
    assert evidence["maintenance_cycles_required"] == 2
    assert evidence["conclusion"].startswith("second consecutive audit")
    assert evidence["next_action"].startswith("merge the final internal retirement PR")
    assert evidence["recovery_drill"]["archive_extracted"] is True
    assert evidence["public_clean_room"]["pytest"] == "55 passed"

    record = RECORD.read_text(encoding="utf-8")
    assert "> status: retired" in record
    assert "维护周期计数为 2/2" in record
    assert "maintenance cycle 2 evidence" in record


def test_final_retirement_evidence_records_private_archive_and_recovery() -> None:
    evidence_path = (
        ROOT / "docs" / "evidence" / "strategy-pipeline-internal-retirement-final-20260905.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["internal_visibility"] == "private"
    assert evidence["internal_archived"] is True
    assert evidence["maintenance_cycles"] == "2/2"
    assert evidence["active_external_consumers"] == 0
    assert evidence["last_recoverable_commit"] == "44fd1bae16f04f18c7fa5234c9f5f0860ae69ac3"
    assert evidence["freeze_tag"] == "retirement-freeze-20260905-r1"
    assert evidence["production_workspace_release"] == ("d31f007223d009a16f76368161536e4be5a51d89")
    assert (
        evidence["observed_local_production_workspace_release"]
        == evidence["production_workspace_release"]
    )
    assert evidence["production_release_matches_observed_local_state"] is True

    record = RECORD.read_text(encoding="utf-8")
    assert "> status: retired" in record
    assert "GitHub 仓库已确认保持私有并进入 archived 状态" in record
    assert "internal retirement final evidence" in record
    assert "production promotion resolution" in record
    assert "此前 closeout consistency audit 中记录的生产指针不一致已解决" in record
