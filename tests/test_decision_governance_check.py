from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = ROOT / "scripts" / "decision_governance_check.py"

checker = importlib.util.spec_from_file_location("decision_governance_check", CHECK_SCRIPT)
module = importlib.util.module_from_spec(checker)
assert checker.loader is not None
sys.modules[checker.name] = module
checker.loader.exec_module(module)


def _valid_claim(claim_id: str = "demo.claim") -> dict[str, object]:
    return {
        "schema_version": "claim.v1",
        "claim_id": claim_id,
        "statement": "演示判断",
        "claim_type": "hypothesis",
        "supports": ["evidence://demo"],
        "contradicts": [],
        "critical_assumptions": [{"assumption_id": "as1", "statement": "假设一"}],
        "invalidation_conditions": [{"observable": "alpha", "threshold": "<0", "horizon": "12M"}],
        "abstain_conditions": [{"dimension": "cost", "reason": "成本证据缺失"}],
        "status": "active",
        "last_reviewed": "2026-08-18",
    }


def _write_claim(root: Path, claim_id: str, payload: dict[str, object]) -> Path:
    target = root / "strategy-research" / "judgment-ledger" / f"{claim_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return target


def _valid_case(case_id: str = "demo-case") -> dict[str, object]:
    return {
        "schema_version": "research_case.v1",
        "case_id": case_id,
        "question": "演示问题",
        "as_of": "2026-08-18",
        "research_specs": ["strategy-research/experiments/demo/research_spec.json"],
        "claims": ["demo.claim"],
        "evidence_bundles": ["strategy-research/evidence/demo.json"],
        "reviews": [
            {
                "review_id": "logic-1",
                "kind": "logic",
                "status": "completed",
                "file": "reviews/logic.json",
            },
            {
                "review_id": "evidence-1",
                "kind": "evidence",
                "status": "completed",
                "file": "reviews/evidence.json",
            },
        ],
        "known_gaps": ["capacity 证据缺失"],
        "abstentions": [],
        "decision": {"status": "provisional", "thesis": "演示结论"},
    }


def _write_case(root: Path, case_id: str, payload: dict[str, object]) -> tuple[Path, Path, Path]:
    case_dir = root / "strategy-research" / "cases" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (case_dir / "decision.md").write_text("# 决策\n", encoding="utf-8")
    reviews_dir = case_dir / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    (reviews_dir / "logic.json").write_text("{}", encoding="utf-8")
    (reviews_dir / "evidence.json").write_text("{}", encoding="utf-8")
    _write_claim(root, "demo.claim", _valid_claim())
    return case_dir / "case.json", reviews_dir / "logic.json", reviews_dir / "evidence.json"


def test_schema_files_exist() -> None:
    for relative in (
        "strategy-research/schemas/claim.v1.schema.json",
        "strategy-research/schemas/research_case.v1.schema.json",
    ):
        path = ROOT / relative
        assert path.is_file(), f"缺失 schema：{relative}"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)


def test_valid_claim_passes(tmp_path: Path) -> None:
    path = _write_claim(tmp_path, "demo.claim", _valid_claim())
    check = module.check_claim(path, root=tmp_path)
    assert check.ok, check.issues


def test_claim_missing_required_field_fails(tmp_path: Path) -> None:
    payload = _valid_claim()
    del payload["statement"]
    path = _write_claim(tmp_path, "demo.claim", payload)
    check = module.check_claim(path, root=tmp_path)
    assert not check.ok
    assert any("statement" in issue for issue in check.issues)


def test_claim_enum_and_id_constraints_fail(tmp_path: Path) -> None:
    payload = _valid_claim()
    payload["claim_type"] = "opinion"
    path = _write_claim(tmp_path, "demo.claim", payload)
    assert not module.check_claim(path, root=tmp_path).ok

    payload = _valid_claim()
    payload["status"] = "approved"
    path = _write_claim(tmp_path, "demo.claim", payload)
    assert not module.check_claim(path, root=tmp_path).ok

    payload = _valid_claim()
    payload["claim_id"] = "Upper.Case"
    path = _write_claim(tmp_path, "demo.claim", payload)
    assert not module.check_claim(path, root=tmp_path).ok


def test_claim_nested_object_fields_fail(tmp_path: Path) -> None:
    payload = _valid_claim()
    payload["invalidation_conditions"] = [{"observable": "alpha"}]
    path = _write_claim(tmp_path, "demo.claim", payload)
    assert not module.check_claim(path, root=tmp_path).ok

    payload = _valid_claim()
    payload["critical_assumptions"] = [{"assumption_id": "as1"}]
    path = _write_claim(tmp_path, "demo.claim", payload)
    assert not module.check_claim(path, root=tmp_path).ok


