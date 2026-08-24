#!/usr/bin/env python3
"""Ratchet owner boundaries that import-only checks cannot see."""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "scripts" / "ownership_boundary_rules.yml"


@dataclass(frozen=True, slots=True)
class OwnershipRule:
    identifier: str
    description: str
    repo: str
    source: str
    allowed_definitions: tuple[str, ...]
    max_unowned_definitions: int
    target_max_unowned_definitions: int
    target_pr: str | None = None
    required: bool = True


@dataclass(frozen=True, slots=True)
class DefinitionFinding:
    path: str
    line: int
    name: str
    kind: str


@dataclass(frozen=True, slots=True)
class OwnershipResult:
    rule: OwnershipRule
    findings: tuple[DefinitionFinding, ...]
    missing_source: bool = False

    @property
    def count(self) -> int:
        return len(self.findings)

    @property
    def over_budget(self) -> bool:
        return self.count > self.rule.max_unowned_definitions

    @property
    def status(self) -> str:
        if self.missing_source:
            return "missing_source"
        if self.over_budget:
            return "over_budget"
        if self.count < self.rule.max_unowned_definitions:
            return "under_budget"
        return "at_budget"


def load_rules(rules_path: Path = RULES_PATH) -> tuple[OwnershipRule, ...]:
    import yaml

    payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "workspace_ownership_boundaries.v1":
        raise ValueError("unsupported ownership-boundary schema")
    return tuple(
        OwnershipRule(
            identifier=raw["identifier"],
            description=raw["description"],
            repo=raw["repo"],
            source=raw["source"],
            allowed_definitions=tuple(raw["allowed_definitions"]),
            max_unowned_definitions=int(raw["max_unowned_definitions"]),
            target_max_unowned_definitions=int(raw["target_max_unowned_definitions"]),
            target_pr=raw.get("target_pr"),
            required=bool(raw.get("required", True)),
        )
        for raw in payload["ownership_rules"]
    )


def _top_level_definitions(tree: ast.Module) -> list[tuple[int, str, str]]:
    definitions: list[tuple[int, str, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.append((node.lineno, node.name, "function"))
        elif isinstance(node, ast.ClassDef):
            definitions.append((node.lineno, node.name, "class"))
    return definitions


def _scan_rule(root: Path, rule: OwnershipRule) -> OwnershipResult:
    path = root / rule.repo / rule.source
    if not path.is_file():
        return OwnershipResult(rule=rule, findings=(), missing_source=True)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    allowed = set(rule.allowed_definitions)
    findings = tuple(
        DefinitionFinding(
            path=path.relative_to(root).as_posix(),
            line=line,
            name=name,
            kind=kind,
        )
        for line, name, kind in _top_level_definitions(tree)
        if name not in allowed
    )
    return OwnershipResult(rule=rule, findings=findings)


def _result_dict(result: OwnershipResult) -> dict[str, Any]:
    return {
        "id": result.rule.identifier,
        "repo": result.rule.repo,
        "source": result.rule.source,
        "description": result.rule.description,
        "count": result.count,
        "max_unowned_definitions": result.rule.max_unowned_definitions,
        "target_max_unowned_definitions": result.rule.target_max_unowned_definitions,
        "target_pr": result.rule.target_pr,
        "required": result.rule.required,
        "status": result.status,
        "findings": [
            {
                "path": finding.path,
                "line": finding.line,
                "name": finding.name,
                "kind": finding.kind,
            }
            for finding in result.findings
        ],
    }


def build_report(
    root: Path = ROOT,
    rules: tuple[OwnershipRule, ...] | None = None,
) -> dict[str, Any]:
    configured = load_rules() if rules is None else rules
    resolved_root = root.resolve()
    results = tuple(_scan_rule(resolved_root, rule) for rule in configured)
    issues: list[str] = []
    for result in results:
        if result.missing_source and result.rule.required:
            issues.append(
                f"{result.rule.identifier}: missing source "
                f"{result.rule.repo}/{result.rule.source}"
            )
        elif result.over_budget:
            issues.append(
                f"{result.rule.identifier}: {result.count} unowned definitions exceed budget "
                f"{result.rule.max_unowned_definitions}"
            )
    return {
        "schema_version": "workspace_ownership_boundaries.v1",
        "root": str(resolved_root),
        "issues": issues,
        "rules": [_result_dict(result) for result in results],
    }


def render_report(report: dict[str, Any]) -> str:
    lines = ["Workspace ownership-boundary report:"]
    for rule in report["rules"]:
        lines.append(
            f"[{rule['status']}] {rule['id']}: "
            f"{rule['count']}/{rule['max_unowned_definitions']} unowned definitions "
            f"(target {rule['target_max_unowned_definitions']})"
        )
    if report["issues"]:
        lines.append("Issues:")
        lines.extend(f"- {issue}" for issue in report["issues"])
    else:
        lines.append("Workspace ownership budgets hold.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_report(report))
    return 1 if args.check and report["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
