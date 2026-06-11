from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "a_share_readiness.py"
sys.path.insert(0, str(SCRIPT.parent))

spec = importlib.util.spec_from_file_location("a_share_readiness", SCRIPT)
a_share_readiness = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = a_share_readiness
spec.loader.exec_module(a_share_readiness)


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _build_contract(
    root: Path,
    *,
    legacy_alias: bool = False,
    include_complete_pit_assets: bool = True,
) -> None:
    assets = {}
    asset_keys = list(a_share_readiness.BASELINE_ASSETS)
    if include_complete_pit_assets:
        asset_keys.extend(a_share_readiness.COMPLETE_PIT_ASSETS)
    for asset_key in asset_keys:
        assets[asset_key] = {
            "exists": True,
            "manifest_path": f"/data/{asset_key}/manifest.yml",
            "manifest": {
                "status": "completed",
                "query_start_date": "20240229" if asset_key.startswith("universe_") else "20240102",
                "query_end_date": "20260529",
                "totals": {"rows": 3, "symbols": 2},
            },
            "as_of": "20260529",
        }
    _write_json(
        root / "metadata" / "current_assets" / "a_share_current.json",
        {
            "contract": {
                "market": "a_share",
                "provider": "tushare",
                "target_date": "20260529",
            },
            "assets": assets,
        },
    )
    if legacy_alias:
        _write_json(root / "metadata" / "current_assets" / "cn_current.json", {})
    registry = root / "metadata" / "dataset_registry.csv"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        "dataset_name,market\na_share_current_contract,a_share\n",
        encoding="utf-8",
    )


def _build_evidence(tmp_path: Path) -> Path:
    reports = tmp_path / "reports"
    for name in (
        "daily_clean",
        "universe",
        "benchmark",
        "cpcv",
        "feature",
        "final_oos",
        "turnover_cost",
        "capacity",
        "promotion",
    ):
        _write_json(reports / f"{name}.json", {"status": "passed"})
    run_dir = tmp_path / "runs" / "candidate"
    _write_json(run_dir / "summary.json", {"run": {"name": "candidate"}})
    (run_dir / "config.used.yml").write_text("market: a_share\n", encoding="utf-8")
    _write_json(run_dir / "inputs.lock.json", {"assets": {}})
    (run_dir / "positions_current.csv").write_text("symbol,weight\n600519.SH,1\n", encoding="utf-8")
    _write_json(
        tmp_path / "targets.json",
        {"targets": [{"symbol": "600519.SH", "market": "CN", "target_weight": 1.0}]},
    )
    _write_json(tmp_path / "targets.json.lineage.json", {"run": "candidate"})
    _write_json(
        reports / "qexec.json",
        {"status": "passed", "dry_run": True, "execute": False, "market": "CN"},
    )
    return _write_json(
        tmp_path / "evidence.json",
        {
            "daily_clean_validation_report": "reports/daily_clean.json",
            "universe_validation_report": "reports/universe.json",
            "research_run_dir": "runs/candidate",
            "targets_file": "targets.json",
            "targets_lineage_file": "targets.json.lineage.json",
            "qexec_dry_run_report": "reports/qexec.json",
            "benchmark_ladder_report": "reports/benchmark.json",
            "cpcv_report": "reports/cpcv.json",
            "feature_evidence_report": "reports/feature.json",
            "final_oos_or_substitute_report": "reports/final_oos.json",
            "turnover_cost_report": "reports/turnover_cost.json",
            "capacity_report": "reports/capacity.json",
            "promotion_gate_report": "reports/promotion.json",
            "research_profile": {
                "configured_start_date": "20240229",
                "universe": {"mode": "by_date", "point_in_time": True},
                "fundamentals": {rule: True for rule in a_share_readiness.PIT_FUNDAMENTALS_RULES},
                "industry": {rule: True for rule in a_share_readiness.HISTORICAL_INDUSTRY_RULES},
                "trading_rules": {rule: True for rule in a_share_readiness.SIDE_AWARE_RULES},
            },
        },
    )


