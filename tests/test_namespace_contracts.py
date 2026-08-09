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


def test_gitlink_sha_reads_the_staged_index(monkeypatch) -> None:
    calls: list[list[str]] = []
    sha = "1" * 40

    def fake_check_output(command, **_kwargs) -> str:
        calls.append(command)
        return f"160000 {sha} 0\tstrategy-pipeline\n"

    monkeypatch.setattr(MODULE.subprocess, "check_output", fake_check_output)

    assert MODULE.gitlink_sha("strategy-pipeline") == sha
    assert calls == [["git", "ls-files", "--stage", "--", "strategy-pipeline"]]


def test_manifest_records_removed_compatibility_surface() -> None:
    manifest = MODULE.load_manifest()
    assert manifest["schema"] == "owner_native_namespace_release.v2"
    assert manifest["compatibility"]["owner"] == "strategy-pipeline"
    assert manifest["compatibility"]["removed_in"] == "workspace-2.0"
    assert manifest["compatibility"]["status"] == "removed"
    assert manifest["packages"]["alpha-research"]["version"] == "0.4.0"
    assert manifest["packages"]["portfolio-backtester"]["version"] == "0.4.0"
    assert manifest["packages"]["strategy-app"]["canonical_package"] == "strategy_app"
    assert manifest["packages"]["strategy-app"]["version"] == "0.2.0"
    assert manifest["packages"]["strategy-pipeline"]["version"] == "2.1.0"
    assert manifest["packages"]["strategy-pipeline"]["compatibility_package_allowed"] is False
