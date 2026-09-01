"""Component registry helpers for workspace architecture projections."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

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


def load_mapping(path: Path) -> Mapping[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path}: expected a mapping")
    return cast(Mapping[str, Any], payload)


def strings(value: object) -> tuple[str, ...]:
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
        package_roots=strings(raw.get("package_roots")),
        source_roots=strings(raw.get("source_roots")),
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


def load_model(root: Path, *, model_path: Path | None = None) -> ArchitectureModel:
    path = model_path or root / "docs" / "architecture-model.yml"
    payload = load_mapping(path)
    schema_version = str(payload.get("schema_version", ""))
    if schema_version != SCHEMA_VERSION:
        raise ValueError(f"{path}: unsupported schema_version {schema_version!r}")
    raw_components = payload.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        raise ValueError(f"{path}: components must be a non-empty list")

    components: list[Component] = []
    for raw in raw_components:
        if not isinstance(raw, Mapping):
            raise ValueError(f"{path}: component entries must be mappings")
        components.append(_component_from_mapping(path, cast(Mapping[str, Any], raw)))
    _validate_component_uniqueness(path, components)
    return ArchitectureModel(
        schema_version=schema_version,
        components=tuple(components),
        external_components=strings(payload.get("external_components")),
    )


def component_root(root: Path, component: Component) -> Path:
    return root if component.repo_path == "." else root / component.repo_path


def iter_python_sources(
    root: Path,
    model: ArchitectureModel,
) -> Iterable[tuple[Component, Path]]:
    for component in model.components:
        repo_root = component_root(root, component)
        for source in component.source_roots:
            source_root = repo_root / source
            if source_root.is_file() and source_root.suffix == ".py":
                yield component, source_root
            elif source_root.is_dir():
                for path in sorted(source_root.rglob("*.py")):
                    if "__pycache__" not in path.parts:
                        yield component, path


def missing_source_warnings(root: Path, model: ArchitectureModel) -> list[str]:
    warnings: list[str] = []
    for component in model.components:
        repo_root = component_root(root, component)
        for source in component.source_roots:
            if not (repo_root / source).exists():
                warnings.append(f"{component.identifier}: missing source root {source}")
    return warnings


def target_component(module: str, package_owners: Mapping[str, str]) -> str | None:
    return package_owners.get(module.split(".", 1)[0])
