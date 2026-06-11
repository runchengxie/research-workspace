from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = ROOT / "scripts" / "export_hk_public_demo.py"
GOVERNANCE_SCRIPT = ROOT / "scripts" / "workspace_governance.py"
sys.path.insert(0, str(EXPORT_SCRIPT.parent))

spec = importlib.util.spec_from_file_location("export_hk_public_demo", EXPORT_SCRIPT)
export_hk_public_demo = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = export_hk_public_demo
spec.loader.exec_module(export_hk_public_demo)

governance_spec = importlib.util.spec_from_file_location("workspace_governance", GOVERNANCE_SCRIPT)
workspace_governance = importlib.util.module_from_spec(governance_spec)
assert governance_spec.loader is not None
sys.modules[governance_spec.name] = workspace_governance
governance_spec.loader.exec_module(workspace_governance)


def _manifest() -> dict[str, object]:
    return export_hk_public_demo.load_split_manifest()


def test_hk_public_split_manifest_validates_schema_and_paths() -> None:
    manifest = _manifest()
    validation = export_hk_public_demo.validate_split_manifest(manifest)
    follow_up_count = sum(
        1
        for record in manifest["records"]
        if record["deletion_gate"]["status"] in {"blocked_pending_audit", "follow_up_required"}
    )

    assert validation["status"] == "passed", validation["issues"]
    assert manifest["schema_version"] == "hk_public_split_manifest.v1"
    assert {"blocked_or_follow_up_records_max", "policy"} <= set(manifest["follow_up_budget"])
    assert manifest["follow_up_budget"]["blocked_or_follow_up_records_max"] == follow_up_count
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
        "top-level-hk-research-lane-template",
    } <= record_ids


def test_hk_public_split_manifest_covers_hk_named_paths() -> None:
    manifest = _manifest()

    assert workspace_governance._uncovered_hk_split_paths(ROOT, manifest) == []


def test_hk_public_split_budget_blocks_new_follow_up_records() -> None:
    manifest = copy.deepcopy(_manifest())
    extra_record = copy.deepcopy(manifest["records"][0])
    extra_record["id"] = "new-hk-follow-up-surface"
    manifest["records"].append(extra_record)

    checks = workspace_governance.check_hk_public_split(ROOT, manifest)

    assert any(
        check.severity == "ERROR"
        and check.code == "governance-hk-public-split"
        and "HK split follow-up count" in check.message
        for check in checks
    )


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
