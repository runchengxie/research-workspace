"""Workspace gitlink and standalone package-pin projections."""

from __future__ import annotations

import subprocess
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from workspace_architecture_model import ArchitectureModel, Graph, component_root


def _run_git(root: Path, *args: str) -> tuple[str | None, str | None]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return None, str(exc)
    if result.returncode != 0:
        return None, result.stderr.strip() or f"git {' '.join(args)} failed"
    return result.stdout, None


def _workspace_gitlinks(
    root: Path,
    model: ArchitectureModel,
) -> tuple[dict[str, str], list[str]]:
    repo_components = {
        component.repo_path: component.identifier
        for component in model.components
        if component.repo_path != "."
    }
    output, error = _run_git(root, "ls-tree", "HEAD")
    if error:
        return {}, [f"gitlink scan unavailable: {error}"]
    assert output is not None
    revisions: dict[str, str] = {}
    for line in output.splitlines():
        metadata, separator, path = line.partition("\t")
        parts = metadata.split()
        if separator and path in repo_components and len(parts) == 3 and parts[0] == "160000":
            revisions[repo_components[path]] = parts[2]
    return revisions, []


def _workspace_revisions(
    root: Path,
    model: ArchitectureModel,
) -> tuple[dict[str, str], list[str]]:
    revisions, warnings = _workspace_gitlinks(root, model)
    output, error = _run_git(root, "rev-parse", "HEAD")
    if error:
        warnings.append(f"root revision scan unavailable: {error}")
        return revisions, warnings
    assert output is not None
    root_revision = output.strip()
    for component in model.components:
        if component.repo_path == ".":
            revisions[component.identifier] = root_revision
    return revisions, warnings


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
    errors: list[str] = []
    for component in model.components:
        pyproject = component_root(root, component) / "pyproject.toml"
        if not pyproject.is_file():
            continue
        payload, error = _load_pyproject(pyproject)
        if error:
            errors.append(f"{component.identifier}: cannot parse pyproject.toml: {error}")
            continue
        assert payload is not None
        component_pins = _uv_source_pins(payload, component_ids)
        if component_pins:
            pins[component.identifier] = component_pins
    return pins, errors


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
    workspace_revisions, git_warnings = _workspace_revisions(root, model)
    standalone_pins, pin_errors = _standalone_pins(root, model)
    differences = compare_version_pins(
        workspace_revisions=workspace_revisions,
        local_pins=standalone_pins,
    )
    return {
        "schema_version": model.schema_version,
        "kind": "version_graph",
        "workspace_revisions": workspace_revisions,
        "standalone_pins": standalone_pins,
        "standalone_pin_differences": differences,
        "errors": pin_errors,
        "warnings": git_warnings,
    }
