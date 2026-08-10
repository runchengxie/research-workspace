from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC_SCRIPT = ROOT / "scripts" / "research_spec_check.py"

spec = importlib.util.spec_from_file_location("research_spec_check", SPEC_SCRIPT)
checker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)


def _valid_spec(experiment_id: str = "demo_experiment") -> dict[str, object]:
    return {
        "schema_version": "research_spec.v1",
        "experiment_id": experiment_id,
        "title": "演示实验",
        "market": "a_share",
        "status": "complete",
        "universe": {"description": "全市场 daily_clean"},
        "data": {"source": "platform_assets"},
        "prediction": {"target": "next_open_return", "horizon": "h5", "task": "ranking"},
        "model": {"name": "XGBoost", "training": "rolling_windows"},
        "portfolio": {"construction": "top_k"},
        "cost": {"cost_bps": [10, 20]},
        "benchmark": {"cohorts": ["a_share_all_equalw"]},
        "evaluation": {"oos_protocol": ["walk_forward"], "final_oos_reserved": False},
        "evidence_refs": ["evidence.md"],
    }


def _write_spec(root: Path, experiment_id: str, payload: dict[str, object]) -> Path:
    target = root / "strategy-research" / "experiments" / experiment_id / "research_spec.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")
    (root / "evidence.md").write_text("evidence", encoding="utf-8")
    return target


def test_real_qlib_pilot_spec_is_valid() -> None:
    path = ROOT / "strategy-research" / "experiments" / "qlib_pilot" / "research_spec.json"
    assert path.is_file()
    result = checker.check_spec(path, expected_id="qlib_pilot", root=ROOT)
    assert result.ok, result.issues


def test_valid_spec_passes(tmp_path: Path) -> None:
    path = _write_spec(tmp_path, "demo_experiment", _valid_spec())
    result = checker.check_spec(path, expected_id="demo_experiment", root=tmp_path)
    assert result.ok, result.issues


def test_missing_required_field_fails(tmp_path: Path) -> None:
    payload = _valid_spec()
    del payload["cost"]
    path = _write_spec(tmp_path, "demo_experiment", payload)
    result = checker.check_spec(path, expected_id="demo_experiment", root=tmp_path)
    assert not result.ok
    assert any("cost" in issue for issue in result.issues)


def test_schema_version_and_id_mismatch_fail(tmp_path: Path) -> None:
    payload = _valid_spec()
    payload["schema_version"] = "research_spec.v2"
    path = _write_spec(tmp_path, "demo_experiment", payload)
    result = checker.check_spec(path, expected_id="demo_experiment", root=tmp_path)
    assert any("schema_version" in issue for issue in result.issues)

    renamed = _write_spec(tmp_path, "demo_experiment", _valid_spec(experiment_id="other_id"))
    result = checker.check_spec(renamed, expected_id="demo_experiment", root=tmp_path)
    assert any("experiment_id" in issue for issue in result.issues)


def test_status_enum_and_enum_fields_fail(tmp_path: Path) -> None:
    payload = _valid_spec()
    payload["status"] = "done"
    path = _write_spec(tmp_path, "demo_experiment", payload)
    assert not checker.check_spec(path, expected_id="demo_experiment", root=tmp_path).ok

    payload = _valid_spec()
    payload["portfolio"] = {"construction": "buy_all"}
    path = _write_spec(tmp_path, "demo_experiment", payload)
    assert not checker.check_spec(path, expected_id="demo_experiment", root=tmp_path).ok

    payload = _valid_spec()
    payload["prediction"] = {"target": "x", "horizon": "h5", "task": "paint"}
    path = _write_spec(tmp_path, "demo_experiment", payload)
    assert not checker.check_spec(path, expected_id="demo_experiment", root=tmp_path).ok


def test_cost_and_benchmark_accept_na(tmp_path: Path) -> None:
    payload = _valid_spec()
    payload["cost"] = {"cost_bps": "n/a"}
    payload["benchmark"] = {"cohorts": "n/a"}
    payload["evaluation"] = {"oos_protocol": "n/a", "final_oos_reserved": False}
    path = _write_spec(tmp_path, "demo_experiment", payload)
    assert checker.check_spec(path, expected_id="demo_experiment", root=tmp_path).ok


def test_completed_spec_requires_existing_evidence(tmp_path: Path) -> None:
    payload = _valid_spec()
    payload["evidence_refs"] = ["does/not/exist.md"]
    path = _write_spec(tmp_path, "demo_experiment", payload)
    result = checker.check_spec(path, expected_id="demo_experiment", root=tmp_path)
    assert not result.ok
    assert any("不存在" in issue for issue in result.issues)

    payload = _valid_spec()
    payload["evidence_refs"] = []
    path = _write_spec(tmp_path, "demo_experiment", payload)
    result = checker.check_spec(path, expected_id="demo_experiment", root=tmp_path)
    assert not result.ok
    assert any("evidence_refs 不能为空" in issue for issue in result.issues)


def test_cli_scan_reports_exit_code(tmp_path: Path) -> None:
    _write_spec(tmp_path, "demo_experiment", _valid_spec())
    assert checker.main(["--root", str(tmp_path)]) == 0

    broken = _valid_spec()
    broken["market"] = ""
    _write_spec(tmp_path, "broken_experiment", broken)
    assert checker.main(["--root", str(tmp_path)]) == 1

    specific = (
        tmp_path / "strategy-research" / "experiments" / "demo_experiment" / "research_spec.json"
    )
    assert checker.main(["--root", str(tmp_path), "--spec", str(specific)]) == 0


def test_cli_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_spec(tmp_path, "demo_experiment", _valid_spec())
    assert checker.main(["--root", str(tmp_path), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["schema_version"] == "research_spec_check.v1"
    assert output["specs"][0]["experiment_id"] == "demo_experiment"
    assert output["specs"][0]["ok"] is True
