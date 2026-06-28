#!/usr/bin/env python3
"""Check cross-repo import direction budgets for the research workspace."""

from __future__ import annotations

import argparse
import ast
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class BoundaryRule:
    identifier: str
    description: str
    repo: str
    source: str
    forbidden: tuple[str, ...]
    max_allowed: int


@dataclass(frozen=True)
class ImportFinding:
    path: str
    line: int
    module: str
    matched: str


@dataclass(frozen=True)
class SourceLayoutRule:
    identifier: str
    description: str
    repo: str
    forbidden_sources: tuple[str, ...]
    max_allowed: int


@dataclass(frozen=True)
class RuleResult:
    rule: BoundaryRule
    findings: tuple[ImportFinding, ...]
    missing_source: bool = False

    @property
    def count(self) -> int:
        return len(self.findings)

    @property
    def over_budget(self) -> bool:
        return self.count > self.rule.max_allowed

    @property
    def status(self) -> str:
        if self.missing_source:
            return "missing_source"
        if self.over_budget:
            return "over_budget"
        if self.count < self.rule.max_allowed:
            return "under_budget"
        return "at_budget"


@dataclass(frozen=True)
class SourceLayoutResult:
    rule: SourceLayoutRule
    findings: tuple[ImportFinding, ...]

    @property
    def count(self) -> int:
        return len(self.findings)

    @property
    def over_budget(self) -> bool:
        return self.count > self.rule.max_allowed

    @property
    def status(self) -> str:
        if self.over_budget:
            return "over_budget"
        if self.count < self.rule.max_allowed:
            return "under_budget"
        return "at_budget"


BOUNDARY_RULES: tuple[BoundaryRule, ...] = (
    BoundaryRule(
        identifier="alpha-research:alpha-to-pipeline",
        description="alpha-research should not grow runtime imports back into strategy pipeline",
        repo="alpha-research",
        source="src/cstree/alpha",
        forbidden=("cstree.pipeline",),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="alpha-research:alpha-to-backtesting",
        description="alpha-research should not grow runtime imports into portfolio backtesting",
        repo="alpha-research",
        source="src/cstree/alpha",
        forbidden=("cstree.backtesting",),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="alpha-research:alpha-to-strategy-core-metrics",
        description="alpha-research should own research metrics",
        repo="alpha-research",
        source="src/cstree/alpha",
        forbidden=("cstree.metrics", "cstree.return_metrics"),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="alpha-research:alpha-to-strategy-compat",
        description="alpha-research should own runtime compatibility shims",
        repo="alpha-research",
        source="src/cstree/alpha",
        forbidden=("cstree.compat",),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="alpha-research:alpha-to-strategy-rebalance",
        description=(
            "alpha-research should own research rebalance sampling instead of importing "
            "strategy-pipeline contract implementation helpers"
        ),
        repo="alpha-research",
        source="src/cstree/alpha",
        forbidden=("cstree.contracts.rebalance",),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="alpha-research:alpha-to-strategy-signal-contract",
        description=(
            "alpha-research should own canonical signal artifacts instead of importing "
            "strategy-pipeline contract modules"
        ),
        repo="alpha-research",
        source="src/cstree/alpha",
        forbidden=("cstree.contracts.signals",),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="portfolio-backtester:backtesting-to-pipeline",
        description="portfolio-backtester should not import strategy pipeline runtime",
        repo="portfolio-backtester",
        source="src/cstree/backtesting",
        forbidden=("cstree.pipeline", "cstree.benchmarking"),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="portfolio-backtester:backtesting-to-alpha",
        description=(
            "portfolio-backtester should not grow runtime imports into alpha implementation"
        ),
        repo="portfolio-backtester",
        source="src/cstree/backtesting",
        forbidden=("cstree.alpha",),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="portfolio-backtester:backtesting-to-strategy-core-metrics",
        description=(
            "portfolio-backtester should own backtest metrics instead of importing "
            "strategy-pipeline top-level metric modules"
        ),
        repo="portfolio-backtester",
        source="src/cstree/backtesting",
        forbidden=("cstree.metrics", "cstree.return_metrics"),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="portfolio-backtester:backtesting-to-strategy-rebalance",
        description=(
            "portfolio-backtester should own backtest rebalance sampling instead of importing "
            "strategy-pipeline contract implementation helpers"
        ),
        repo="portfolio-backtester",
        source="src/cstree/backtesting",
        forbidden=("cstree.contracts.rebalance",),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="portfolio-backtester:backtesting-to-strategy-liquidity-proxy",
        description=(
            "portfolio-backtester should own capacity liquidity proxy derivation instead of "
            "importing strategy-pipeline top-level helpers"
        ),
        repo="portfolio-backtester",
        source="src/cstree/backtesting",
        forbidden=("cstree.liquidity_proxy",),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="portfolio-backtester:backtesting-to-strategy-contracts",
        description=(
            "portfolio-backtester should own backtest pricing and strategy specs instead of "
            "importing strategy-pipeline contract modules"
        ),
        repo="portfolio-backtester",
        source="src/cstree/backtesting",
        forbidden=("cstree.contracts.backtest", "cstree.contracts.strategy"),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="market-data-platform:no-cstree-imports",
        description="market-data-platform must stay independent from research strategy internals",
        repo="market-data-platform",
        source="src",
        forbidden=("cstree",),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="quant-execution-engine:no-cstree-imports",
        description="quant-execution-engine consumes targets.json, not research/backtest internals",
        repo="quant-execution-engine",
        source="src",
        forbidden=("cstree",),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="strategy-pipeline:no-execution-engine-imports",
        description="strategy-pipeline exports execution targets without execution internals",
        repo="strategy-pipeline",
        source="src/cstree",
        forbidden=("quant_execution_engine",),
        max_allowed=0,
    ),
    BoundaryRule(
        identifier="strategy-pipeline:contracts-pure-handoff",
        description="strategy-pipeline contract compatibility modules stay pure before extraction",
        repo="strategy-pipeline",
        source="src/cstree/contracts",
        forbidden=(
            "cstree.alpha",
            "cstree.backtesting",
            "cstree.pipeline",
            "quant_execution_engine",
        ),
        max_allowed=0,
    ),
)

