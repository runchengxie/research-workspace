from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "workspace_import_boundaries.py"

spec = importlib.util.spec_from_file_location("workspace_import_boundaries", SCRIPT)
workspace_import_boundaries = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = workspace_import_boundaries
spec.loader.exec_module(workspace_import_boundaries)


def _submodules_initialized() -> bool:
    return all(
        path.is_file()
        for path in (
            ROOT / "alpha-research/src/alpha_research/__init__.py",
            ROOT / "portfolio-backtester/src/portfolio_backtester/__init__.py",
            ROOT / "strategy-pipeline/src/strategy_pipeline/__init__.py",
            ROOT / "market-data-platform/src/market_data_platform/__init__.py",
            ROOT / "quant-execution-engine/src/quant_execution_engine/__init__.py",
            ROOT / "strategy-app/src/strategy_app/__init__.py",
        )
    )


def test_current_workspace_import_boundary_budgets_hold() -> None:
    if not _submodules_initialized():
        pytest.skip("source-level boundary scan requires initialized submodules")

    report = workspace_import_boundaries.build_report(ROOT)

    assert report["issues"] == []
    assert {
        "research-workspace:contracts-no-direct-framework-imports",
        "alpha-research:alpha-to-pipeline",
        "alpha-research:alpha-to-backtesting",
        "alpha-research:alpha-to-execution",
        "alpha-research:alpha-to-strategy-core-metrics",
        "alpha-research:alpha-to-strategy-compat",
        "alpha-research:alpha-to-strategy-rebalance",
        "alpha-research:alpha-to-strategy-signal-contract",
        "portfolio-backtester:backtesting-to-pipeline",
        "portfolio-backtester:backtesting-to-alpha",
        "portfolio-backtester:backtesting-to-execution",
        "portfolio-backtester:backtesting-to-strategy-core-metrics",
        "portfolio-backtester:backtesting-to-strategy-rebalance",
        "portfolio-backtester:backtesting-to-strategy-liquidity-proxy",
        "portfolio-backtester:backtesting-to-strategy-contracts",
        "market-data-platform:no-legacy-shared-namespace-imports",
        "quant-execution-engine:no-legacy-shared-namespace-imports",
        "quant-execution-engine:no-research-runtime-imports",
        "strategy-app:no-control-plane-imports",
        "strategy-app:no-execution-runtime-imports",
        "strategy-research:no-control-or-execution-runtime-imports",
        "strategy-pipeline:no-execution-engine-imports",
        "strategy-pipeline:contracts-pure-handoff",
        "strategy-pipeline:liveops-no-cli-backedge",
        "strategy-pipeline:pipeline-no-cli-backedge",
        "strategy-pipeline:target-contract-no-direct-framework-imports",
        "market-data-platform:published-contract-no-direct-qlib-imports",
        "alpha-research:signal-contract-no-direct-qlib-imports",
        "portfolio-backtester:contracts-no-direct-framework-imports",
        "quant-execution-engine:domain-no-direct-vnpy-imports",
        "quant-execution-engine:legacy-domain-no-direct-vnpy-imports",
        "quant-execution-engine:targets-no-direct-vnpy-imports",
        "research-workspace:legacy-hotsector-internal-imports",
    } == {rule["id"] for rule in report["rules"]}
    assert {
        "strategy-pipeline:no-local-alpha-backtesting-source",
        "strategy-pipeline:no-local-strategy-app-source",
    } == {rule["id"] for rule in report["source_layout_rules"]}
    assert all(rule["count"] == 0 for rule in report["source_layout_rules"])
    assert {
        "strategy-app:no-cross-repo-private-imports",
        "strategy-pipeline:no-cross-repo-private-imports",
        "strategy-research:no-owner-private-test-imports",
    } == {rule["id"] for rule in report["private_import_rules"]}
    assert all(rule["count"] == 0 for rule in report["private_import_rules"])


def test_owner_native_cross_imports_are_detected(tmp_path: Path) -> None:
    source = tmp_path / "alpha-research" / "src" / "alpha_research"
    source.mkdir(parents=True)
    (source / "example.py").write_text(
        textwrap.dedent(
            """
            from strategy_pipeline.pipeline.dates import build_walk_forward_windows
            from portfolio_backtester.engine import backtest_topk
            """
        ),
        encoding="utf-8",
    )
    rules = (
        workspace_import_boundaries.BoundaryRule(
            identifier="alpha-to-pipeline",
            description="test",
            repo="alpha-research",
            source="src/alpha_research",
            forbidden=("strategy_pipeline",),
            max_allowed=0,
        ),
        workspace_import_boundaries.BoundaryRule(
            identifier="alpha-to-backtesting",
            description="test",
            repo="alpha-research",
            source="src/alpha_research",
            forbidden=("portfolio_backtester",),
            max_allowed=0,
        ),
    )

    report = workspace_import_boundaries.build_report(tmp_path, rules)

    assert report["issues"] == [
        "alpha-to-pipeline: 1 imports exceed budget 0",
        "alpha-to-backtesting: 1 imports exceed budget 0",
    ]


