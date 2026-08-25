from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from research_contracts.promotion_evidence import validate_strategy_promotion  # noqa: E402
from research_contracts.promotion_evidence_checks import check_errors  # noqa: E402

GATE_SCRIPT = ROOT / "scripts" / "strategy_evidence_gate.py"
GATE_SPEC = importlib.util.spec_from_file_location("strategy_evidence_gate_promotion", GATE_SCRIPT)
gate = importlib.util.module_from_spec(GATE_SPEC)
assert GATE_SPEC.loader is not None
sys.modules[GATE_SPEC.name] = gate
GATE_SPEC.loader.exec_module(gate)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _profiles() -> dict[str, Any]:
    return {
        "schema_version": "strategy_promotion_profiles.v1",
        "strategy_profiles": {"s": "a_share_long_window"},
        "profiles": {
            "a_share_long_window": {
                "configured_start_date": "20150101",
                "current_contract_path": "metadata/current_assets/a_share_current.json",
                "required_current_assets": ["daily_clean", "pit_fundamentals"],
                "required_profile_checks": ["capacity"],
            }
        },
    }


def _fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    root = tmp_path / "workspace"
    data_root = tmp_path / "data-platform"
    config = root / "strategy-pipeline/configs/a_share_long_window.yml"
    source = root / "strategy-pipeline/docs/evidence/final.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("data:\n  start_date: '20150101'\n", encoding="utf-8")
    _write_json(source, {"status": "passed"})

    assets: dict[str, Any] = {}
    manifest_entries: list[dict[str, Any]] = []
    for asset_key in ("daily_clean", "pit_fundamentals"):
        manifest_path = f"assets/{asset_key}/manifest.json"
        manifest = data_root / manifest_path
        _write_json(
            manifest,
            {
                "status": "completed",
                "query_start_date": "20150101",
                "query_end_date": "20260821",
            },
        )
        assets[asset_key] = {
            "exists": True,
            "manifest_path": manifest_path,
            "manifest": {
                "status": "completed",
                "query_start_date": "20150101",
                "query_end_date": "20260821",
            },
        }
        manifest_entries.append(
            {
                "asset_key": asset_key,
                "path": manifest_path,
                "sha256": _sha256(manifest),
            }
        )

    contract_path = data_root / "metadata/current_assets/a_share_current.json"
    _write_json(contract_path, {"contract": {"market": "a_share"}, "assets": assets})

    receipt_path = root / "strategy-research/evidence/promotion/s/review.json"
    receipt: dict[str, Any] = {
        "schema_version": "strategy_promotion_evidence.v2",
        "strategy_id": "s",
        "profile_id": "a_share_long_window",
        "review_id": "review",
        "generated_at": "2026-08-25T11:00:00+00:00",
        "status": "passed",
        "research_window": {
            "configured_start_date": "20150101",
            "end_date": "20260821",
        },
        "lineage": {
            "producer_repository": "strategy-pipeline",
            "repositories": {"strategy-pipeline": "a" * 40},
            "config": {
                "path": "strategy-pipeline/configs/a_share_long_window.yml",
                "sha256": _sha256(config),
            },
            "current_contract": {
                "path": "metadata/current_assets/a_share_current.json",
                "sha256": _sha256(contract_path),
            },
            "data_manifests": manifest_entries,
            "source_artifacts": [
                {
                    "location": "workspace",
                    "path": "strategy-pipeline/docs/evidence/final.json",
                    "sha256": _sha256(source),
                }
            ],
        },
        "checks": {
            "pit": {
                "status": "passed",
                "pit_universe": True,
                "pit_fundamentals": True,
                "pit_industry_membership": True,
            },
            "capacity": {
                "status": "passed",
                "portfolio_values": [1_000_000.0, 5_000_000.0],
                "participation_rates": [0.02, 0.05],
                "primary_participation_rate": 0.05,
                "recommended_capacity": 1_000_000.0,
            },
        },
        "limitations": [],
    }
    _write_json(receipt_path, receipt)
    bundle: dict[str, Any] = {
        "checks": {
            "pit": {
                "outcome": "pass",
                "evidence": "docs/evidence/legacy-pit.json",
                "pit_universe": True,
            }
        },
        "promotion_evidence": {
            "pit": "strategy-research/evidence/promotion/s/review.json",
            "capacity": "strategy-research/evidence/promotion/s/review.json",
        },
        "known_gaps": [],
    }
    return root, data_root, bundle, receipt


def _validate(
    root: Path,
    data_root: Path | None,
    bundle: dict[str, Any],
    *,
    git_sha: str = "a" * 40,
):
    return validate_strategy_promotion(
        root=root,
        strategy_id="s",
        required_checks=["pit"],
        bundle=bundle,
        profiles=_profiles(),
        data_platform_root=data_root,
        gitlinks={"strategy-pipeline": git_sha},
    )


