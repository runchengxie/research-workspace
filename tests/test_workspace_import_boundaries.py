from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "workspace_import_boundaries.py"

spec = importlib.util.spec_from_file_location("workspace_import_boundaries", SCRIPT)
workspace_import_boundaries = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = workspace_import_boundaries
spec.loader.exec_module(workspace_import_boundaries)


def test_current_workspace_import_boundary_budgets_hold() -> None:
    report = workspace_import_boundaries.build_report(ROOT)

    assert report["issues"] == []
    assert {
        "alpha-research:alpha-to-pipeline",
        "alpha-research:alpha-to-backtesting",
        "alpha-research:alpha-to-strategy-core-metrics",
        "alpha-research:alpha-to-strategy-compat",
        "alpha-research:alpha-to-strategy-rebalance",
        "alpha-research:alpha-to-strategy-signal-contract",
        "portfolio-backtester:backtesting-to-pipeline",
        "portfolio-backtester:backtesting-to-alpha",
        "portfolio-backtester:backtesting-to-strategy-core-metrics",
        "portfolio-backtester:backtesting-to-strategy-rebalance",
        "portfolio-backtester:backtesting-to-strategy-liquidity-proxy",
        "portfolio-backtester:backtesting-to-strategy-contracts",
        "market-data-platform:no-cstree-imports",
        "quant-execution-engine:no-cstree-imports",
        "strategy-pipeline:no-execution-engine-imports",
    } == {rule["id"] for rule in report["rules"]}
    assert {
        "strategy-pipeline:no-local-alpha-backtesting-source",
    } == {rule["id"] for rule in report["source_layout_rules"]}
    assert all(rule["count"] == 0 for rule in report["source_layout_rules"])


def test_relative_imports_are_resolved_against_namespace_package(tmp_path: Path) -> None:
    source = tmp_path / "alpha-research" / "src" / "cstree" / "alpha"
    source.mkdir(parents=True)
    (source / "example.py").write_text(
        textwrap.dedent(
            """
            from ..pipeline.dates import build_walk_forward_windows
            from cstree.backtesting.engine import backtest_topk
            """
        ),
        encoding="utf-8",
    )
    rules = (
        workspace_import_boundaries.BoundaryRule(
            identifier="alpha-to-pipeline",
            description="test",
            repo="alpha-research",
            source="src/cstree/alpha",
            forbidden=("cstree.pipeline",),
            max_allowed=0,
        ),
        workspace_import_boundaries.BoundaryRule(
            identifier="alpha-to-backtesting",
            description="test",
            repo="alpha-research",
            source="src/cstree/alpha",
            forbidden=("cstree.backtesting",),
            max_allowed=0,
        ),
    )

    report = workspace_import_boundaries.build_report(tmp_path, rules)

    assert report["issues"] == [
        "alpha-to-pipeline: 1 imports exceed budget 0",
        "alpha-to-backtesting: 1 imports exceed budget 0",
    ]


def test_strategy_pipeline_source_layout_rule_blocks_local_alpha_backtesting_code(
    tmp_path: Path,
) -> None:
    source = tmp_path / "strategy-pipeline" / "src" / "cstree" / "backtesting"
    source.mkdir(parents=True)
    (source / "engine.py").write_text("def backtest_topk():\n    return None\n", encoding="utf-8")
    rules = (
        workspace_import_boundaries.SourceLayoutRule(
            identifier="no-local-backtesting",
            description="test",
            repo="strategy-pipeline",
            forbidden_sources=("src/cstree/backtesting",),
            max_allowed=0,
        ),
    )

    report = workspace_import_boundaries.build_report(tmp_path, (), rules)

    assert report["issues"] == [
        "no-local-backtesting: 1 source files exceed budget 0",
    ]
    assert report["source_layout_rules"][0]["findings"] == [
        {
            "matched": "src/cstree/backtesting",
            "path": "strategy-pipeline/src/cstree/backtesting/engine.py",
        }
    ]