def test_cross_repo_private_symbols_are_detected(tmp_path: Path) -> None:
    source = tmp_path / "strategy-app" / "src" / "strategy_app"
    source.mkdir(parents=True)
    (source / "example.py").write_text(
        textwrap.dedent(
            """
            from portfolio_backtester.daily_watch20_oos import _portfolio_daily_rows
            from alpha_research._internal import public_name
            """
        ),
        encoding="utf-8",
    )
    private_rules = (
        workspace_import_boundaries.PrivateImportRule(
            identifier="no-private",
            description="test",
            repo="strategy-app",
            source="src/strategy_app",
            external_roots=("portfolio_backtester", "alpha_research"),
            max_allowed=0,
        ),
    )

    report = workspace_import_boundaries.build_report(tmp_path, (), (), private_rules)

    assert report["issues"] == ["no-private: 2 private imports exceed budget 0"]
    assert [finding["module"] for finding in report["private_import_rules"][0]["findings"]] == [
        "portfolio_backtester.daily_watch20_oos._portfolio_daily_rows",
        "alpha_research._internal.public_name",
    ]


def test_execution_runtime_cross_edges_are_detected(tmp_path: Path) -> None:
    portfolio_source = tmp_path / "portfolio-backtester" / "src" / "portfolio_backtester"
    portfolio_source.mkdir(parents=True)
    (portfolio_source / "sim.py").write_text(
        "from quant_execution_engine.domain import OrderIntent\n",
        encoding="utf-8",
    )
    execution_source = tmp_path / "quant-execution-engine" / "src" / "quant_execution_engine"
    execution_source.mkdir(parents=True)
    (execution_source / "planner.py").write_text(
        textwrap.dedent(
            """
            from alpha_research.metrics import summarize_ic
            from portfolio_backtester.engine import backtest_topk
            """
        ),
        encoding="utf-8",
    )
    rules = (
        workspace_import_boundaries.BoundaryRule(
            identifier="portfolio-to-execution",
            description="test",
            repo="portfolio-backtester",
            source="src/portfolio_backtester",
            forbidden=("quant_execution_engine",),
            max_allowed=0,
        ),
        workspace_import_boundaries.BoundaryRule(
            identifier="execution-to-research",
            description="test",
            repo="quant-execution-engine",
            source="src/quant_execution_engine",
            forbidden=("alpha_research", "portfolio_backtester"),
            max_allowed=0,
        ),
    )

    report = workspace_import_boundaries.build_report(tmp_path, rules)

    assert report["issues"] == [
        "portfolio-to-execution: 1 imports exceed budget 0",
        "execution-to-research: 2 imports exceed budget 0",
    ]


def test_strategy_research_cannot_import_control_or_execution_runtime(tmp_path: Path) -> None:
    source = tmp_path / "strategy-research" / "src" / "style_factors"
    source.mkdir(parents=True)
    (source / "example.py").write_text(
        textwrap.dedent(
            """
            from strategy_pipeline.pipeline.runner import run_pipeline
            from quant_execution_engine.targets import read_targets_json
            """
        ),
        encoding="utf-8",
    )
    rules = (
        workspace_import_boundaries.BoundaryRule(
            identifier="strategy-research-no-runtime",
            description="test",
            repo="strategy-research",
            source="src/style_factors",
            forbidden=("strategy_pipeline", "quant_execution_engine"),
            max_allowed=0,
        ),
    )

    report = workspace_import_boundaries.build_report(tmp_path, rules)

    assert report["issues"] == ["strategy-research-no-runtime: 2 imports exceed budget 0"]
    assert [finding["matched"] for finding in report["rules"][0]["findings"]] == [
        "strategy_pipeline",
        "quant_execution_engine",
    ]


