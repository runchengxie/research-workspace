from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = ROOT / "scripts" / "decision_governance_check.py"

checker = importlib.util.spec_from_file_location("decision_governance_check_counterexamples", CHECK_SCRIPT)
module = importlib.util.module_from_spec(checker)
assert checker.loader is not None
sys.modules[checker.name] = module
checker.loader.exec_module(module)


def _write_claim(root: Path, claim_id: str = "demo.claim") -> None:
    path = root / "strategy-research" / "judgment-ledger" / f"{claim_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "claim.v1",
                "claim_id": claim_id,
                "statement": "demo",
                "claim_type": "hypothesis",
                "status": "active",
                "last_reviewed": "2026-08-26",
            }
        ),
        encoding="utf-8",
    )


def _valid_counterexample(counterexample_id: str = "demo.claim.cost-stress") -> dict[str, object]:
    return {
        "schema_version": "counterexample.v1",
        "counterexample_id": counterexample_id,
        "claim_id": "demo.claim",
        "scenario_type": "cost",
        "summary": "cost stress erases the edge",
        "as_of": "2026-08-26",
        "status": "open",
        "severity": "material",
        "stress_dimensions": [
            {"name": "round_trip_cost_bps", "baseline": "10", "stressed": "40"}
        ],
        "baseline_metrics": [{"name": "net_sharpe", "value": 0.8}],
        "stressed_metrics": [{"name": "net_sharpe", "value": 0.1}],
        "failure_conditions": ["net_sharpe < 0.2"],
        "evidence_refs": ["evidence://demo-cost-stress"],
    }


def _write_counterexample(root: Path, payload: dict[str, object]) -> Path:
    counterexample_id = str(payload["counterexample_id"])
    path = root / "strategy-research" / "counterexamples" / f"{counterexample_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_counterexample_schema_exists() -> None:
    path = ROOT / "strategy-research" / "schemas" / "counterexample.v1.schema.json"
    assert path.is_file()
    assert json.loads(path.read_text(encoding="utf-8"))["$id"] == "counterexample.v1"


def test_valid_counterexample_passes(tmp_path: Path) -> None:
    _write_claim(tmp_path)
    path = _write_counterexample(tmp_path, _valid_counterexample())

    check = module.check_counterexample(path, root=tmp_path)

    assert check.ok, check.issues


def test_counterexample_requires_existing_claim(tmp_path: Path) -> None:
    path = _write_counterexample(tmp_path, _valid_counterexample())

    check = module.check_counterexample(path, root=tmp_path)

    assert not check.ok
    assert any("claim_id" in issue and "缺失" in issue for issue in check.issues)


def test_counterexample_rejects_duplicate_metric_names(tmp_path: Path) -> None:
    _write_claim(tmp_path)
    payload = _valid_counterexample()
    payload["stressed_metrics"] = [
        {"name": "net_sharpe", "value": 0.1},
        {"name": "net_sharpe", "value": 0.2},
    ]
    path = _write_counterexample(tmp_path, payload)

    check = module.check_counterexample(path, root=tmp_path)

    assert not check.ok
    assert any("重复" in issue for issue in check.issues)


def test_counterexample_rejects_unknown_type_and_non_finite_metric(tmp_path: Path) -> None:
    _write_claim(tmp_path)
    payload = _valid_counterexample()
    payload["scenario_type"] = "magic"
    payload["stressed_metrics"] = [{"name": "net_sharpe", "value": float("nan")}]
    path = _write_counterexample(tmp_path, payload)

    check = module.check_counterexample(path, root=tmp_path)

    assert not check.ok
    assert any("scenario_type" in issue for issue in check.issues)
    assert any("有限数值" in issue for issue in check.issues)


def test_case_counterexample_reference_must_exist(tmp_path: Path) -> None:
    _write_claim(tmp_path)
    case_dir = tmp_path / "strategy-research" / "cases" / "demo-case"
    case_dir.mkdir(parents=True)
    case_path = case_dir / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "schema_version": "research_case.v1",
                "case_id": "demo-case",
                "question": "demo",
                "as_of": "2026-08-26",
                "claims": ["demo.claim"],
                "counterexamples": ["demo.claim.missing"],
                "decision": {"status": "provisional", "thesis": "demo"},
            }
        ),
        encoding="utf-8",
    )

    check = module.check_case(case_path, root=tmp_path)

    assert not check.ok
    assert any("counterexamples 引用缺失" in issue for issue in check.issues)


def test_cli_scan_includes_counterexamples(tmp_path: Path, capsys: object) -> None:
    _write_claim(tmp_path)
    _write_counterexample(tmp_path, _valid_counterexample())

    assert module.main(["--root", str(tmp_path)]) == 0
