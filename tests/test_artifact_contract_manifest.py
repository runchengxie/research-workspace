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
    result = smoke_contracts._artifact_contract_manifest_check(ROOT)

    assert result.severity == "OK"
    assert result.message == "passed"


def test_contract_smoke_includes_manifest_check() -> None:
    results = smoke_contracts.run_smoke(ROOT, timeout=30)

    assert results[0].name == "artifact contract manifest"
    assert results[0].severity == "OK"
