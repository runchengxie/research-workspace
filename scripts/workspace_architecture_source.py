"""Static Python source projections for workspace architecture."""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from workspace_architecture_model import (
    ArchitectureModel,
    Graph,
    iter_python_sources,
    missing_source_warnings,
    target_component,
)


def _parse_python(path: Path, root: Path) -> tuple[ast.AST | None, str | None]:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path)), None
    except SyntaxError as exc:
        return None, f"{path.relative_to(root).as_posix()}:{exc.lineno or 0}: syntax error"


def _iter_imports(tree: ast.AST) -> Iterable[tuple[int, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module


def build_import_graph(root: Path, model: ArchitectureModel) -> Graph:
    edges: list[dict[str, Any]] = []
    errors: list[str] = []
    for component, path in iter_python_sources(root, model):
        tree, error = _parse_python(path, root)
        if error:
            errors.append(error)
            continue
        assert tree is not None
        for line, module in _iter_imports(tree):
            target = target_component(module, model.package_owners)
            if target is None or target == component.identifier:
                continue
            edges.append(
                {
                    "source": component.identifier,
                    "target": target,
                    "module": module,
                    "path": path.relative_to(root).as_posix(),
                    "line": line,
                }
            )
    edges.sort(key=lambda edge: (edge["source"], edge["target"], edge["path"], edge["line"]))
    return {
        "schema_version": model.schema_version,
        "kind": "import_graph",
        "nodes": [component.identifier for component in model.components],
        "edges": edges,
        "errors": errors,
        "warnings": missing_source_warnings(root, model),
    }


def _import_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".", 1)[0]
                aliases[name] = alias.name if alias.asname else name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for alias in node.names:
                if alias.name != "*":
                    aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return aliases


def _attribute_parts(node: ast.AST) -> tuple[str, ...] | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return tuple(reversed(parts))


def _called_symbol(func: ast.AST, aliases: Mapping[str, str]) -> str | None:
    if isinstance(func, ast.Name):
        return aliases.get(func.id)
    parts = _attribute_parts(func)
    if not parts:
        return None
    base = aliases.get(parts[0])
    if base is None:
        return None
    suffix = ".".join(parts[1:])
    return f"{base}.{suffix}" if suffix else base


def build_call_graph(root: Path, model: ArchitectureModel) -> Graph:
    edges: list[dict[str, Any]] = []
    errors: list[str] = []
    for component, path in iter_python_sources(root, model):
        tree, error = _parse_python(path, root)
        if error:
            errors.append(error)
            continue
        assert tree is not None
        aliases = _import_aliases(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            symbol = _called_symbol(node.func, aliases)
            if symbol is None:
                continue
            target = target_component(symbol, model.package_owners)
            if target is None or target == component.identifier:
                continue
            edges.append(
                {
                    "source": component.identifier,
                    "target": target,
                    "target_symbol": symbol,
                    "path": path.relative_to(root).as_posix(),
                    "line": node.lineno,
                }
            )
    edges.sort(key=lambda edge: (edge["source"], edge["target"], edge["path"], edge["line"]))
    return {
        "schema_version": model.schema_version,
        "kind": "call_graph",
        "completeness": "conservative-static",
        "nodes": [component.identifier for component in model.components],
        "edges": edges,
        "errors": errors,
        "warnings": missing_source_warnings(root, model),
    }


def _canonical_cycle(cycle: list[str]) -> list[str]:
    core = cycle[:-1]
    rotations = [core[index:] + core[:index] for index in range(len(core))]
    chosen = min(rotations)
    return [*chosen, chosen[0]]


def find_runtime_cycles(model: ArchitectureModel, edges: object) -> list[list[str]]:
    runtime = {c.identifier for c in model.components if c.runtime_cycle_check}
    adjacency = {identifier: set() for identifier in runtime}
    if isinstance(edges, list):
        for edge in edges:
            if not isinstance(edge, Mapping):
                continue
            source = str(edge.get("source", ""))
            target = str(edge.get("target", ""))
            if source in runtime and target in runtime:
                adjacency[source].add(target)
    found: set[tuple[str, ...]] = set()

    def visit(node: str, path: list[str]) -> None:
        if node in path:
            start = path.index(node)
            found.add(tuple(_canonical_cycle([*path[start:], node])))
            return
        if len(path) >= len(runtime):
            return
        for target in sorted(adjacency.get(node, ())):
            visit(target, [*path, node])

    for identifier in sorted(runtime):
        visit(identifier, [])
    return [list(cycle) for cycle in sorted(found)]
