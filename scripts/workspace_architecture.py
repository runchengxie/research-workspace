#!/usr/bin/env python3
"""Project workspace architecture into import, call, artifact, and version graphs."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from workspace_architecture_artifacts import build_artifact_graph
from workspace_architecture_model import (
    SCHEMA_VERSION,
    ArchitectureModel,
    Graph,
    load_mapping,
    load_model,
)
from workspace_architecture_source import (
    build_call_graph,
    build_import_graph,
    find_runtime_cycles,
)
from workspace_architecture_versions import build_version_graph, compare_version_pins

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "docs" / "architecture-model.yml"
ARTIFACT_MANIFEST_PATH = ROOT / "docs" / "artifact-contracts.yml"


def _boundary_coverage_errors(root: Path, model: ArchitectureModel) -> list[str]:
    path = root / "scripts" / "import_boundary_rules.yml"
    if not path.is_file():
        return []
    payload = load_mapping(path)
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
        *version_graph["errors"],
        *_boundary_coverage_errors(root, model),
        *[f"runtime import cycle: {' -> '.join(cycle)}" for cycle in cycles],
    ]
    warnings = set(import_graph["warnings"])
    warnings.update(artifact_graph["warnings"])
    warnings.update(version_graph["warnings"])
    for difference in version_graph["standalone_pin_differences"]:
        warnings.add(
            "standalone pin differs from workspace revision: "
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
            "Call graph note: direct imported-symbol calls only; "
            "dynamic Python dispatch is omitted.",
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


__all__ = [
    "ArchitectureModel",
    "build_artifact_graph",
    "build_call_graph",
    "build_import_graph",
    "build_report",
    "build_version_graph",
    "compare_version_pins",
    "find_runtime_cycles",
    "load_model",
    "main",
    "render_report",
    "write_outputs",
]


if __name__ == "__main__":
    raise SystemExit(main())
