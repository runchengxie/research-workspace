#!/usr/bin/env python3
"""Validate the cross-repository research capability registry."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_VERSION = "research_capability_registry.v1"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
OWNER_REPOSITORIES = {
    "research-workspace",
    "market-data-platform",
    "deep-learning-tick-data-prediction",
    "alpha-research",
    "portfolio-backtester",
    "strategy-research",
    "strategy-app",
    "strategy-pipeline",
    "quant-execution-engine",
}
STAGES = {
    "data",
    "feature",
    "labeling",
    "modeling",
    "validation",
    "portfolio",
    "orchestration",
    "execution",
    "governance",
}
KINDS = {"computation", "validation", "contract", "orchestration", "monitoring"}
MATURITIES = {"experimental", "runnable", "verified", "deprecated"}
REQUIRED = {
    "capability_id",
    "summary",
    "owner_repository",
    "stage",
    "kind",
    "maturity",
    "canonical_entrypoint",
    "inputs",
    "outputs",
    "requires",
    "method_refs",
    "evidence_refs",
}


@dataclass(frozen=True)
class RegistryCheck:
    path: str
    issues: list[str] = field(default_factory=list)
    capability_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.issues


def load_registry(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("registry must be a YAML object")
    return payload


def _owner_root(root: Path, owner: str) -> Path:
    if owner == "research-workspace":
        return root
    return root / owner


def _resolve_owner_path(
    root: Path,
    owner: str,
    relative_path: str,
) -> tuple[Path | None, str | None]:
    if not isinstance(relative_path, str) or not relative_path.strip():
        return None, "path must be a non-empty string"
    base = _owner_root(root, owner).resolve()
    resolved = (base / relative_path).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        return None, f"path escapes owner repository: {relative_path}"
    return resolved, None


def _is_private(entrypoint: Mapping[str, Any]) -> bool:
    source = entrypoint.get("source_path")
    if isinstance(source, str):
        for part in Path(source).parts:
            if part.startswith("_") and part != "__init__.py":
                return True
    value = entrypoint.get("value")
    if isinstance(value, str):
        for part in value.split("."):
            if part.startswith("_") and part != "__init__":
                return True
    return False


def _list_of_text(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def _shape_issues(entry: dict[str, Any], prefix: str) -> list[str]:
    issues: list[str] = []
    missing = sorted(REQUIRED - entry.keys())
    if missing:
        issues.append(f"{prefix}: missing fields: {','.join(missing)}")
    capability_id = entry.get("capability_id")
    if not isinstance(capability_id, str) or ID_RE.fullmatch(capability_id) is None:
        issues.append(f"{prefix}: capability_id is invalid")
    summary = entry.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        issues.append(f"{prefix}: summary must be non-empty")
    if entry.get("owner_repository") not in OWNER_REPOSITORIES:
        issues.append(f"{prefix}: owner_repository is invalid")
    if entry.get("stage") not in STAGES:
        issues.append(f"{prefix}: stage is invalid")
    if entry.get("kind") not in KINDS:
        issues.append(f"{prefix}: kind is invalid")
    if entry.get("maturity") not in MATURITIES:
        issues.append(f"{prefix}: maturity is invalid")
    for key in ("inputs", "outputs", "requires", "evidence_refs"):
        if not _list_of_text(entry.get(key)):
            issues.append(f"{prefix}: {key} must be a string list")
    if not isinstance(entry.get("method_refs"), list):
        issues.append(f"{prefix}: method_refs must be a list")
    return issues


def _entrypoint_issues(
    entry: dict[str, Any],
    prefix: str,
    root: Path,
) -> list[str]:
    entrypoint = entry.get("canonical_entrypoint")
    if not isinstance(entrypoint, dict):
        return [f"{prefix}: canonical_entrypoint must be an object"]
    issues: list[str] = []
    if _is_private(entrypoint):
        issues.append(f"{prefix}: canonical entrypoint cannot be private")
    owner = entry.get("owner_repository")
    maturity = entry.get("maturity")
    source = entrypoint.get("source_path")
    if owner not in OWNER_REPOSITORIES:
        return issues
    if not isinstance(source, str):
        if maturity in {"runnable", "verified"}:
            issues.append(f"{prefix}: runnable capability requires source_path")
        return issues
    resolved, error = _resolve_owner_path(root, owner, source)
    if error:
        issues.append(f"{prefix}: source_path {error}")
        return issues
    if maturity in {"runnable", "verified"} and resolved is not None:
        if not resolved.is_file():
            issues.append(f"{prefix}: source_path does not exist: {source}")
    return issues


def _evidence_issues(
    entry: dict[str, Any],
    prefix: str,
    root: Path,
) -> list[str]:
    owner = entry.get("owner_repository")
    evidence = entry.get("evidence_refs")
    maturity = entry.get("maturity")
    if owner not in OWNER_REPOSITORIES or not isinstance(evidence, list):
        return []
    issues: list[str] = []
    test_evidence = False
    for ref in evidence:
        if not isinstance(ref, str):
            continue
        resolved, error = _resolve_owner_path(root, owner, ref)
        if error:
            issues.append(f"{prefix}: evidence_ref {error}")
            continue
        exists = resolved is not None and resolved.is_file()
        if not exists:
            issues.append(f"{prefix}: evidence_ref does not exist: {ref}")
        if (ref.startswith("tests/") or "/tests/" in f"/{ref}") and exists:
            test_evidence = True
    if maturity in {"runnable", "verified"} and not evidence:
        issues.append(f"{prefix}: {maturity} capability requires evidence")
    if maturity == "verified" and not test_evidence:
        issues.append(f"{prefix}: verified capability requires existing test evidence")
    return issues


def _deprecation_issues(entry: dict[str, Any], prefix: str) -> list[str]:
    if entry.get("maturity") != "deprecated":
        return []
    if entry.get("replacement") or entry.get("deprecation_reason"):
        return []
    return [f"{prefix}: deprecated capability requires replacement or deprecation_reason"]


def _entry_issues(entry: Any, index: int, root: Path) -> list[str]:
    prefix = f"capabilities[{index}]"
    if not isinstance(entry, dict):
        return [f"{prefix} must be an object"]
    issues = _shape_issues(entry, prefix)
    issues.extend(_entrypoint_issues(entry, prefix, root))
    issues.extend(_evidence_issues(entry, prefix, root))
    issues.extend(_deprecation_issues(entry, prefix))
    return issues


def _unknown_dependency_issues(entries: list[dict[str, Any]]) -> list[str]:
    known = {
        entry["capability_id"]
        for entry in entries
        if isinstance(entry.get("capability_id"), str)
    }
    issues: list[str] = []
    for entry in entries:
        capability_id = entry.get("capability_id")
        requires = entry.get("requires")
        if not isinstance(requires, list):
            continue
        for dependency in requires:
            if dependency not in known:
                issues.append(
                    f"{capability_id}: requires unknown capability {dependency}"
                )
    return issues


def _dependency_cycle_issues(entries: list[dict[str, Any]]) -> list[str]:
    graph = {
        entry["capability_id"]: list(entry.get("requires", []))
        for entry in entries
        if isinstance(entry.get("capability_id"), str)
        and isinstance(entry.get("requires"), list)
    }
    issues: list[str] = []
    state: dict[str, int] = {}

    def visit(node: str, stack: list[str]) -> None:
        if state.get(node) == 1:
            issues.append("dependency cycle: " + " -> ".join(stack + [node]))
            return
        if state.get(node) == 2:
            return
        state[node] = 1
        for dependency in graph.get(node, []):
            if dependency in graph:
                visit(dependency, stack + [node])
        state[node] = 2

    for node in graph:
        visit(node, [])
    return issues


def _dependency_issues(entries: list[dict[str, Any]]) -> list[str]:
    issues = _unknown_dependency_issues(entries)
    issues.extend(_dependency_cycle_issues(entries))
    return issues


def validate_registry(path: Path, *, root: Path) -> RegistryCheck:
    try:
        payload = load_registry(path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return RegistryCheck(str(path), [str(exc)])
    issues: list[str] = []
    if payload.get("schema_version") != REGISTRY_VERSION:
        issues.append(f"schema_version must be {REGISTRY_VERSION}")
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list):
        return RegistryCheck(str(path), issues + ["capabilities must be a list"])
    for index, entry in enumerate(capabilities):
        issues.extend(_entry_issues(entry, index, root.resolve()))
    entries = [entry for entry in capabilities if isinstance(entry, dict)]
    seen: set[str] = set()
    for entry in entries:
        capability_id = entry.get("capability_id")
        if not isinstance(capability_id, str):
            continue
        if capability_id in seen:
            issues.append(f"duplicate capability_id: {capability_id}")
        seen.add(capability_id)
    issues.extend(_dependency_issues(entries))
    return RegistryCheck(str(path), issues, len(capabilities))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / "docs/research-capabilities.yml",
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    result = validate_registry(args.registry.resolve(), root=args.root.resolve())
    payload = {
        "schema_version": "research_capability_registry_check.v1",
        "ok": result.ok,
        "issues": result.issues,
        "capability_count": result.capability_count,
    }
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        state = "OK" if result.ok else "ERROR"
        print(f"[{state}] {result.path} capabilities={result.capability_count}")
        for issue in result.issues:
            print(f"  - {issue}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
