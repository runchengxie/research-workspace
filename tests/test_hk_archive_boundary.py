from __future__ import annotations

import configparser
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ACTIVE_SUBMODULES = {
    "market-data-platform",
    "alpha-research",
    "portfolio-backtester",
    "strategy-pipeline",
    "quant-execution-engine",
}
REMOVED_ACTIVE_HK_SURFACES = (
    "demo/hk-public-demo-template-v1",
    "demo/hk-public-demo-allowlist-v1.txt",
    "demo/hk-public-demo-export-v1.json",
    "demo/hk-research-lane-template-v1",
    "scripts/export_hk_public_demo.py",
    "scripts/hk_public_demo_scan.py",
    "scripts/hk_research_lane_inventory.py",
    "market-data-platform/src/market_data_platform/hk_assets",
    "market-data-platform/src/market_data_platform/hk_depth",
    "market-data-platform/src/hk_data_platform",
    "strategy-pipeline/src/cstree/liveops/alloc_hk.py",
    "strategy-pipeline/configs/presets/data/hk_rqdata.yml",
)
REMOVED_ACTIVE_HK_GLOBS = (
    "strategy-pipeline/src/cstree/liveops/alloc_hk*.py",
    "strategy-pipeline/configs/presets/hk*.yml",
    "strategy-pipeline/configs/field_profiles/hk_*",
    "strategy-pipeline/configs/experiments/**/*hk*.yml",
)
CACHE_PARTS = {".pytest_cache", "__pycache__"}


def _load_json_subset(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _has_active_files(path: Path) -> bool:
    if path.is_file():
        return not any(part in CACHE_PARTS for part in path.parts)
    if not path.is_dir():
        return False
    return any(
        candidate.is_file() and not any(part in CACHE_PARTS for part in candidate.parts)
        for candidate in path.rglob("*")
    )


def test_hk_archives_stay_outside_active_submodule_graph() -> None:
    parser = configparser.ConfigParser()
    parser.read(ROOT / ".gitmodules", encoding="utf-8")
    paths = {parser.get(section, "path") for section in parser.sections()}
    urls = {parser.get(section, "url") for section in parser.sections()}
    private_archive = _load_json_subset("docs/hk-private-archive-manifest.yml")[
        "archive_repository"
    ]

    assert paths == EXPECTED_ACTIVE_SUBMODULES
    assert "hk-quant-legacy-archive" not in "\n".join(sorted(paths | urls))
    assert "hk-cross-sectional-strategy-demo" not in "\n".join(sorted(paths | urls))
    assert private_archive["workspace_integration"] == "external_not_submodule"
    assert private_archive["purpose"] == "restore_only"
    assert private_archive["visibility"] == "private"


def test_hk_archive_has_single_restore_entrypoint_and_no_public_followups() -> None:
    archive_index = (ROOT / "docs" / "archive" / "hk" / "README.md").read_text(encoding="utf-8")
    split_manifest = _load_json_subset("docs/hk-public-split-manifest.yml")
    follow_up = [
        record["id"]
        for record in split_manifest["records"]
        if record["deletion_gate"]["status"] in {"blocked_pending_audit", "follow_up_required"}
    ]

    assert "source_of_truth: yes" in archive_index
    assert "public demo 路线已经退役" in archive_index
    assert split_manifest["follow_up_budget"]["blocked_or_follow_up_records_max"] == 0
    assert follow_up == []


def test_removed_hk_business_surfaces_do_not_return_to_active_workspace() -> None:
    existing = [path for path in REMOVED_ACTIVE_HK_SURFACES if _has_active_files(ROOT / path)]
    glob_matches = [
        path.relative_to(ROOT).as_posix()
        for pattern in REMOVED_ACTIVE_HK_GLOBS
        for path in ROOT.glob(pattern)
    ]

    assert existing == []
    assert sorted(glob_matches) == []
