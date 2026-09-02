from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "research_contracts" / "smoke_contracts.py"
MANIFEST = ROOT / "docs" / "artifact-contracts.yml"

sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("smoke_contracts", SCRIPT)
smoke_contracts = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = smoke_contracts
spec.loader.exec_module(smoke_contracts)


def _load_contracts_package():
    contracts_src = ROOT / "src"
    if str(contracts_src) not in sys.path:
        sys.path.insert(0, str(contracts_src))
    import research_contracts

    return research_contracts


def _load_manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_artifact_contract_manifest_covers_stage3_core_handoff() -> None:
    manifest = _load_manifest()
    records = {
        str(record["artifact"]): record
        for record in manifest["artifacts"]  # type: ignore[index]
    }

    assert set(records) >= {
        "signals.parquet",
        "signals.meta.json",
        "positions_by_rebalance.csv",
        "selection_receipt.json",
        "targets.json",
        "watchlist_20.csv",
    }
    assert records["signals.parquet"]["owner"] == "alpha-research"
    assert "market-intel/hot-sector-screener" in records["signals.parquet"]["external_producers"]
    assert "confidence_score" in records["signals.parquet"]["optional_fields"]
    assert "daily_confirm_score" in records["signals.parquet"]["optional_fields"]
    assert records["positions_by_rebalance.csv"]["owner"] == "portfolio-backtester"
    assert records["targets.json"]["owner"] == "quant-execution-engine"
    assert records["targets.json"]["producer"] == "strategy-pipeline"
    assert records["targets.json"]["required_fields"] == ["targets", "symbol", "market"]
    assert records["targets.json"]["exactly_one_of_fields"] == [
        ["target_weight", "target_quantity"]
    ]
    assert records["watchlist_20.csv"]["owner"] == "strategy-pipeline"
    assert records["watchlist_20.csv"]["consumers"] == ["market-intel"]
    watchlist_notes = str(records["watchlist_20.csv"]["notes"])
    assert "Internal-only" in watchlist_notes
    assert "must not appear in the client renderer" in watchlist_notes
    assert "not a realtime feed" in watchlist_notes
    assert "eligible_for_live" in records["selection_receipt.json"]["required_fields"]


def test_orchestration_contract_identities_match_owner_packages() -> None:
    from alpha_research.signal_artifact import SIGNAL_CONTRACT_NAME as alpha_signal_name
    from portfolio_backtester.contracts import (
        BACKTEST_PRICING_CONTRACT_NAME as portfolio_pricing_name,
    )
    from portfolio_backtester.contracts import (
        STRATEGY_SPEC_CONTRACT_NAME as portfolio_strategy_name,
    )
    from strategy_pipeline.contracts.signals import (
        SIGNAL_CONTRACT_NAME as orchestration_signal_name,
    )

    records = {
        str(record["artifact"]): record
        for record in _load_manifest()["artifacts"]  # type: ignore[index]
    }
    assert alpha_signal_name == orchestration_signal_name == "alpha_research.signals"
    assert records["signals.parquet"]["contract"] == alpha_signal_name
    assert portfolio_pricing_name == "portfolio_backtester.backtest_pricing"
    assert portfolio_strategy_name == "portfolio_backtester.strategy_spec"


def test_artifact_contract_manifest_is_docs_and_path_validated() -> None:
    contracts = _load_contracts_package()
    result = contracts.validate_artifact_contract_manifest(
        root=ROOT,
        manifest_path=MANIFEST,
        docs_path=ROOT / "docs" / "contracts.md",
    )

    assert result.ok


def test_exactly_one_field_groups_reject_required_field_overlap(tmp_path: Path) -> None:
    contracts = _load_contracts_package()
    manifest = tmp_path / "artifact-contracts.yml"
    docs = tmp_path / "contracts.md"
    entrypoint = tmp_path / "quant-execution-engine" / "src" / "targets.py"
    entrypoint.parent.mkdir(parents=True)
    entrypoint.write_text("# fixture\n", encoding="utf-8")
    docs.write_text(
        "targets.json quant-execution-engine.targets/v2 quant-execution-engine",
        encoding="utf-8",
    )
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "artifact_contracts.v1",
                "artifact_envelope": {
                    "schema_version": "research.artifact-envelope.v2",
                    "write_mode": "opt_in",
                    "container_key": "artifact_envelope",
                    "required_fields": ["schema_version"],
                },
                "artifacts": [
                    {
                        "artifact": "targets.json",
                        "contract": "quant-execution-engine.targets/v2",
                        "owner": "quant-execution-engine",
                        "required_fields": ["targets", "symbol", "market", "target_weight"],
                        "exactly_one_of_fields": [["target_weight", "target_quantity"]],
                        "canonical_files": ["targets.json"],
                        "entrypoints": [
                            {
                                "repo": "quant-execution-engine",
                                "path": "src/targets.py",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = contracts.validate_artifact_contract_manifest(
        root=tmp_path,
        manifest_path=manifest,
        docs_path=docs,
        required_artifacts=("targets.json",),
    )

    assert (
        "targets.json: exactly_one_of_fields overlap required_fields: target_weight"
        in result.issues
    )


def test_shared_contract_package_loads_manifest() -> None:
    contracts = _load_contracts_package()
    manifest = contracts.load_artifact_contract_manifest(MANIFEST)

    assert manifest.schema_version == "artifact_contracts.v1"
    assert manifest.artifact_envelope["schema_version"] == "research.artifact-envelope.v2"
    assert manifest.artifact_envelope["write_mode"] == "opt_in"
    assert {str(record["artifact"]) for record in manifest.artifacts} >= {
        "signals.parquet",
        "positions_by_rebalance.csv",
        "selection_receipt.json",
        "targets.json",
        "watchlist_20.csv",
    }


def test_contract_smoke_includes_manifest_check() -> None:
    results = smoke_contracts.run_smoke(ROOT, timeout=30)

    assert results[0].name == "artifact contract manifest"
    assert results[0].severity == "OK"


def test_artifact_envelope_adoption_lists_match_producer_status() -> None:
    manifest = _load_manifest()
    envelope = manifest["artifact_envelope"]
    adopted = set(envelope["adopted_by"])
    pending = set(envelope["adoption_pending"])

    assert {
        "signals.parquet",
        "signals_style_replica.parquet",
        "positions_by_rebalance.csv",
        "targets.json",
    } <= adopted
    assert not pending
    assert not adopted.intersection(pending)


def test_contract_docs_do_not_claim_targets_envelope_is_pending() -> None:
    docs = (ROOT / "docs" / "contracts.md").read_text(encoding="utf-8")

    assert "`targets.json` 的导出方尚未接入" not in docs
