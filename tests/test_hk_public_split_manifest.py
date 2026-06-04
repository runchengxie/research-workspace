from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = ROOT / "scripts" / "export_hk_public_demo.py"

spec = importlib.util.spec_from_file_location("export_hk_public_demo", EXPORT_SCRIPT)
export_hk_public_demo = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = export_hk_public_demo
spec.loader.exec_module(export_hk_public_demo)


def _manifest() -> dict[str, object]:
    return export_hk_public_demo.load_split_manifest()


def test_hk_public_split_manifest_validates_schema_and_paths() -> None:
    manifest = _manifest()
    validation = export_hk_public_demo.validate_split_manifest(manifest)

    assert validation["status"] == "passed", validation["issues"]
    assert manifest["schema_version"] == "hk_public_split_manifest.v1"
    assert {
        "keep_in_main",
        "move_to_public_demo",
        "archive_in_public_demo",
        "delete_after_split",
        "private_do_not_export",
    } == set(manifest["actions"])
    assert {
        "docs/archive/hk/README.md",
        "docs/hk-legacy-surface-inventory.md",
        "docs/hk-public-demo-export.md",
        "demo/hk-public-demo-allowlist-v1.txt",
    } <= set(manifest["generated_from"])


def test_hk_public_split_manifest_has_unique_required_surface_ids() -> None:
    manifest = _manifest()
    record_ids = {record["id"] for record in manifest["records"]}

    assert len(record_ids) == len(manifest["records"])
    assert {
        "market-data-platform-hk-assets-and-depth",
        "market-data-platform-legacy-hk-entrypoints",
        "strategy-research-hk-allocation-compat",
        "strategy-research-hk-configs",
        "execution-longport-runtime",
        "top-level-hk-public-demo-staging",
    } <= record_ids


def test_hk_public_split_manifest_ready_cleanup_requires_evidence() -> None:
    manifest = copy.deepcopy(_manifest())
    first_record = manifest["records"][0]
    first_record["deletion_gate"]["status"] = "ready"
    first_record["deletion_gate"]["consumer_audit"] = "pending"

    validation = export_hk_public_demo.validate_split_manifest(manifest)

    assert validation["status"] == "failed"
    assert {
        "path": first_record["id"],
        "check": "ready_gate_blocked_consumer_audit",
    } in validation["issues"]


def test_hk_public_demo_allowlist_matches_template_files() -> None:
    template_root = ROOT / "demo" / "hk-public-demo-template-v1"
    allowlist_path = ROOT / "demo" / "hk-public-demo-allowlist-v1.txt"
    allowed = {
        line.strip()
        for line in allowlist_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    actual = {
        path.relative_to(template_root).as_posix()
        for path in template_root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
        and "samples" not in path.parts
    }

    assert actual == allowed
