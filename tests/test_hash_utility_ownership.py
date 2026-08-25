from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HASH_FUNCTION_NAMES = {"file_sha256", "sha256_file"}
ALLOWED_HASH_DEFINITIONS = {
    "src/research_contracts/file_receipts.py",
    "strategy-research/style_factors/robustness_sources.py",
    "market-data-platform/src/market_data_platform/file_receipts.py",
    "portfolio-backtester/src/portfolio_backtester/evidence_receipts.py",
    "strategy-app/src/strategy_app/file_receipts.py",
    "quant-execution-engine/src/quant_execution_engine/handoff_audit.py",
}
SCAN_ROOTS = (
    ROOT / "src/research_contracts",
    ROOT / "strategy-research/style_factors",
    ROOT / "market-data-platform/src/market_data_platform",
    ROOT / "portfolio-backtester/src/portfolio_backtester",
    ROOT / "strategy-app/src/strategy_app",
    ROOT / "quant-execution-engine/src/quant_execution_engine",
    ROOT / "strategy-pipeline/src/strategy_pipeline",
)


def _hash_definition_paths() -> set[str]:
    definitions: set[str] = set()
    for scan_root in SCAN_ROOTS:
        for path in scan_root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if any(
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in HASH_FUNCTION_NAMES
                for node in tree.body
            ):
                definitions.add(path.relative_to(ROOT).as_posix())
    return definitions


def test_sha256_file_helpers_do_not_proliferate_across_workspace() -> None:
    assert _hash_definition_paths() == ALLOWED_HASH_DEFINITIONS
