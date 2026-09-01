#!/usr/bin/env python3
"""Project workspace architecture into import, call, artifact, and version graphs."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "docs" / "architecture-model.yml"
ARTIFACT_MANIFEST_PATH = ROOT / "docs" / "artifact-contracts.yml"
SCHEMA_VERSION = "workspace_architecture.v1"


@dataclass(frozen=True)
class Component:
    identifier: str
    repo_path: str
    plane: str
    role: str
    package_roots: tuple[str, ...]
    source_roots: tuple[str, ...]
    runtime_cycle_check: bool


@dataclass(frozen=True)
class ArchitectureModel:
    schema_version: str
    components: tuple[Component, ...]
    external_components: tuple[str, ...]

    @property
    def by_id(self) -> dict[str, Component]:
        return {component.identifier: component for component in self.components}

    @property
    def package_owners(self) -> dict[str, str]:
        return {
            package: component.identifier
            for component in self.components
            for package in component.package_roots
        }


def _load_yaml_or_json(path: Path) -> Mapping[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected a mapping")
    return payload


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def load_model(
    root: Path = ROOT,
    *,
    model_path: Path | None = None,
) -> ArchitectureModel:
    path = model_path or root / "docs" / "architecture-model.yml"
    payload = _load_yaml_or_json(path)
    schema_version = str(payload.get("schema_version", ""))
    if schema_version != SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported schema_version {schema_version!r}")

    raw_components = payload.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        raise ValueError(f"{path}: components must be a non-empty list")

    components: list[Component] = []
    seen_ids: set[str] = set()
    seen_packages: dict[str, str] = {}
    for raw in raw_components:
        if not isinstance(raw, Mapping):
            raise ValueError(f"{path}: component entries must be mappings")
        identifier = str(raw.get("id", "")).strip()
        if not identifier:
            raise ValueError(f"{path}: component id is required")
        if identifier in seen_ids:
            raise ValueError(f"{path}: duplicate component id {identifier!r}")
        seen_ids.add(identifier)
        package_roots = _strings(raw.get("package_roots"))
        for package in package_roots:
            previous = seen_packages.get(package)
            if previous:
                raise ValueError(
                    f"{path}: package root {package!r} belongs to both "
                    f"{previous!r} and {identifier!r}"
                )
            seen_packages[package] = identifier
        components.append(
            Component(
                identifier=identifier,
                repo_path=str(raw.get("repo_path", ".")).strip() or ".",
                plane=str(raw.get("plane", "")).strip(),
                role=str(raw.get("role", "")).strip(),
                package_roots=package_roots,
                source_roots=_strings(raw.get("source_roots")),
                runtime_cycle_check=bool(raw.get("runtime_cycle_check", True)),
            )
        )

    return ArchitectureModel(
        schema_version=schema_version,
        components=tuple(components),
        external_components=_strings(payload.get("external_components")),
    )


def _component_root(root: Path, component: Component) -> Path:
    return root if component.repo_path == "." else root / component.repo_path


def _python_sources(
    root: Path,
    model: ArchitectureModel,
) -> Iterable[tuple[Component, Path, Path]]:
    for component in model.components:
        repo_root = _component_root(root, component)
        for source in component.source_roots:
            source_root = repo_root / source
            if source_root.is_file() and source_root.suffix == ".py":
                yield component, source_root, source_root
            elif source_root.is_dir():
                for path in sorted(source_root.rglob("*.py")):
                    if "__pycache__" not in path.parts:
                        yield component, source_root, path


def _missing_source_warnings(root: Path, model: ArchitectureModel) -> list[str]:
    warnings: list[str] = []
    for component in model.components:
        repo_root = _component_root(root, component)
        for source in component.source_roots:
            if not (repo_root / source).exists():
                warnings.append(f"{component.identifier}: missing source root {source}")
    return warnings


def _target_component(module: str, package_owners: Mapping[str, str]) -> str | None:
    package = module.split(".", 1)[0]
    return package_owners.get(package)


def _iter_imports(tree: ast.AST) -> Iterable[tuple[int, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module


def build_import_graph(root: Path, model: ArchitectureModel) -> dict[str, object]:
    package_owners = model.package_owners
    edges: list[dict[str, object]] = []
    errors: list[str] = []
    for component, _source_root, path in _python_sources(root, model):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(
                f"{path.relative_to(root).as_posix()}:{exc.lineno or 0}: syntax error"
            )
            continue
        for line, module in _iter_imports(tree):
            target = _target_component(module, package_owners)
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
    edges.sort(
        key=lambda edge: (
            str(edge["source"]),
            str(edge["target"]),
            str(edge["path"]),
            int(edge["line"]),
            str(edge["module"]),
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "import_graph",
        "nodes": [component.identifier for component in model.components],
        "edges": edges,
        "errors": errors,
        "warnings": _missing_source_warnings(root, model),
    }


def _import_aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound_name = alias.asname or alias.name.split(".", 1)[0]
                bound_target = alias.name if alias.asname else bound_name
                aliases[bound_name] = bound_target
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for alias in node.names:
                if alias.name == "*":
                    continue
                bound_name = alias.asname or alias.name
                aliases[bound_name] = f"{node.module}.{alias.name}"
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


def build_call_graph(root: Path, model: ArchitectureModel) -> dict[str, object]:
    package_owners = model.package_owners
    edges: list[dict[str, object]] = []
    errors: list[str] = []
    for component, _source_root, path in _python_sources(root, model):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(
                f"{path.relative_to(root).as_posix()}:{exc.lineno or 0}: syntax error"
            )
            continue
        aliases = _import_aliases(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            symbol = _called_symbol(node.func, aliases)
            if symbol is None:
                continue
            target = _target_component(symbol, package_owners)
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
    edges.sort(
        key=lambda edge: (
            str(edge["source"]),
            str(edge["target"]),
            str(edge["path"]),
            int(edge["line"]),
            str(edge["target_symbol"]),
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "call_graph",
        "completeness": "conservative-static",
        "nodes": [component.identifier for component in model.components],
        "edges": edges,
        "errors": errors,
        "warnings": _missing_source_warnings(root, model),
    }


def _known_reference(model: ArchitectureModel, identifier: str) -> bool:
    return identifier in model.by_id or identifier in model.external_components


def build_artifact_graph(
    root: Path,
    model: ArchitectureModel,
    *,
    manifest_path: Path | None = None,
) -> dict[str, object]:
    path = manifest_path or root / "docs" / "artifact-contracts.yml"
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "artifact_graph",
            "nodes": [],
            "edges": [],
            "errors": [],
            "warnings": [f"missing artifact manifest: {path}"],
        }
    payload = _load_yaml_or_json(path)
    records = payload.get("artifacts")
    if not isinstance(records, list):
        records = []

    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    errors: list[str] = []
    for raw in records:
        if not isinstance(raw, Mapping):
            continue
        artifact = str(raw.get("artifact", "")).strip()
        if not artifact:
            continue
        artifact_node = f"artifact:{artifact}"
        owner = str(raw.get("owner", "")).strip()
        producer = str(raw.get("producer", "")).strip()
        nodes.append(
            {
                "id": artifact_node,
                "artifact": artifact,
                "owner": owner,
                "contract": str(raw.get("contract", "")).strip(),
                "schema_version": raw.get("schema_version"),
            }
        )
        for identifier, field in ((owner, "owner"), (producer, "producer")):
            if identifier and not _known_reference(model, identifier):
                errors.append(f"{artifact}: unknown {field} component {identifier!r}")
        if producer:
            edges.append(
                {"source": producer, "target": artifact_node, "kind": "produces"}
            )
        external_producers = raw.get("external_producers")
        if isinstance(external_producers, list):
            for item in external_producers:
                identifier = str(item).strip()
                if not identifier:
                    continue
                if not _known_reference(model, identifier):
                    errors.append(
                        f"{artifact}: unknown external producer component {identifier!r}"
                    )
                edges.append(
                    {"source": identifier, "target": artifact_node, "kind": "produces"}
                )
        consumers = raw.get("consumers")
        if isinstance(consumers, list):
            for item in consumers:
                identifier = str(item).strip()
                if not identifier:
                    continue
                if not _known_reference(model, identifier):
                    errors.append(f"{artifact}: unknown consumer component {identifier!r}")
                edges.append(
                    {"source": artifact_node, "target": identifier, "kind": "consumes"}
                )
    nodes.sort(key=lambda node: str(node["id"]))
    edges.sort(key=lambda edge: (str(edge["source"]), str(edge["target"]), str(edge["kind"])))
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "artifact_graph",
        "nodes": nodes,
        "edges": edges,
        "errors": sorted(set(errors)),
        "warnings": [],
    }


def _workspace_gitlinks(root: Path, model: ArchitectureModel) -> tuple[dict[str, str], list[str]]:
    repo_components = {
        component.repo_path: component.identifier
        for component in model.components
        if component.repo_path != "."
    }
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-tree", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return {}, [f"gitlink scan unavailable: {exc}"]
    if result.returncode != 0:
        message = result.stderr.strip() or "git ls-tree failed"
        return {}, [f"gitlink scan unavailable: {message}"]

    revisions: dict[str, str] = {}
    for line in result.stdout.splitlines():
        metadata, separator, path = line.partition("\t")
        if not separator or path not in repo_components:
            continue
        parts = metadata.split()
        if len(parts) != 3 or parts[0] != "160000":
            continue
        revisions[repo_components[path]] = parts[2]
    return revisions, []


def _standalone_pins(root: Path, model: ArchitectureModel) -> tuple[dict[str, dict[str, str]], list[str]]:
    component_ids = set(model.by_id)
    pins: dict[str, dict[str, str]] = {}
    warnings: list[str] = []
    for component in model.components:
        pyproject = _component_root(root, component) / "pyproject.toml"
        if not pyproject.is_file():
            continue
        try:
            payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            warnings.append(f"{component.identifier}: cannot parse pyproject.toml: {exc}")
            continue
        tool = payload.get("tool")
        if not isinstance(tool, Mapping):
            continue
        uv = tool.get("uv")
        if not isinstance(uv, Mapping):
            continue
        sources = uv.get("sources")
        if not isinstance(sources, Mapping):
            continue
        component_pins: dict[str, str] = {}
        for dependency, raw in sources.items():
            dependency_id = str(dependency)
            if dependency_id not in component_ids or not isinstance(raw, Mapping):
                continue
            revision = str(raw.get("rev", "")).strip()
            if revision:
                component_pins[dependency_id] = revision
        if component_pins:
            pins[component.identifier] = component_pins
    return pins, warnings


def compare_version_pins(
    *,
    workspace_revisions: Mapping[str, str],
    local_pins: Mapping[str, Mapping[str, str]],
) -> list[dict[str, str]]:
    differences: list[dict[str, str]] = []
    for consumer in sorted(local_pins):
        for dependency in sorted(local_pins[consumer]):
            standalone_revision = local_pins[consumer][dependency]
            workspace_revision = workspace_revisions.get(dependency)
            if workspace_revision is None or workspace_revision == standalone_revision:
                continue
            differences.append(
                {
                    "consumer": consumer,
                    "dependency": dependency,
                    "workspace_revision": workspace_revision,
                    "standalone_revision": standalone_revision,
                    "severity": "warning",
                }
            )
    return differences


def build_version_graph(root: Path, model: ArchitectureModel) -> dict[str, object]:
    workspace_revisions, git_warnings = _workspace_gitlinks(root, model)
    standalone_pins, pin_warnings = _standalone_pins(root, model)
    differences = compare_version_pins(
        workspace_revisions=workspace_revisions,
        local_pins=standalone_pins,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "version_graph",
        "workspace_revisions": workspace_revisions,
        "standalone_pins": standalone_pins,
        "standalone_pin_differences": differences,
        "errors": [],
        "warnings": [*git_warnings, *pin_warnings],
    }


def _canonical_cycle(cycle: list[str]) -> list[str]:
    core = cycle[:-1]
    rotations = [core[index:] + core[:index] for index in range(len(core))]
    chosen = min(rotations)
    return [*chosen, chosen[0]]


def find_runtime_cycles(
    model: ArchitectureModel,
    edges: object,
) -> list[list[str]]:
    runtime = {
        component.identifier
        for component in model.components
        if component.runtime_cycle_check
    }
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
            cycle = _canonical_cycle([*path[start:], node])
            found.add(tuple(cycle))
            return
        if len(path) >= len(runtime):
            return
        for target in sorted(adjacency.get(node, ())):
            visit(target, [*path, node])

    for identifier in sorted(runtime):
        visit(identifier, [])
    return [list(cycle) for cycle in sorted(found)]


def _boundary_coverage_errors(root: Path, model: ArchitectureModel) -> list[str]:
    path = root / "scripts" / "import_boundary_rules.yml"
    if not path.is_file():
        return []
    payload = _load_yaml_or_json(path)
    known_repo_paths = {component.repo_path for component in model.components}
    errors: list[str] = []
    for section in ("boundary_rules", "source_layout_rules", "private_import_rules"):
        records = payload.get(section)
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, Mapping):
                continue
            repo = str(record.get("repo", ".")).strip() or "."
            if repo not in known_repo_paths:
                identifier = str(record.get("identifier", "<unknown>"))
                errors.append(f"{identifier}: architecture model does not cover repo {repo!r}")
    return errors


def build_report(
    root: Path = ROOT,
    *,
    model_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict[str, object]:
    model = load_model(root, model_path=model_path)
    import_graph = build_import_graph(root, model)
    call_graph = build_call_graph(root, model)
    artifact_graph = build_artifact_graph(root, model, manifest_path=manifest_path)
    version_graph = build_version_graph(root, model)
    cycles = find_runtime_cycles(model, import_graph["edges"])

    errors = [
        *[str(item) for item in import_graph["errors"]],
        *[str(item) for item in call_graph["errors"]],
        *[str(item) for item in artifact_graph["errors"]],
        *_boundary_coverage_errors(root, model),
        *[f"runtime import cycle: {' -> '.join(cycle)}" for cycle in cycles],
    ]
    warnings = sorted(
        set(
            [str(item) for item in import_graph["warnings"]]
            + [str(item) for item in artifact_graph["warnings"]]
            + [str(item) for item in version_graph["warnings"]]
        )
    )
    for difference in version_graph["standalone_pin_differences"]:
        warnings.append(
            "standalone pin differs from workspace gitlink: "
            f"{difference['consumer']} -> {difference['dependency']} "
            f"({difference['standalone_revision']} != {difference['workspace_revision']})"
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "cycles": cycles,
        "graphs": {
            "import_graph": import_graph,
            "call_graph": call_graph,
            "artifact_graph": artifact_graph,
            "version_graph": version_graph,
        },
    }


def render_report(report: Mapping[str, object]) -> str:
    graphs = report.get("graphs")
    graph_map = graphs if isinstance(graphs, Mapping) else {}
    lines = ["# Workspace architecture report", ""]
    errors = report.get("errors") if isinstance(report.get("errors"), list) else []
    warnings = report.get("warnings") if isinstance(report.get("warnings"), list) else []
    lines.extend(
        [
            f"- errors: {len(errors)}",
            f"- warnings: {len(warnings)}",
            "",
            "## Graph sizes",
            "",
        ]
    )
    for name in ("import_graph", "call_graph", "artifact_graph"):
        graph = graph_map.get(name)
        edge_count = len(graph.get("edges", [])) if isinstance(graph, Mapping) else 0
        lines.append(f"- {name}: {edge_count} edges")
    version_graph = graph_map.get("version_graph")
    difference_count = (
        len(version_graph.get("standalone_pin_differences", []))
        if isinstance(version_graph, Mapping)
        else 0
    )
    lines.append(f"- version_graph: {difference_count} standalone pin differences")
    if errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {item}" for item in errors)
    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in warnings)
    lines.extend(
        [
            "",
            "Call graph note: direct imported-symbol calls only; dynamic Python dispatch is omitted.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(report: Mapping[str, object], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    graphs = report.get("graphs")
    if not isinstance(graphs, Mapping):
        raise ValueError("report is missing graphs")
    for name in ("import_graph", "call_graph", "artifact_graph", "version_graph"):
        path = out_dir / f"{name}.json"
        path.write_text(
            json.dumps(graphs[name], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    (out_dir / "report.md").write_text(render_report(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=MODEL_PATH)
    parser.add_argument("--artifact-manifest", type=Path, default=ARTIFACT_MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    try:
        report = build_report(
            ROOT,
            model_path=args.model,
            manifest_path=args.artifact_manifest,
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Architecture scan failed: {exc}")
        return 1
    if args.out_dir:
        write_outputs(report, args.out_dir)
    print(render_report(report), end="")
    errors = report.get("errors")
    return 1 if args.check and isinstance(errors, list) and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