def test_readiness_uses_canonical_contract_and_keeps_broker_separate(tmp_path: Path) -> None:
    _build_contract(tmp_path, legacy_alias=True)
    evidence = _build_evidence(tmp_path)

    report = a_share_readiness.build_readiness_report(tmp_path, evidence_manifest=evidence)

    assert report["levels"]["baseline_reproducible"]["passed"] is True
    assert report["levels"]["complete_pit_research_data"]["passed"] is True
    assert report["levels"]["production_strategy_evidence"]["passed"] is True
    assert report["levels"]["research_default_promotable"]["passed"] is True
    assert report["levels"]["broker_trading_enabled"]["passed"] is False
    assert report["summary"]["legacy_cn_alias_present"] is True


def test_readiness_reports_missing_evidence(tmp_path: Path) -> None:
    _build_contract(tmp_path)

    report = a_share_readiness.build_readiness_report(tmp_path)

    baseline = report["levels"]["baseline_reproducible"]
    assert baseline["passed"] is False
    assert "daily_clean_validation_report" in baseline["failed_checks"]
    assert "research_run_outputs" in baseline["failed_checks"]
    assert "targets_lineage" in baseline["failed_checks"]
    assert "qexec_cn_dry_run" in baseline["failed_checks"]
    complete_data = report["levels"]["complete_pit_research_data"]
    assert "profile:pit_fundamentals" in complete_data["failed_checks"]
    assert "profile:historical_industry" in complete_data["failed_checks"]


def test_readiness_requires_canonical_pit_fundamentals_assets(tmp_path: Path) -> None:
    _build_contract(tmp_path, include_complete_pit_assets=False)
    evidence = _build_evidence(tmp_path)

    report = a_share_readiness.build_readiness_report(tmp_path, evidence_manifest=evidence)

    complete_data = report["levels"]["complete_pit_research_data"]
    assert complete_data["passed"] is False
    assert "asset:pit_fundamentals" in complete_data["failed_checks"]
    assert "asset:industry_changes" in complete_data["failed_checks"]


def test_readiness_rejects_research_window_before_required_assets(tmp_path: Path) -> None:
    _build_contract(tmp_path)
    evidence = _build_evidence(tmp_path)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["research_profile"]["configured_start_date"] = "20150101"
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    report = a_share_readiness.build_readiness_report(tmp_path, evidence_manifest=evidence)

    assert report["levels"]["baseline_reproducible"]["passed"] is True
    complete_data = report["levels"]["complete_pit_research_data"]
    assert complete_data["passed"] is False
    assert "research_window" in complete_data["failed_checks"]


def test_readiness_records_disabled_pit_and_industry_as_pending_complete_support(
    tmp_path: Path,
) -> None:
    _build_contract(tmp_path)
    evidence = _build_evidence(tmp_path)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["research_profile"]["fundamentals"]["statement_features_enabled"] = False
    payload["research_profile"]["industry"]["historical_backtest_enabled"] = False
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    report = a_share_readiness.build_readiness_report(tmp_path, evidence_manifest=evidence)

    assert report["levels"]["baseline_reproducible"]["passed"] is True
    complete_data = report["levels"]["complete_pit_research_data"]
    assert complete_data["passed"] is False
    assert "profile:pit_fundamentals" in complete_data["failed_checks"]
    assert "profile:historical_industry" in complete_data["failed_checks"]


def test_readiness_rejects_qexec_report_that_claims_execute(tmp_path: Path) -> None:
    _build_contract(tmp_path)
    evidence = _build_evidence(tmp_path)
    _write_json(
        tmp_path / "reports" / "qexec.json",
        {"status": "passed", "dry_run": True, "execute": True, "market": "CN"},
    )

    report = a_share_readiness.build_readiness_report(tmp_path, evidence_manifest=evidence)

    assert report["levels"]["baseline_reproducible"]["passed"] is False
    assert "qexec_cn_dry_run" in report["levels"]["baseline_reproducible"]["failed_checks"]


def test_readiness_requires_capacity_report_for_production_strategy(tmp_path: Path) -> None:
    _build_contract(tmp_path)
    evidence = _build_evidence(tmp_path)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload.pop("capacity_report")
    evidence.write_text(json.dumps(payload), encoding="utf-8")

    report = a_share_readiness.build_readiness_report(tmp_path, evidence_manifest=evidence)

    assert report["levels"]["complete_pit_research_data"]["passed"] is True
    assert report["levels"]["production_strategy_evidence"]["passed"] is False
    assert "capacity_report" in report["levels"]["production_strategy_evidence"]["failed_checks"]
