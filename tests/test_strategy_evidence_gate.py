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


def test_real_catalog_keeps_e2_candidates_outside_strategy_identity() -> None:
    catalog = _load_json(CATALOG_PATH)
    ids = {item["id"] for item in catalog["strategies"]}
    required = {
        "daily_watch20",
        "hotsector",
        "style_replica_a80_b20",
        "d11_h5_shadow",
        "dividend_growth_momentum",
    }

    assert required <= ids
    assert "a_share_e2_promotion_candidate_20260825" not in ids
    assert all(
        item["production_eligible"] is False
        for item in catalog["strategies"]
        if item["id"] in required
    )


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


def test_known_gap_waiver_blocks_on_unregistered_gap(tmp_path: Path) -> None:
    """A non-production strategy must register every missing check.

    Registered known gaps do not block ``--strict``; an unregistered missing
    check does. This guards against gaps being silently dropped from the bundle.
    """
    policy = {
        "schema_version": "strategy_evidence_policy.v1",
        "checks": {
            "pit": {"name": "时间点数据", "evidence_keys": ["pit_universe"]},
            "cost": {"name": "交易成本", "evidence_keys": ["cost_bps"]},
        },
        "required_by_lifecycle": {"pre_production": ["pit", "cost"]},
    }
    catalog = {
        "strategies": [
            {"id": "s", "lifecycle": "pre_production", "production_eligible": False},
        ]
    }
    root = tmp_path
    (root / "strategy-research").mkdir(parents=True)
    (root / "strategy-research" / "evidence_policy.json").write_text(
        json.dumps(policy), encoding="utf-8"
    )
    (root / "strategy-research" / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    bundle_dir = root / "strategy-research" / "evidence"
    bundle_dir.mkdir(parents=True)

    # Both required checks missing, pit registered as a known gap, cost not.
    unregistered = {
        "schema_version": "strategy_evidence_bundle.v1",
        "strategy_id": "s",
        "checks": {
            "pit": {"outcome": "missing", "evidence": None},
            "cost": {"outcome": "missing", "evidence": None},
        },
        "known_gaps": ["pit: 未提供时间点数据证据"],
    }
    (bundle_dir / "s.json").write_text(json.dumps(unregistered), encoding="utf-8")
    assert gate._run_gate(["--root", str(root), "--strict"]) == 1

    # Now cost is also registered: fully waived, strict gate passes.
    fully_waived = dict(unregistered)
    fully_waived["known_gaps"] = [
        "pit: 未提供时间点数据证据",
        "cost: 未提供交易成本证据",
    ]
    (bundle_dir / "s.json").write_text(json.dumps(fully_waived), encoding="utf-8")
    assert gate._run_gate(["--root", str(root), "--strict"]) == 0


def test_production_strategy_cannot_waive_gaps(tmp_path: Path) -> None:
    """A production-eligible strategy must close every required check."""
    policy = {
        "schema_version": "strategy_evidence_policy.v1",
        "checks": {"pit": {"name": "时间点数据", "evidence_keys": ["pit_universe"]}},
        "required_by_lifecycle": {"operational": ["pit"]},
    }
    catalog = {
        "strategies": [
            {"id": "s", "lifecycle": "operational", "production_eligible": True},
        ]
    }
    root = tmp_path
    (root / "strategy-research").mkdir(parents=True)
    (root / "strategy-research" / "evidence_policy.json").write_text(
        json.dumps(policy), encoding="utf-8"
    )
    (root / "strategy-research" / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    bundle_dir = root / "strategy-research" / "evidence"
    bundle_dir.mkdir(parents=True)
    bundle = {
        "schema_version": "strategy_evidence_bundle.v1",
        "strategy_id": "s",
        "checks": {"pit": {"outcome": "missing", "evidence": None}},
        "known_gaps": ["pit: 未提供时间点数据证据"],
    }
    (bundle_dir / "s.json").write_text(json.dumps(bundle), encoding="utf-8")
    result = gate._evaluate(catalog["strategies"][0], policy, bundle, require_lifecycle=None)
    assert result.production_eligible is True
    assert result.verdict is False
    assert gate._run_gate(["--root", str(root), "--strict"]) == 1


def test_zero_gaps_requires_explicit_flag(tmp_path: Path) -> None:
    """--zero-gaps 不能单独使用，必须与 --strict 同用。"""
    policy = {
        "schema_version": "strategy_evidence_policy.v1",
        "checks": {"pit": {"name": "时间点数据", "evidence_keys": ["pit_universe"]}},
        "required_by_lifecycle": {"pre_production": ["pit"]},
    }
    catalog = {"strategies": [{"id": "s", "lifecycle": "pre_production"}]}
    root = tmp_path
    (root / "strategy-research").mkdir(parents=True)
    (root / "strategy-research" / "evidence_policy.json").write_text(
        json.dumps(policy), encoding="utf-8"
    )
    (root / "strategy-research" / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    with pytest.raises(SystemExit):
        gate._run_gate(["--root", str(root), "--zero-gaps"])


def test_zero_gaps_blocks_research_strategy_with_known_gaps(tmp_path: Path) -> None:
    """晋级评审档下，带已知缺口的研究型策略必须失败。"""
    policy = {
        "schema_version": "strategy_evidence_policy.v1",
        "checks": {"pit": {"name": "时间点数据", "evidence_keys": ["pit_universe"]}},
        "required_by_lifecycle": {"pre_production": ["pit"]},
    }
    catalog = {
        "strategies": [{"id": "s", "lifecycle": "pre_production", "production_eligible": False}]
    }
    root = tmp_path
    (root / "strategy-research").mkdir(parents=True)
    (root / "strategy-research" / "evidence_policy.json").write_text(
        json.dumps(policy), encoding="utf-8"
    )
    (root / "strategy-research" / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    bundle_dir = root / "strategy-research" / "evidence"
    bundle_dir.mkdir(parents=True)
    bundle = {
        "schema_version": "strategy_evidence_bundle.v1",
        "strategy_id": "s",
        "checks": {"pit": {"outcome": "missing", "evidence": None}},
        "known_gaps": ["pit: 未提供时间点数据证据"],
    }
    (bundle_dir / "s.json").write_text(json.dumps(bundle), encoding="utf-8")
    # 护栏档放行（已知缺口已登记）
    assert gate._run_gate(["--root", str(root), "--strict"]) == 0
    # 晋级档拦截（仍带已知缺口）
    assert gate._run_gate(["--root", str(root), "--strict", "--zero-gaps"]) == 1


def test_zero_gaps_passes_research_strategy_without_gaps(tmp_path: Path) -> None:
    """晋级评审档下，零已知缺口的研究型策略通过。"""
    policy = {
        "schema_version": "strategy_evidence_policy.v1",
        "checks": {"pit": {"name": "时间点数据", "evidence_keys": ["pit_universe"]}},
        "required_by_lifecycle": {"pre_production": ["pit"]},
    }
    catalog = {
        "strategies": [{"id": "s", "lifecycle": "pre_production", "production_eligible": False}]
    }
    root = tmp_path
    (root / "strategy-research").mkdir(parents=True)
    (root / "strategy-research" / "evidence_policy.json").write_text(
        json.dumps(policy), encoding="utf-8"
    )
    (root / "strategy-research" / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    bundle_dir = root / "strategy-research" / "evidence"
    bundle_dir.mkdir(parents=True)
    bundle = {
        "schema_version": "strategy_evidence_bundle.v1",
        "strategy_id": "s",
        "checks": {
            "pit": {"outcome": "pass", "evidence": "docs/evidence/pit.json", "pit_universe": True}
        },
    }
    (bundle_dir / "s.json").write_text(json.dumps(bundle), encoding="utf-8")
    assert gate._run_gate(["--root", str(root), "--strict", "--zero-gaps"]) == 0
