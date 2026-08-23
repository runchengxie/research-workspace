from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "workspace_ownership_boundaries.py"

spec = importlib.util.spec_from_file_location("workspace_ownership_boundaries", SCRIPT)
workspace_ownership_boundaries = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = workspace_ownership_boundaries
spec.loader.exec_module(workspace_ownership_boundaries)


def _strategy_app_initialized() -> bool:
    return (ROOT / "strategy-app/src/strategy_app/__init__.py").is_file()


def test_current_workspace_ownership_budgets_hold() -> None:
    if not _strategy_app_initialized():
        pytest.skip("ownership scan requires initialized strategy-app submodule")

    report = workspace_ownership_boundaries.build_report(ROOT)

    assert report["issues"] == []
    rules = {rule["id"]: rule for rule in report["rules"]}
    assert rules["strategy-app:numeric-v2-adapter-only"]["count"] <= 7
    assert rules["strategy-app:numeric-v2-adapter-only"]["target_max_unowned_definitions"] == 0
    assert rules["strategy-app:holdings-overlay-app-shell"]["count"] <= 1
    assert rules["strategy-app:holdings-overlay-app-shell"]["target_max_unowned_definitions"] == 0


def test_unowned_top_level_definition_breaks_zero_budget(tmp_path: Path) -> None:
    source = tmp_path / "strategy-app" / "src" / "strategy_app" / "hotsector" / "adapter.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        textwrap.dedent(
            """
            def allowed_adapter():
                return None

            def reusable_scoring_kernel():
                return 1.0
            """
        ),
        encoding="utf-8",
    )
    rules = (
        workspace_ownership_boundaries.OwnershipRule(
            identifier="adapter-only",
            description="test",
            repo="strategy-app",
            source="src/strategy_app/hotsector/adapter.py",
            allowed_definitions=("allowed_adapter",),
            max_unowned_definitions=0,
            target_max_unowned_definitions=0,
        ),
    )

    report = workspace_ownership_boundaries.build_report(tmp_path, rules)

    assert report["issues"] == ["adapter-only: 1 unowned definitions exceed budget 0"]
    assert report["rules"][0]["findings"] == [
        {
            "path": "strategy-app/src/strategy_app/hotsector/adapter.py",
            "line": 5,
            "name": "reusable_scoring_kernel",
            "kind": "function",
        }
    ]
