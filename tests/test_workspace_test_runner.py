from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_workspace_tests.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_workspace_tests", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_source_roots(root: Path) -> list[Path]:
    relative = (
        "src",
        "market-data-platform/src",
        "alpha-research/src",
        "portfolio-backtester/src",
        "strategy-app/src",
        "strategy-pipeline/src",
    )
    paths = []
    for value in relative:
        path = root / value
        path.mkdir(parents=True, exist_ok=True)
        paths.append(path.resolve())
    return paths


def test_workspace_pythonpath_prefers_gitlink_source_trees(tmp_path: Path) -> None:
    module = _load_module()
    expected = _make_source_roots(tmp_path)

    value = module.workspace_pythonpath(tmp_path, existing="/external/site-packages")
    parts = [Path(item).resolve() for item in value.split(os.pathsep)]

    assert parts[: len(expected)] == expected
    assert parts[-1] == Path("/external/site-packages")


def test_workspace_pythonpath_rejects_missing_source_tree(tmp_path: Path) -> None:
    module = _load_module()
    _make_source_roots(tmp_path)
    missing = tmp_path / "alpha-research" / "src"
    missing.rmdir()

    with pytest.raises(module.WorkspaceSourceError, match="alpha-research/src"):
        module.workspace_pythonpath(tmp_path)


def test_pytest_command_uses_workspace_environment(tmp_path: Path) -> None:
    module = _load_module()

    command = module.pytest_command(tmp_path)

    assert command == (
        "uv",
        "run",
        "--project",
        str(tmp_path),
        "--group",
        "dev",
        "python",
        "-m",
        "pytest",
        str(tmp_path / "tests"),
        "--ignore",
        str(tmp_path / "tests/test_next_open_to_high_research.py"),
        "--ignore",
        str(tmp_path / "tests/test_next_open_to_high_research_part2.py"),
        "--ignore",
        str(tmp_path / "tests/test_private_research_config_boundary.py"),
        "-q",
    )
