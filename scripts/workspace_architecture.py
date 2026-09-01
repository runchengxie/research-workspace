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
Graph = dict[str, Any]


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


def _component_from_mapping(path: Path, raw: Mapping[str, Any]) -> Component:
    identifier = str(raw.get("id", "")).strip()
    if not identifier:
        raise ValueError(f"{path}: component id is required")
    return Component(
        identifier=identifier,
        repo_path=str(raw.get("repo_path", ".")).strip() or ".",
        plane=str(raw.get("plane", "")).strip(),
        role=str(raw.get("role", "")).strip(),
        package_roots=_strings(raw.get("package_roots")),
        source_roots=_strings(raw.get("source_roots")),
        runtime_cycle_check=bool(raw.get("runtime_cycle_check", True)),
    )


def _validate_component_uniqueness(path: Path, components: list[Component]) -> None:
    seen_ids: set[str] = set()
    seen_packages: dict[str, str] = {}
    for component in components:
        if component.identifier in seen_ids:
            raise ValueError(f"{path}: duplicate component id {component.identifier!r}")
        seen_ids.add(component.identifier)
        for package in component.package_roots:
            previous = seen_packages.get(package)
            if previous:
                raise ValueError(
                    f"{path}: package root {package!r} belongs to both "
                    f"{previous!r} and {component.identifier!r}"
                )
            seen_packages[package] = component.identifier


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
    if not all(isinstance(raw, Mapping) for raw in raw_components):
        raise ValueError(f"{path}: component entries must be mappings")
    components = [_component_from_mapping(path, raw) for raw in raw_components]
    _validate_component_uniqueness(path, components)
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
) -> Iterable[tuple[Component, Path]]:
    for component in model.components:
        repo_root = _component_root(root, component)
        for source in component.source_roots:
            source_root = repo_root / source
            if source_root.is_file() and source_root.suffix == ".py":
                yield component, source_root
            elif source_root.is_dir():
                for path in sorted(source_root.rglob("*.py")):
                    if "__pycache__" not in path.parts:
                        yield component, path


def _missing_source_warnings(root: Path, model: ArchitectureModel) -> list[str]:
    warnings: list[str] = []
    for component in model.components:
        repo_root = _component_root(root, component)
        for source in component.source_roots:
            if not (repo_root / source).exists():
                warnings.append(f"{component.identifier}: missing source root {source}")
    return warnings


def _target_component(module: str, package_owners: Mapping[str, str]) -> str | None:
    return package_owners.get(module.split(".", 1)[0])


def _parse_python(path: Path, root: Path) -> tuple[ast.AST | None, str | None]:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path)), None
    except SyntaxError as exc:
        relative = path.relative_to(root).as_posix()
        return None, f"{relative}:{exc.lineno or 0}: syntax error"


def _iter_imports(tree: ast.AST) -> Iterable[tuple[int, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module


def build_import_graph(root: Path, model: ArchitectureModel) -> Graph:
    package_owners = model.package_owners
    edges: list[dict[str, Any]] = []
    errors: list[str] = []
    for component, path in _python_sources(root, model):
        tree, error = _parse_python(path, root)
        if error:
            errors.append(error)
            continue
        assert tree is not None
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
            edge["source"],
            edge["target"],
            edge["path"],
            edge["line"],
            edge["module"],
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
                aliases[bound_name] = alias.name if alias.asname else bound_name
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
    package_owners = model.package_owners
    edges: list[dict[str, Any]] = []
    errors: list[str] = []
    for component, path in _python_sources(root, model):
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
            edge["source"],
            edge["target"],
            edge["path"],
            edge["line"],
            edge["target_symbol"],
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


def _reference_error(
    model: ArchitectureModel,
    artifact: str,
    identifier: str,
    field: str,
) -> str | None:
    if not identifier or _known_reference(model, identifier):
        return None
    return f"{artifact}: unknown {field} component {identifier!r}"


def _producer_edges(
    model: ArchitectureModel,
    artifact: str,
    artifact_node: str,
    raw: Mapping[str, Any],
) -> tuple[list[dict[str, str]], list[str]]:
    edges: list[dict[str, str]] = []
    errors: list[str] = []
    producer = str(raw.get("producer", "")).strip()
    error = _reference_error(model, artifact, producer, "producer")
    if error:
        errors.append(error)
    if producer:
        edges.append({"source": producer, "target": artifact_node, "kind": "produces"})
    for identifier in _strings(raw.get("external_producers")):
        error = _reference_error(model, artifact, identifier, "external producer")
        if error:
            errors.append(error)
        edges.append({"source": identifier, "target": artifact_node, "kind": "produces"})
    return edges, errors


def _consumer_edges(
    model: ArchitectureModel,
    artifact: str,
    artifact_node: str,
    raw: Mapping[str, Any],
) -> tuple[list[dict[str, str]], list[str]]:
    edges: list[dict[str, str]] = []
    errors: list[str] = []
    for identifier in _strings(raw.get("consumers")):
        error = _reference_error(model, artifact, identifier, "consumer")
        if error:
            errors.append(error)
        edges.append({"source": artifact_node, "target": identifier, "kind": "consumes"})
    return edges, errors


def _artifact_record(
    model: ArchitectureModel,
    raw: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, str]], list[str]]:
    artifact = str(raw.get("artifact", "")).strip()
    if not artifact:
        return None, [], []
    artifact_node = f"artifact:{artifact}"
    owner = str(raw.get("owner", "")).strip()
    errors: list[str] = []
    owner_error = _reference_error(model, artifact, owner, "owner")
    if owner_error:
        errors.append(owner_error)
    producer_edges, producer_errors = _producer_edges(model, artifact, artifact_node, raw)
    consumer_edges, consumer_errors = _consumer_edges(model, artifact, artifact_node, raw)
    node = {
        "id": artifact_node,
        "artifact": artifact,
        "owner": owner,
        "contract": str(raw.get("contract", "")).strip(),
        "schema_version": raw.get("schema_version"),
    }
    return node, [*producer_edges, *consumer_edges], [
        *errors,
        *producer_errors,
        *consumer_errors,
    ]


