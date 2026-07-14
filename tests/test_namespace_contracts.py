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


def test_manifest_declares_single_compatibility_owner() -> None:
    manifest = MODULE.load_manifest()
    assert manifest["compatibility"]["owner"] == "strategy-pipeline"
    assert manifest["compatibility"]["removal_release"] == "workspace-2.0"