SOURCE_LAYOUT_RULES: tuple[SourceLayoutRule, ...] = (
    SourceLayoutRule(
        identifier="strategy-pipeline:no-local-alpha-backtesting-source",
        description=(
            "strategy-pipeline should orchestrate alpha research and portfolio backtesting "
            "instead of carrying local alpha/backtesting implementation modules"
        ),
        repo="strategy-pipeline",
        forbidden_sources=("src/cstree/alpha", "src/cstree/backtesting"),
        max_allowed=0,
    ),
)


def _module_for_path(src_root: Path, path: Path) -> str:
    relative = path.relative_to(src_root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _package_for_import_from(src_root: Path, path: Path) -> list[str]:
    module = _module_for_path(src_root, path)
    parts = module.split(".") if module else []
    if path.name == "__init__.py":
        return parts
    return parts[:-1]


def _resolve_import_from(src_root: Path, path: Path, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module

    package = _package_for_import_from(src_root, path)
    keep = len(package) - node.level + 1
    if keep < 0:
        return None
    base = ".".join(package[:keep])
    if node.module:
        return f"{base}.{node.module}" if base else node.module
    return base or None


def _iter_imports(src_root: Path, path: Path, tree: ast.AST) -> Iterable[tuple[int, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_import_from(src_root, path, node)
            if module:
                yield node.lineno, module


def _matches(module: str, forbidden: str) -> bool:
    return module == forbidden or module.startswith(f"{forbidden}.")


def _python_files(source_root: Path) -> list[Path]:
    return sorted(
        path
        for path in source_root.rglob("*.py")
        if "__pycache__" not in path.parts and path.is_file()
    )


def _scan_rule(root: Path, rule: BoundaryRule) -> RuleResult:
    repo_root = root / rule.repo
    src_root = repo_root / "src"
    source_root = repo_root / rule.source
    if not source_root.is_dir():
        return RuleResult(rule=rule, findings=(), missing_source=True)

    findings: list[ImportFinding] = []
    for path in _python_files(source_root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            findings.append(
                ImportFinding(
                    path=path.relative_to(root).as_posix(),
                    line=exc.lineno or 0,
                    module="<syntax-error>",
                    matched="<syntax-error>",
                )
            )
            continue
        for line, module in _iter_imports(src_root, path, tree):
            for forbidden in rule.forbidden:
                if _matches(module, forbidden):
                    findings.append(
                        ImportFinding(
                            path=path.relative_to(root).as_posix(),
                            line=line,
                            module=module,
                            matched=forbidden,
                        )
                    )
                    break
    return RuleResult(rule=rule, findings=tuple(findings))


def _scan_source_layout_rule(root: Path, rule: SourceLayoutRule) -> SourceLayoutResult:
    repo_root = root / rule.repo
    findings: list[ImportFinding] = []
    for source in rule.forbidden_sources:
        source_root = repo_root / source
        if not source_root.exists():
            continue
        if source_root.is_file():
            if source_root.suffix == ".py":
                findings.append(
                    ImportFinding(
                        path=source_root.relative_to(root).as_posix(),
                        line=0,
                        module="<source-file>",
                        matched=source,
                    )
                )
            continue
        for path in _python_files(source_root):
            findings.append(
                ImportFinding(
                    path=path.relative_to(root).as_posix(),
                    line=0,
                    module="<source-file>",
                    matched=source,
                )
            )
    return SourceLayoutResult(rule=rule, findings=tuple(findings))


def _finding_to_dict(finding: ImportFinding) -> dict[str, Any]:
    return {
        "path": finding.path,
        "line": finding.line,
        "module": finding.module,
        "matched": finding.matched,
    }


def _source_layout_finding_to_dict(finding: ImportFinding) -> dict[str, Any]:
    return {
        "path": finding.path,
        "matched": finding.matched,
    }


def _result_to_dict(result: RuleResult) -> dict[str, Any]:
    return {
        "id": result.rule.identifier,
        "repo": result.rule.repo,
        "source": result.rule.source,
        "description": result.rule.description,
        "forbidden": list(result.rule.forbidden),
        "count": result.count,
        "max_allowed": result.rule.max_allowed,
        "status": result.status,
        "findings": [_finding_to_dict(finding) for finding in result.findings],
    }


def _source_layout_result_to_dict(result: SourceLayoutResult) -> dict[str, Any]:
    return {
        "id": result.rule.identifier,
        "repo": result.rule.repo,
        "description": result.rule.description,
        "forbidden_sources": list(result.rule.forbidden_sources),
        "count": result.count,
        "max_allowed": result.rule.max_allowed,
        "status": result.status,
        "findings": [_source_layout_finding_to_dict(finding) for finding in result.findings],
    }


def build_report(
    root: Path = ROOT,
    rules: tuple[BoundaryRule, ...] = BOUNDARY_RULES,
    source_layout_rules: tuple[SourceLayoutRule, ...] = SOURCE_LAYOUT_RULES,
) -> dict[str, Any]:
    resolved_root = root.resolve()
    results = tuple(_scan_rule(resolved_root, rule) for rule in rules)
    source_layout_results = tuple(
        _scan_source_layout_rule(resolved_root, rule) for rule in source_layout_rules
    )
    issues: list[str] = []
    for result in results:
        if result.missing_source:
            issues.append(
                f"{result.rule.identifier}: missing source directory "
                f"{result.rule.repo}/{result.rule.source}"
            )
        elif result.over_budget:
            issues.append(
                f"{result.rule.identifier}: {result.count} imports exceed budget "
                f"{result.rule.max_allowed}"
            )
    for result in source_layout_results:
        if result.over_budget:
            issues.append(
                f"{result.rule.identifier}: {result.count} source files exceed budget "
                f"{result.rule.max_allowed}"
            )
    return {
        "schema_version": "workspace_import_boundaries.v2",
        "root": str(root.resolve()),
        "issues": issues,
        "rules": [_result_to_dict(result) for result in results],
        "source_layout_rules": [
            _source_layout_result_to_dict(result) for result in source_layout_results
        ],
    }


def render_report(report: dict[str, Any]) -> str:
    lines = ["Workspace boundary report:"]
    for rule in report["rules"]:
        lines.append(
            f"[{rule['status']}] {rule['id']}: "
            f"{rule['count']}/{rule['max_allowed']} forbidden imports"
        )
    for rule in report["source_layout_rules"]:
        lines.append(
            f"[{rule['status']}] {rule['id']}: "
            f"{rule['count']}/{rule['max_allowed']} forbidden source files"
        )
    if report["issues"]:
        lines.append("Issues:")
        lines.extend(f"- {issue}" for issue in report["issues"])
    else:
        lines.append("Workspace boundary budgets hold.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true", help="Print machine-readable report.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero on budget drift.")
    args = parser.parse_args(argv)

    report = build_report(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_report(report))
    return 1 if args.check and report["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
