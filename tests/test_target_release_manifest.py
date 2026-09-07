import json
from pathlib import Path


def test_target_release_manifest_is_candidate_and_rollback_complete() -> None:
    payload = json.loads(
        (Path(__file__).parents[1] / "migration/target-release-manifest-20260907.json").read_text()
    )
    assert payload["schema_version"] == "quant.workspace.target_release.v1"
    assert payload["status"] == "candidate_not_promoted"
    assert payload["rollback_window_days"] == 14
    assert payload["rollback"]["legacy_workspace_commit"]
    assert payload["rollback"]["legacy_submodule_commits"]
    assert payload["targets"]["quant-platform"]["commit"]
    assert payload["targets"]["quant-research"]["commit"]
    assert payload["targets"]["quant-market-data-platform"]["commit"]
    assert payload["targets"]["quant-intel-platform"]["commit"]
    assert payload["production"]["current_switch"] is False
