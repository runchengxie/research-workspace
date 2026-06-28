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


BOUNDARY_RULES: tuple[BoundaryRule, ...] = (
    BoundaryRule(
        identifier="alpha-research:alpha-to-pipeline",
        description="alpha-research should not grow runtime imports back into strategy pipeline",
        repo="alpha-research",
        source="src/cstree/alpha",
        forbidden=("cstree.pipeline",),
        max_allowed=14,
    ),
    BoundaryRule(
        identifier="alpha-research:alpha-to-backtesting",
        description="alpha-research should not grow runtime imports into portfolio backtesting",
        repo="alpha-research",
        source="src/cstree/alpha",
        forbidden=("cstree.backtesting",),
        max_allowed=6,
    ),
    BoundaryRule(
        identifier="portfolio-backtester:backtesting-to-pipeline",
        description=(
            "portfolio-backtester should not grow runtime imports back into strategy pipeline"
        ),
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
        max_allowed=1,
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
        description=(
            "strategy-pipeline exports execution targets without importing execution internals"
        ),
        repo="cross-sectional-trees",
        source="src/cstree",
        forbidden=("quant_execution_engine",),
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


def evaluate_boundaries(
    root: Path = ROOT,
    rules: tuple[BoundaryRule, ...] = BOUNDARY_RULES,
) -> tuple[RuleResult, ...]:
    resolved_root = root.resolve()
    return tuple(_scan_rule(resolved_root, rule) for rule in rules)


def _finding_to_dict(finding: ImportFinding) -> dict[str, Any]:
    return {
        "path": finding.path,
        "line": finding.line,
        "module": finding.module,
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


def build_report(
    root: Path = ROOT,
    rules: tuple[BoundaryRule, ...] = BOUNDARY_RULES,
) -> dict[str, Any]:
    results = evaluate_boundaries(root, rules)
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
    return {
        "schema_version": "workspace_import_boundaries.v1",
        "root": str(root.resolve()),
        "issues": issues,
        "rules": [_result_to_dict(result) for result in results],
    }


def render_report(report: dict[str, Any]) -> str:
    lines = ["Workspace import boundary report:"]
    for rule in report["rules"]:
        lines.append(
            f"[{rule['status']}] {rule['id']}: "
            f"{rule['count']}/{rule['max_allowed']} forbidden imports"
        )
    if report["issues"]:
        lines.append("Issues:")
        lines.extend(f"- {issue}" for issue in report["issues"])
    else:
        lines.append("Import boundary budgets hold.")
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
