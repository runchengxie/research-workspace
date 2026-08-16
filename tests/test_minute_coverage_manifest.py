from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_research_module(filename: str, module_name: str):
    research_dir = (
        Path(__file__).resolve().parents[1]
        / "strategy-research"
        / "experiments"
        / "next_open_to_high"
    )
    module_path = research_dir / filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    sys.path.insert(0, str(research_dir))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(research_dir))
    return module


COVERAGE = _load_research_module(
    "a_share_next_open_to_high_coverage_manifest.py",
    "a_share_coverage_manifest_for_tests",
)


def test_default_coverage_manifest_tracks_resolved_minute_alias(tmp_path: Path) -> None:
    data_root = tmp_path / "market-data-platform"
    minute_parent = data_root / "assets/derived/a_share"
    version = minute_parent / "minute_1m_v3_20260714"
    version.mkdir(parents=True)
    current = minute_parent / "minute_1m"
    current.symlink_to(version.name)

    assert COVERAGE.coverage_manifest_for_minute_root(
        current,
        data_root=data_root,
    ) == (data_root / "metadata/minute_fusion/a_share_minute_1m_v3_20260714.coverage.json")