def test_valid_canonical_receipt_passes_source_and_profile_checks(tmp_path: Path) -> None:
    root, data_root, bundle, _receipt = _fixture(tmp_path)

    result = _validate(root, data_root, bundle)

    assert result.passed is True
    assert result.profile_id == "a_share_long_window"
    assert result.validated_checks == ["pit", "capacity"]
    assert result.invalid_evidence == {}
    assert result.profile_failures == []


def test_missing_promotion_source_is_reported_without_changing_lifecycle_count(
    tmp_path: Path,
) -> None:
    root, data_root, bundle, _receipt = _fixture(tmp_path)
    promotion = bundle["promotion_evidence"]
    promotion.pop("pit")

    result = _validate(root, data_root, bundle)

    assert result.invalid_evidence == {"pit": ["missing_promotion_evidence"]}
    assert "capacity" in result.validated_checks


def test_diagnostic_receipt_fails_closed(tmp_path: Path) -> None:
    root, data_root, bundle, receipt = _fixture(tmp_path)
    receipt["status"] = "diagnostic"
    _write_json(root / "strategy-research/evidence/promotion/s/review.json", receipt)

    result = _validate(root, data_root, bundle)

    assert "receipt_not_passed" in result.invalid_evidence["pit"]
    assert "capacity_not_passed" in result.profile_failures


def test_config_hash_drift_fails_closed(tmp_path: Path) -> None:
    root, data_root, bundle, _receipt = _fixture(tmp_path)
    config = root / "strategy-pipeline/configs/a_share_long_window.yml"
    config.write_text("data:\n  start_date: '20200101'\n", encoding="utf-8")

    result = _validate(root, data_root, bundle)

    assert "config_hash_mismatch" in result.invalid_evidence["pit"]


def test_missing_data_root_fails_closed(tmp_path: Path) -> None:
    root, _data_root, bundle, _receipt = _fixture(tmp_path)

    result = _validate(root, None, bundle)

    assert "data_root_unavailable" in result.invalid_evidence["pit"]
    assert "capacity_not_passed" in result.profile_failures


def test_gitlink_mismatch_fails_closed(tmp_path: Path) -> None:
    root, data_root, bundle, _receipt = _fixture(tmp_path)

    result = _validate(root, data_root, bundle, git_sha="b" * 40)

    assert "repository_commit_mismatch" in result.invalid_evidence["pit"]


def test_stale_research_window_fails_closed(tmp_path: Path) -> None:
    root, data_root, bundle, receipt = _fixture(tmp_path)
    receipt["research_window"]["end_date"] = "20260820"
    _write_json(root / "strategy-research/evidence/promotion/s/review.json", receipt)

    result = _validate(root, data_root, bundle)

    assert "evidence_window_stale" in result.invalid_evidence["pit"]


def test_negative_performance_values_are_valid_metrics() -> None:
    receipt = {
        "checks": {
            "cost": {
                "status": "passed",
                "turnover": 0.7,
                "scenarios": [
                    {"cost_bps": 10.0, "metric": "net_return", "value": -0.05},
                    {"cost_bps": 30.0, "metric": "net_return", "value": -0.12},
                ],
            },
            "regime": {
                "status": "passed",
                "metric": "return",
                "regimes": [
                    {"id": "bull", "value": 0.2},
                    {"id": "bear", "value": -0.3},
                    {"id": "sideways", "value": -0.01},
                ],
            },
        }
    }

    assert check_errors(receipt, "cost") == []
    assert check_errors(receipt, "regime") == []


def test_zero_gaps_blocks_invalid_canonical_sources_but_strict_does_not() -> None:
    result = gate.StrategyResult(
        strategy_id="s",
        lifecycle="pre_production",
        required=["pit"],
        present=["pit"],
        missing=[],
        verdict=True,
        invalid_evidence={"pit": ["missing_promotion_evidence"]},
    )

    assert gate._blocked_strategy_ids([result], zero_gaps=False) == []
    assert gate._blocked_strategy_ids([result], zero_gaps=True) == ["s"]


def test_promotion_source_count_excludes_profile_only_capacity() -> None:
    result = gate.StrategyResult(
        strategy_id="s",
        lifecycle="pre_production",
        required=["pit"],
        present=["pit"],
        missing=[],
        verdict=True,
        promotion_profile="a_share_long_window",
        validated_promotion_checks=["capacity"],
    )

    assert gate._promotion_cells(result) == ("0/1", "通过")


def test_real_promotion_profiles_cover_all_e2_strategies() -> None:
    path = ROOT / "strategy-research" / "promotion_profiles.json"
    profiles = json.loads(path.read_text(encoding="utf-8"))
    mappings = profiles["strategy_profiles"]

    assert mappings == {
        "daily_watch20": "a_share_long_window",
        "hotsector": "a_share_long_window",
        "style_replica_a80_b20": "a_share_long_window",
        "d11_h5_shadow": "a_share_long_window",
        "dividend_growth_momentum": "a_share_long_window",
    }