@pytest.mark.parametrize(
    ("statement", "framework"),
    (
        ("from qlib.data.dataset import DatasetH\n", "qlib"),
        ("import backtrader\n", "backtrader"),
    ),
)
def test_single_file_contract_rule_blocks_optional_framework_import(
    tmp_path: Path,
    statement: str,
    framework: str,
) -> None:
    contract = tmp_path / "owner" / "src" / "owner" / "contract.py"
    contract.parent.mkdir(parents=True)
    contract.write_text(statement, encoding="utf-8")
    rules = (
        workspace_import_boundaries.BoundaryRule(
            identifier="contract-no-framework",
            description="test",
            repo="owner",
            source="src/owner/contract.py",
            forbidden=(framework,),
            max_allowed=0,
        ),
    )

    report = workspace_import_boundaries.build_report(tmp_path, rules, ())

    assert report["issues"] == ["contract-no-framework: 1 imports exceed budget 0"]
    assert report["rules"][0]["findings"] == [
        {
            "path": "owner/src/owner/contract.py",
            "line": 1,
            "module": "qlib.data.dataset" if framework == "qlib" else "backtrader",
            "matched": framework,
        }
    ]


def test_strategy_pipeline_source_layout_rule_blocks_embedded_owner_code(
    tmp_path: Path,
) -> None:
    source = tmp_path / "strategy-pipeline" / "src" / "portfolio_backtester"
    source.mkdir(parents=True)
    (source / "engine.py").write_text(
        "def backtest_topk():\n    return None\n",
        encoding="utf-8",
    )
    rules = (
        workspace_import_boundaries.SourceLayoutRule(
            identifier="no-local-backtesting",
            description="test",
            repo="strategy-pipeline",
            forbidden_sources=("src/portfolio_backtester",),
            max_allowed=0,
        ),
    )

    report = workspace_import_boundaries.build_report(tmp_path, (), rules)

    assert report["issues"] == [
        "no-local-backtesting: 1 source files exceed budget 0",
    ]
    assert report["source_layout_rules"][0]["findings"] == [
        {
            "matched": "src/portfolio_backtester",
            "path": "strategy-pipeline/src/portfolio_backtester/engine.py",
        }
    ]


def test_strategy_pipeline_contract_boundary_blocks_runtime_back_edges(
    tmp_path: Path,
) -> None:
    source = tmp_path / "strategy-pipeline" / "src" / "strategy_pipeline" / "contracts"
    source.mkdir(parents=True)
    (source / "signals.py").write_text(
        textwrap.dedent(
            """
            from ..pipeline.runner import run_pipeline
            from ..liveops.export_targets import main as export_targets
            from ..cli import build_parser
            from quant_execution_engine.targets import TargetSet
            """
        ),
        encoding="utf-8",
    )
    rules = (
        workspace_import_boundaries.BoundaryRule(
            identifier="contracts-pure-handoff",
            description="test",
            repo="strategy-pipeline",
            source="src/strategy_pipeline/contracts",
            forbidden=(
                "strategy_pipeline.pipeline",
                "strategy_pipeline.liveops",
                "strategy_pipeline.cli",
                "quant_execution_engine",
            ),
            max_allowed=0,
        ),
    )

    report = workspace_import_boundaries.build_report(tmp_path, rules)

    assert report["issues"] == [
        "contracts-pure-handoff: 4 imports exceed budget 0",
    ]
    assert [finding["matched"] for finding in report["rules"][0]["findings"]] == [
        "strategy_pipeline.pipeline",
        "strategy_pipeline.liveops",
        "strategy_pipeline.cli",
        "quant_execution_engine",
    ]


def test_strategy_pipeline_runtime_layers_cannot_import_cli(tmp_path: Path) -> None:
    liveops = tmp_path / "strategy-pipeline" / "src" / "strategy_pipeline" / "liveops"
    pipeline = tmp_path / "strategy-pipeline" / "src" / "strategy_pipeline" / "pipeline"
    liveops.mkdir(parents=True)
    pipeline.mkdir(parents=True)
    (liveops / "runner.py").write_text("from ..cli import build_parser\n", encoding="utf-8")
    (pipeline / "runner.py").write_text("from ..cli.core import handle_run\n", encoding="utf-8")
    rules = (
        workspace_import_boundaries.BoundaryRule(
            identifier="liveops-no-cli",
            description="test",
            repo="strategy-pipeline",
            source="src/strategy_pipeline/liveops",
            forbidden=("strategy_pipeline.cli",),
            max_allowed=0,
        ),
        workspace_import_boundaries.BoundaryRule(
            identifier="pipeline-no-cli",
            description="test",
            repo="strategy-pipeline",
            source="src/strategy_pipeline/pipeline",
            forbidden=("strategy_pipeline.cli",),
            max_allowed=0,
        ),
    )

    report = workspace_import_boundaries.build_report(tmp_path, rules)

    assert report["issues"] == [
        "liveops-no-cli: 1 imports exceed budget 0",
        "pipeline-no-cli: 1 imports exceed budget 0",
    ]