def test_valid_case_passes(tmp_path: Path) -> None:
    case_path, _, _ = _write_case(tmp_path, "demo-case", _valid_case())
    check = module.check_case(case_path, root=tmp_path)
    assert check.ok, check.issues


def test_case_decision_status_and_reviews_fail(tmp_path: Path) -> None:
    payload = _valid_case()
    payload["decision"] = {"status": "approved", "thesis": "x"}
    case_path, _, _ = _write_case(tmp_path, "demo-case", payload)
    assert not module.check_case(case_path, root=tmp_path).ok

    payload = _valid_case()
    payload["reviews"] = [
        {"review_id": "logic-1", "kind": "logic", "status": "done", "file": "reviews/logic.json"}
    ]
    case_path, _, _ = _write_case(tmp_path, "demo-case", payload)
    assert not module.check_case(case_path, root=tmp_path).ok


def test_case_missing_review_file_and_claim_fail(tmp_path: Path) -> None:
    payload = _valid_case()
    payload["reviews"] = [
        {
            "review_id": "logic-1",
            "kind": "logic",
            "status": "completed",
            "file": "reviews/missing.json",
        }
    ]
    case_path, _, _ = _write_case(tmp_path, "demo-case", payload)
    assert not module.check_case(case_path, root=tmp_path).ok
    assert any("缺失" in issue for issue in module.check_case(case_path, root=tmp_path).issues)


def test_case_dir_must_match_case_id(tmp_path: Path) -> None:
    payload = _valid_case(case_id="other-case")
    case_path, _, _ = _write_case(tmp_path, "demo-case", payload)
    assert not module.check_case(case_path, root=tmp_path).ok
    assert any(
        "目录必须与 case_id" in issue
        for issue in module.check_case(case_path, root=tmp_path).issues
    )


def test_cli_scan_exit_code(tmp_path: Path) -> None:
    _write_claim(tmp_path, "demo.claim", _valid_claim())
    _write_case(tmp_path, "demo-case", _valid_case())
    assert module.main(["--root", str(tmp_path)]) == 0

    _write_claim(tmp_path, "broken.claim", _valid_claim(claim_id="broken.claim"))
    broken_payload = _valid_claim(claim_id="broken.claim")
    broken_payload["status"] = "nope"
    _write_claim(tmp_path, "broken.claim", broken_payload)
    assert module.main(["--root", str(tmp_path)]) == 1


def test_cli_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_claim(tmp_path, "demo.claim", _valid_claim())
    assert module.main(["--root", str(tmp_path), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["schema_version"] == "decision_governance_check.v1"
    assert output["manifests"][0]["ok"] is True


def test_dg4_no_view_requires_abstentions(tmp_path: Path) -> None:
    payload = _valid_case()
    payload["decision"] = {"status": "no_view", "thesis": "证据不足放弃判断"}
    payload["abstentions"] = []
    case_path, _, _ = _write_case(tmp_path, "demo-case", payload)
    check = module.check_case(case_path, root=tmp_path)
    assert not check.ok
    assert any("no_view" in issue for issue in check.issues)


def test_dg4_known_gaps_blocks_accepted(tmp_path: Path) -> None:
    payload = _valid_case()
    payload["known_gaps"] = ["capacity 证据缺失"]
    payload["decision"] = {"status": "accepted", "thesis": "错误地在缺口下接受"}
    case_path, _, _ = _write_case(tmp_path, "demo-case", payload)
    check = module.check_case(case_path, root=tmp_path)
    assert not check.ok
    assert any("known_gaps" in issue for issue in check.issues)


def test_dg5_requires_both_review_kinds(tmp_path: Path) -> None:
    payload = _valid_case()
    payload["reviews"] = [
        {
            "review_id": "logic-1",
            "kind": "logic",
            "status": "completed",
            "file": "reviews/logic.json",
        }
    ]
    case_path, _, _ = _write_case(tmp_path, "demo-case", payload)
    check = module.check_case(case_path, root=tmp_path)
    assert not check.ok
    assert any("DG5" in issue for issue in check.issues)


def test_dg6_evidence_readiness_dimensions_valid(tmp_path: Path) -> None:
    payload = _valid_case()
    payload["decision"] = {
        "status": "provisional",
        "thesis": "演示结论",
        "evidence_readiness": [
            {"dimension": "证据覆盖", "status": "partial", "note": "长窗口未跑"},
            {"dimension": "来源可靠性", "status": "ok"},
        ],
        "investment_conviction": "中等，主观判断",
    }
    case_path, _, _ = _write_case(tmp_path, "demo-case", payload)
    check = module.check_case(case_path, root=tmp_path)
    assert check.ok, check.issues