def build_artifact_graph(
    root: Path,
    model: ArchitectureModel,
    *,
    manifest_path: Path | None = None,
) -> Graph:
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
    raw_records = payload.get("artifacts")
    records = raw_records if isinstance(raw_records, list) else []
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    errors: list[str] = []
    for raw in records:
        if not isinstance(raw, Mapping):
            continue
        node, record_edges, record_errors = _artifact_record(model, raw)
        if node:
            nodes.append(node)
        edges.extend(record_edges)
        errors.extend(record_errors)
    nodes.sort(key=lambda node: node["id"])
    edges.sort(key=lambda edge: (edge["source"], edge["target"], edge["kind"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "artifact_graph",
        "nodes": nodes,
        "edges": edges,
        "errors": sorted(set(errors)),
        "warnings": [],
    }


def _workspace_gitlinks(
    root: Path,
    model: ArchitectureModel,
) -> tuple[dict[str, str], list[str]]:
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
        parts = metadata.split()
        if separator and path in repo_components and len(parts) == 3 and parts[0] == "160000":
            revisions[repo_components[path]] = parts[2]
    return revisions, []


def _load_pyproject(path: Path) -> tuple[Mapping[str, Any] | None, str | None]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8")), None
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, str(exc)


def _uv_source_pins(payload: Mapping[str, Any], component_ids: set[str]) -> dict[str, str]:
    tool = payload.get("tool")
    if not isinstance(tool, Mapping):
        return {}
    uv = tool.get("uv")
    if not isinstance(uv, Mapping):
        return {}
    sources = uv.get("sources")
    if not isinstance(sources, Mapping):
        return {}
    pins: dict[str, str] = {}
    for dependency, raw in sources.items():
        dependency_id = str(dependency)
        if dependency_id not in component_ids or not isinstance(raw, Mapping):
            continue
        revision = str(raw.get("rev", "")).strip()
        if revision:
            pins[dependency_id] = revision
    return pins


def _standalone_pins(
    root: Path,
    model: ArchitectureModel,
) -> tuple[dict[str, dict[str, str]], list[str]]:
    component_ids = set(model.by_id)
    pins: dict[str, dict[str, str]] = {}
    warnings: list[str] = []
    for component in model.components:
        pyproject = _component_root(root, component) / "pyproject.toml"
        if not pyproject.is_file():
            continue
        payload, error = _load_pyproject(pyproject)
        if error:
            warnings.append(f"{component.identifier}: cannot parse pyproject.toml: {error}")
            continue
        assert payload is not None
        component_pins = _uv_source_pins(payload, component_ids)
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


def build_version_graph(root: Path, model: ArchitectureModel) -> Graph:
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


def find_runtime_cycles(model: ArchitectureModel, edges: object) -> list[list[str]]:
    runtime = {
        component.identifier for component in model.components if component.runtime_cycle_check
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
            found.add(tuple(_canonical_cycle([*path[start:], node])))
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
) -> Graph:
    model = load_model(root, model_path=model_path)
    import_graph = build_import_graph(root, model)
    call_graph = build_call_graph(root, model)
    artifact_graph = build_artifact_graph(root, model, manifest_path=manifest_path)
    version_graph = build_version_graph(root, model)
    cycles = find_runtime_cycles(model, import_graph["edges"])
    errors = [
        *import_graph["errors"],
        *call_graph["errors"],
        *artifact_graph["errors"],
        *_boundary_coverage_errors(root, model),
        *[f"runtime import cycle: {' -> '.join(cycle)}" for cycle in cycles],
    ]
    warnings = set(import_graph["warnings"])
    warnings.update(artifact_graph["warnings"])
    warnings.update(version_graph["warnings"])
    for difference in version_graph["standalone_pin_differences"]:
        warnings.add(
            "standalone pin differs from workspace gitlink: "
            f"{difference['consumer']} -> {difference['dependency']} "
            f"({difference['standalone_revision']} != {difference['workspace_revision']})"
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "errors": sorted(set(errors)),
        "warnings": sorted(warnings),
        "cycles": cycles,
        "graphs": {
            "import_graph": import_graph,
            "call_graph": call_graph,
            "artifact_graph": artifact_graph,
            "version_graph": version_graph,
        },
    }


def render_report(report: Mapping[str, Any]) -> str:
    graphs = report.get("graphs", {})
    errors = report.get("errors", [])
    warnings = report.get("warnings", [])
    lines = [
        "# Workspace architecture report",
        "",
        f"- errors: {len(errors)}",
        f"- warnings: {len(warnings)}",
        "",
        "## Graph sizes",
        "",
    ]
    for name in ("import_graph", "call_graph", "artifact_graph"):
        graph = graphs.get(name, {})
        lines.append(f"- {name}: {len(graph.get('edges', []))} edges")
    version_graph = graphs.get("version_graph", {})
    differences = version_graph.get("standalone_pin_differences", [])
    lines.append(f"- version_graph: {len(differences)} standalone pin differences")
    if errors:
        lines.extend(["", "## Errors", "", *[f"- {item}" for item in errors]])
    if warnings:
        lines.extend(["", "## Warnings", "", *[f"- {item}" for item in warnings]])
    lines.extend(
        [
            "",
            "Call graph note: direct imported-symbol calls only; dynamic Python dispatch is omitted.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(report: Mapping[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    graphs = report["graphs"]
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
    return 1 if args.check and report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
