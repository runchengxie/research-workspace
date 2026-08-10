from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE_SCRIPT = ROOT / "scripts" / "strategy_evidence_gate.py"
POLICY_PATH = ROOT / "strategy-research" / "evidence_policy.json"
CATALOG_PATH = ROOT / "strategy-research" / "catalog.json"

spec = importlib.util.spec_from_file_location("strategy_evidence_gate", GATE_SCRIPT)
gate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)


def _evidence_bundle(strategy_id: str, checks: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "strategy_evidence_bundle.v1",
        "strategy_id": strategy_id,
        "as_of": "2026-08-11",
        "checks": checks,
    }


def _write_fixture(root: Path) -> None:
    policy = {
        "schema_version": "strategy_evidence_policy.v1",
        "checks": {
            "pit": {"name": "时间点数据", "meaning": "", "evidence_keys": ["pit_universe"]},
            "benchmark_matrix": {
                "name": "统一考试表",
                "meaning": "",
                "evidence_keys": ["cells", "axes"],
            },
            "cost": {"name": "交易成本", "meaning": "", "evidence_keys": ["cost_bps"]},
            "regime": {"name": "市场状态", "meaning": "", "evidence_keys": ["regimes"]},
        },
        "required_by_lifecycle": {
            "exploration": [],
            "pre_production": ["pit", "benchmark_matrix", "cost"],
            "operational": ["pit", "benchmark_matrix", "cost", "regime"],
        },
    }
    catalog = {
        "strategies": [
            {"id": "pre_strategy", "lifecycle": "pre_production"},
            {"id": "op_strategy", "lifecycle": "operational"},
            {"id": "exp_strategy", "lifecycle": "exploration"},
        ]
    }
    pass_pit = {"outcome": "pass", "evidence": "docs/evidence/pit.json", "pit_universe": True}
    compliant_cells = [
        {"universe": "csi300", "horizon": "h5", "regime": "bull", "cost_bps": 20, "sharpe": 0.7},
        {"universe": "csi500", "horizon": "h5", "regime": "bull", "cost_bps": 20, "sharpe": 1.1},
        {"universe": "csi500", "horizon": "h20", "regime": "bear", "cost_bps": 50, "sharpe": -0.2},
    ]
    single_cell = [compliant_cells[0]]
    bundles = {
        "pre_strategy": _evidence_bundle(
            "pre_strategy",
            {
                "pit": pass_pit,
                "benchmark_matrix": {
                    "outcome": "pass",
                    "evidence": "docs/evidence/bm.json",
                    "cells": compliant_cells,
                },
                "cost": {
                    "outcome": "pass",
                    "evidence": "docs/evidence/cost.json",
                    "cost_bps": [10, 30],
                },
            },
        ),
        "op_strategy": _evidence_bundle(
            "op_strategy",
            {
                "pit": pass_pit,
                "benchmark_matrix": {
                    "outcome": "pass",
                    "evidence": "docs/evidence/bm.json",
                    "cells": single_cell,
                },
                "cost": {
                    "outcome": "fail",
                    "evidence": "docs/evidence/cost.json",
                    "cost_bps": [10, 30],
                },
            },
        ),
    }
    (root / "strategy-research" / "evidence").mkdir(parents=True)
    (root / "strategy-research" / "evidence_policy.json").write_text(
        json.dumps(policy), encoding="utf-8"
    )
    (root / "strategy-research" / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    for strategy_id, bundle in bundles.items():
        (root / "strategy-research" / "evidence" / f"{strategy_id}.json").write_text(
            json.dumps(bundle), encoding="utf-8"
        )


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_real_policy_and_catalog_are_aligned() -> None:
    policy = _load_json(POLICY_PATH)
    catalog = _load_json(CATALOG_PATH)

    checks = policy["checks"]
    assert isinstance(checks, dict)
    required_by_lifecycle = policy["required_by_lifecycle"]
    assert isinstance(required_by_lifecycle, dict)

    lifecycles = {item["lifecycle"] for item in catalog["strategies"]}
    assert lifecycles <= set(required_by_lifecycle)
    for required in required_by_lifecycle.values():
        assert set(required) <= set(checks)

    ladder = ("pre_production", "shadow", "research_shadow", "operational_research", "operational")
    previous: set[str] = set()
    for lifecycle in ladder:
        current = set(required_by_lifecycle[lifecycle])
        assert previous <= current, lifecycle
        previous = current


def test_evidence_ladder_is_strictly_increasing_for_real_policy() -> None:
    policy = _load_json(POLICY_PATH)
    table = policy["required_by_lifecycle"]

    pre = set(table["pre_production"])
    shadow = set(table["shadow"])
    operational = set(table["operational"])
    assert shadow - pre == {"final_oos", "cpcv", "regime"}
    assert operational - shadow == {
        "pbo",
        "dsr",
        "capacity",
        "negative_controls",
        "execution_deviation",
    }
    assert set(table["shadow"]) == set(table["research_shadow"])
    assert set(table["shadow"]) == set(table["operational_research"])
    assert table["exploration"] == []


def test_entry_valid_requires_pass_outcome_and_evidence_path() -> None:
    requirement = {"evidence_keys": ["pit_universe"]}

    assert not gate._entry_valid(None, requirement)
    assert not gate._entry_valid({}, requirement)
    assert not gate._entry_valid({"outcome": "fail", "evidence": "x"}, requirement)
    assert not gate._entry_valid({"outcome": "pass", "evidence": ""}, requirement)
    assert not gate._entry_valid({"outcome": "pass", "evidence": "x"}, requirement)
    assert gate._entry_valid(
        {"outcome": "pass", "evidence": "x", "pit_universe": True}, requirement
    )


def test_benchmark_matrix_rejects_single_point_estimate() -> None:
    two_axes = [
        {"universe": "csi300", "horizon": "h5", "cost_bps": 20},
        {"universe": "csi500", "horizon": "h5", "cost_bps": 20},
        {"universe": "csi500", "horizon": "h20", "cost_bps": 50},
    ]
    one_axis = [
        {"universe": "csi300", "horizon": "h5", "cost_bps": 20},
        {"universe": "csi500", "horizon": "h5", "cost_bps": 20},
    ]

    assert gate._validate_benchmark_cells({"cells": two_axes}) == (True, "")
    assert gate._validate_benchmark_cells({"cells": one_axis})[0] is False
    assert gate._validate_benchmark_cells({"cells": [one_axis[0]]})[0] is False
    assert gate._validate_benchmark_cells({"cells": "nope"})[0] is False
    assert gate._validate_benchmark_cells({})[0] is False


def test_evaluate_marks_compliant_and_missing(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    policy = _load_json(tmp_path / "strategy-research" / "evidence_policy.json")
    catalog = _load_json(tmp_path / "strategy-research" / "catalog.json")

    bundle_dir = tmp_path / "strategy-research" / "evidence"
    results = [
        gate._evaluate(
            item,
            policy,
            gate._bundle_for(bundle_dir, str(item["id"])),
            require_lifecycle=None,
        )
        for item in catalog["strategies"]
    ]

    by_id = {result.strategy_id: result for result in results}
    assert by_id["pre_strategy"].verdict is True
    assert by_id["pre_strategy"].missing == []
    assert by_id["op_strategy"].verdict is False
    assert "regime" in by_id["op_strategy"].missing
    assert "benchmark_matrix" in by_id["op_strategy"].missing
    assert by_id["exp_strategy"].verdict is True


def test_run_gate_default_report_and_strict_failure(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    args = ["--root", str(tmp_path)]

    assert gate._run_gate([*args]) == 0
    assert gate._run_gate([*args, "--strict"]) == 1
    assert gate._run_gate([*args, "--json"]) == 0


def test_run_gate_promotion_check_is_fail_closed(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    base = ["--root", str(tmp_path)]

    assert gate._run_gate([*base, "--strategy", "pre_strategy", "--require", "pre_production"]) == 0
    assert gate._run_gate([*base, "--strategy", "pre_strategy", "--require", "operational"]) == 1
    with pytest.raises(SystemExit):
        gate._run_gate([*base, "--strategy", "pre_strategy"])
    with pytest.raises(SystemExit):
        gate._run_gate([*base, "--strategy", "missing_strategy", "--require", "operational"])


def test_run_gate_on_real_repository_reports_gaps(capsys: pytest.CaptureFixture[str]) -> None:
    assert gate._run_gate([]) == 0
    captured = capsys.readouterr().out

    assert "daily_watch20" in captured
    assert "结论" in captured
    assert gate._run_gate(["--json"]) == 0
