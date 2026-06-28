from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "smoke_contracts.py"
MANIFEST = ROOT / "docs" / "artifact-contracts.yml"

sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("smoke_contracts", SCRIPT)
smoke_contracts = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = smoke_contracts
spec.loader.exec_module(smoke_contracts)


def _load_contracts_package():
    contracts_src = ROOT / "research-contracts" / "src"
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
        "targets.json",
    }
    assert records["signals.parquet"]["owner"] == "alpha-research"
    assert records["positions_by_rebalance.csv"]["owner"] == "portfolio-backtester"
    assert records["targets.json"]["owner"] == "quant-execution-engine"
    assert records["targets.json"]["producer"] == "strategy-pipeline"


def test_artifact_contract_manifest_is_docs_and_path_validated() -> None:
    contracts = _load_contracts_package()
    result = contracts.validate_artifact_contract_manifest(
        root=ROOT,
        manifest_path=MANIFEST,
        docs_path=ROOT / "docs" / "contracts.md",
    )

    assert result.ok


def test_shared_contract_package_loads_manifest() -> None:
    contracts = _load_contracts_package()
    manifest = contracts.load_artifact_contract_manifest(MANIFEST)

    assert manifest.schema_version == "artifact_contracts.v1"
    assert {str(record["artifact"]) for record in manifest.artifacts} >= {
        "signals.parquet",
        "positions_by_rebalance.csv",
        "targets.json",
    }


def test_contract_smoke_includes_manifest_check() -> None:
    results = smoke_contracts.run_smoke(ROOT, timeout=30)

    assert results[0].name == "artifact contract manifest"
    assert results[0].severity == "OK"
