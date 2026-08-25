#!/usr/bin/env python3
"""Check cross-repo import direction budgets for the research workspace."""

from __future__ import annotations

import argparse
import ast
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class BoundaryRule:
    identifier: str
    description: str
    repo: str
    source: str
    forbidden: tuple[str, ...]
    max_allowed: int
    required: bool = True


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
class PrivateImportRule:
    identifier: str
    description: str
    repo: str
    source: str
    external_roots: tuple[str, ...]
    max_allowed: int
    required: bool = True


@dataclass(frozen=True)
class RuleResult:
    rule: BoundaryRule | SourceLayoutRule | PrivateImportRule
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


RULES_PATH = ROOT / "scripts" / "import_boundary_rules.yml"


def load_rules(
    rules_path: Path = RULES_PATH,
) -> tuple[
    tuple[BoundaryRule, ...],
    tuple[SourceLayoutRule, ...],
    tuple[PrivateImportRule, ...],
]:
    """从治理 YAML 加载跨仓库导入方向规则，避免规则硬编码在脚本内。"""
    import yaml

    data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    boundary_rules = tuple(
        BoundaryRule(
            identifier=r["identifier"],
            description=r["description"],
            repo=r["repo"],
            source=r["source"],
            forbidden=tuple(r["forbidden"]),
            max_allowed=int(r["max_allowed"]),
            required=bool(r.get("required", True)),
        )
        for r in data["boundary_rules"]
    )
    source_layout_rules = tuple(
        SourceLayoutRule(
            identifier=r["identifier"],
            description=r["description"],
            repo=r["repo"],
            forbidden_sources=tuple(r["forbidden_sources"]),
            max_allowed=int(r["max_allowed"]),
        )
        for r in data["source_layout_rules"]
    )
    private_import_rules = tuple(
        PrivateImportRule(
            identifier=r["identifier"],
            description=r["description"],
            repo=r["repo"],
            source=r["source"],
            external_roots=tuple(r["external_roots"]),
            max_allowed=int(r["max_allowed"]),
            required=bool(r.get("required", True)),
        )
        for r in data.get("private_import_rules", ())
    )
    return boundary_rules, source_layout_rules, private_import_rules


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
    if source_root.is_file():
        return [source_root] if source_root.suffix == ".py" else []
    return sorted(
        path
        for path in source_root.rglob("*.py")
        if "__pycache__" not in path.parts and path.is_file()
    )


def _scan_rule(root: Path, rule: BoundaryRule) -> RuleResult:
    repo_root = root / rule.repo
    source_root = repo_root / rule.source
    if not source_root.exists() or (not source_root.is_dir() and not source_root.is_file()):
        return RuleResult(rule=rule, findings=(), missing_source=True)

    # Module resolution is anchored at ``repo_root / "src"`` (every rule's
    # ``source`` already carries the ``src/`` prefix), which is what makes
    # ``from ..pipeline.runner import ...`` resolve to the right package. A
    # single-file ``source`` (e.g. ``src/foo/contract.py``) is scanned as a
    # top-level module inside its own directory, so its anchor is the file's
    # parent, not ``src``.
    if source_root.is_file():
        resolve_root = source_root.parent
    else:
        resolve_root = repo_root / "src"

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
        for line, module in _iter_imports(resolve_root, path, tree):
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


def _scan_source_layout_rule(root: Path, rule: SourceLayoutRule) -> RuleResult:
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
    return RuleResult(rule=rule, findings=tuple(findings))


