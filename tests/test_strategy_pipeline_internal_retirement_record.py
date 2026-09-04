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
    assert "> status: ready-for-retirement" in record
    assert "维护周期计数为 2/2" in record
    assert "maintenance cycle 2 evidence" in record
