from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_SCRIPT = ROOT / "scripts" / "research_spec_check.py"

spec = importlib.util.spec_from_file_location("research_spec_check_trial_ledger", SPEC_SCRIPT)
checker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)


def _payload(experiment_id: str = "ledger_demo") -> dict[str, object]:
    return {
        "schema_version": "research_spec.v1",
        "experiment_id": experiment_id,
        "title": "Trial ledger demo",
        "market": "a_share",
        "status": "complete",
        "universe": {"description": "fixture", "pit": True},
        "data": {"source": "fixture"},
        "prediction": {"target": "return", "horizon": "h5", "task": "ranking"},
        "model": {"name": "fixture", "training": "fixed"},
        "portfolio": {"construction": "top_k"},
        "cost": {"cost_bps": [20]},
        "benchmark": {"cohorts": ["equal_weight"]},
        "evaluation": {"oos_protocol": ["walk_forward"], "final_oos_reserved": True},
        "evidence_refs": ["evidence.md"],
        "trial_ledger": {
            "path": f"trial-ledger/{experiment_id}.jsonl",
            "multiple_testing_family": "factor-search-v1",
        },
    }


def _write_spec(root: Path, payload: dict[str, object]) -> Path:
    experiment_id = str(payload["experiment_id"])
    path = root / "strategy-research" / "experiments" / experiment_id / "research_spec.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    (root / "evidence.md").write_text("evidence", encoding="utf-8")
    return path


def _write_ledger(
    root: Path,
    *,
    experiment_id: str = "ledger_demo",
    family: str = "factor-search-v1",
    counted: bool = True,
) -> Path:
    path = root / "strategy-research" / "trial-ledger" / f"{experiment_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "experiment_id": experiment_id,
        "multiple_testing": {"family_id": family, "counted": counted},
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    return path


def test_existing_spec_without_trial_ledger_remains_valid(tmp_path: Path) -> None:
    payload = _payload()
    payload.pop("trial_ledger")
    path = _write_spec(tmp_path, payload)
    result = checker.check_spec(path, expected_id="ledger_demo", root=tmp_path)
    assert result.ok, result.issues


def test_trial_ledger_link_passes_when_experiment_and_family_match(tmp_path: Path) -> None:
    payload = _payload()
    path = _write_spec(tmp_path, payload)
    _write_ledger(tmp_path)
    result = checker.check_spec(path, expected_id="ledger_demo", root=tmp_path)
    assert result.ok, result.issues


def test_trial_ledger_link_rejects_missing_file(tmp_path: Path) -> None:
    path = _write_spec(tmp_path, _payload())
    result = checker.check_spec(path, expected_id="ledger_demo", root=tmp_path)
    assert any("trial_ledger" in issue and "不存在" in issue for issue in result.issues)


def test_trial_ledger_link_rejects_foreign_experiment(tmp_path: Path) -> None:
    path = _write_spec(tmp_path, _payload())
    ledger = tmp_path / "strategy-research" / "trial-ledger" / "ledger_demo.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps(
            {
                "experiment_id": "other_experiment",
                "multiple_testing": {"family_id": "factor-search-v1", "counted": True},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = checker.check_spec(path, expected_id="ledger_demo", root=tmp_path)
    assert any("experiment_id" in issue and "trial_ledger" in issue for issue in result.issues)


def test_trial_ledger_link_requires_counted_member_of_declared_family(tmp_path: Path) -> None:
    path = _write_spec(tmp_path, _payload())
    _write_ledger(tmp_path, counted=False)
    result = checker.check_spec(path, expected_id="ledger_demo", root=tmp_path)
    assert any("multiple_testing_family" in issue for issue in result.issues)