def _private_imports(tree: ast.Module, external_roots: set[str]) -> Iterable[tuple[int, str, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] in external_roots and any(part.startswith("_") for part in parts[1:]):
                    yield node.lineno, alias.name, parts[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            parts = node.module.split(".")
            if parts[0] not in external_roots:
                continue
            private_module = any(part.startswith("_") for part in parts[1:])
            for alias in node.names:
                if private_module or alias.name.startswith("_"):
                    yield node.lineno, f"{node.module}.{alias.name}", parts[0]


def _scan_private_import_rule(root: Path, rule: PrivateImportRule) -> RuleResult:
    source_root = root / rule.repo / rule.source
    if not source_root.exists() or (not source_root.is_dir() and not source_root.is_file()):
        return RuleResult(rule=rule, findings=(), missing_source=True)

    external_roots = set(rule.external_roots)
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
        relative = path.relative_to(root).as_posix()
        findings.extend(
            ImportFinding(path=relative, line=line, module=module, matched=matched)
            for line, module, matched in _private_imports(tree, external_roots)
        )
    return RuleResult(rule=rule, findings=tuple(findings))


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
    rule = cast(BoundaryRule, result.rule)
    return {
        "id": rule.identifier,
        "repo": rule.repo,
        "source": rule.source,
        "description": rule.description,
        "forbidden": list(rule.forbidden),
        "count": result.count,
        "max_allowed": rule.max_allowed,
        "required": rule.required,
        "status": result.status,
        "findings": [_finding_to_dict(finding) for finding in result.findings],
    }


def _source_layout_result_to_dict(result: RuleResult) -> dict[str, Any]:
    rule = cast(SourceLayoutRule, result.rule)
    return {
        "id": rule.identifier,
        "repo": rule.repo,
        "description": rule.description,
        "forbidden_sources": list(rule.forbidden_sources),
        "count": result.count,
        "max_allowed": rule.max_allowed,
        "status": result.status,
        "findings": [_source_layout_finding_to_dict(finding) for finding in result.findings],
    }


def _private_import_result_to_dict(result: RuleResult) -> dict[str, Any]:
    rule = cast(PrivateImportRule, result.rule)
    return {
        "id": rule.identifier,
        "repo": rule.repo,
        "source": rule.source,
        "description": rule.description,
        "external_roots": list(rule.external_roots),
        "count": result.count,
        "max_allowed": rule.max_allowed,
        "required": rule.required,
        "status": result.status,
        "findings": [_finding_to_dict(finding) for finding in result.findings],
    }


def _collect_issues(
    results: tuple[RuleResult, ...],
    source_layout_results: tuple[RuleResult, ...],
    private_import_results: tuple[RuleResult, ...],
) -> list[str]:
    issues: list[str] = []
    for result in results:
        rule = cast(BoundaryRule, result.rule)
        if result.missing_source and rule.required:
            issues.append(f"{rule.identifier}: missing source directory {rule.repo}/{rule.source}")
        elif result.over_budget:
            issues.append(
                f"{rule.identifier}: {result.count} imports exceed budget {rule.max_allowed}"
            )
    for result in source_layout_results:
        if result.over_budget:
            issues.append(
                f"{result.rule.identifier}: {result.count} source files exceed budget "
                f"{result.rule.max_allowed}"
            )
    for result in private_import_results:
        rule = cast(PrivateImportRule, result.rule)
        if result.missing_source and rule.required:
            issues.append(f"{rule.identifier}: missing source directory {rule.repo}/{rule.source}")
        elif result.over_budget:
            issues.append(
                f"{rule.identifier}: {result.count} private imports exceed budget "
                f"{rule.max_allowed}"
            )
    return issues


def build_report(
    root: Path = ROOT,
    rules: tuple[BoundaryRule, ...] | None = None,
    source_layout_rules: tuple[SourceLayoutRule, ...] | None = None,
    private_import_rules: tuple[PrivateImportRule, ...] | None = None,
) -> dict[str, Any]:
    if rules is None and source_layout_rules is None and private_import_rules is None:
        loaded_rules, loaded_layout, loaded_private = load_rules()
        rules = loaded_rules
        source_layout_rules = loaded_layout
        private_import_rules = loaded_private
    else:
        loaded_rules, loaded_layout, _loaded_private = load_rules()
        rules = rules if rules is not None else loaded_rules
        source_layout_rules = (
            source_layout_rules if source_layout_rules is not None else loaded_layout
        )
        private_import_rules = private_import_rules if private_import_rules is not None else ()
    resolved_root = root.resolve()
    results = tuple(_scan_rule(resolved_root, rule) for rule in rules)
    source_layout_results = tuple(
        _scan_source_layout_rule(resolved_root, rule) for rule in source_layout_rules
    )
    private_import_results = tuple(
        _scan_private_import_rule(resolved_root, rule) for rule in private_import_rules
    )
    issues = _collect_issues(results, source_layout_results, private_import_results)
    return {
        "schema_version": "workspace_import_boundaries.v3",
        "root": str(root.resolve()),
        "issues": issues,
        "rules": [_result_to_dict(result) for result in results],
        "source_layout_rules": [
            _source_layout_result_to_dict(result) for result in source_layout_results
        ],
        "private_import_rules": [
            _private_import_result_to_dict(result) for result in private_import_results
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
    for rule in report["private_import_rules"]:
        lines.append(
            f"[{rule['status']}] {rule['id']}: "
            f"{rule['count']}/{rule['max_allowed']} cross-repo private imports"
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
