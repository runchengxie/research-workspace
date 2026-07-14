from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "namespace_contracts", ROOT / "scripts/namespace_contracts.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_owner_native_manifest_matches_gitlinks() -> None:
    assert MODULE.check_manifest() == []


def test_manifest_records_removed_compatibility_surface() -> None:
    manifest = MODULE.load_manifest()
    assert manifest["schema"] == "owner_native_namespace_release.v2"
    assert manifest["compatibility"]["owner"] == "strategy-pipeline"
    assert manifest["compatibility"]["removed_in"] == "workspace-2.0"
    assert manifest["compatibility"]["status"] == "removed"
    assert manifest["packages"]["alpha-research"]["version"] == "0.3.0"
    assert manifest["packages"]["portfolio-backtester"]["version"] == "0.3.0"
    assert manifest["packages"]["strategy-pipeline"]["version"] == "2.0.0"
    assert manifest["packages"]["strategy-pipeline"]["compatibility_package_allowed"] is False
