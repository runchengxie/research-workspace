#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/owner-native-namespace-release.json"


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def gitlink_sha(path: str) -> str:
    """Read the index gitlink so checks cover the exact state about to be committed."""
    output = subprocess.check_output(
        ["git", "ls-files", "--stage", "--", path],
        cwd=ROOT,
        text=True,
    ).strip()
    if not output:
        raise RuntimeError(f"missing gitlink: {path}")
    mode, sha, stage_and_name = output.split(maxsplit=2)
    stage, name = stage_and_name.split("\t", maxsplit=1)
    if mode != "160000" or stage != "0" or name != path:
        raise RuntimeError(f"invalid gitlink entry for {path}: {output}")
    return sha


def check_manifest() -> list[str]:
    manifest = load_manifest()
    errors: list[str] = []
    for repo, package in manifest["packages"].items():
        actual = gitlink_sha(repo)
        if actual != package["commit"]:
            errors.append(f"{repo}: gitlink {actual} != manifest {package['commit']}")
        project_path = ROOT / repo / "pyproject.toml"
        if project_path.is_file():
            project = tomllib.loads(project_path.read_text(encoding="utf-8"))["project"]
            if project["version"] != package["version"]:
                errors.append(
                    f"{repo}: project version {project['version']} != manifest {package['version']}"
                )
    if manifest["compatibility"]["owner"] != "strategy-pipeline":
        errors.append("removed compatibility record must be owned by strategy-pipeline")
    if manifest["compatibility"].get("status") != "removed":
        errors.append("shared namespace compatibility status must be removed")
    return errors


def check_initialized_layout() -> list[str]:
    errors: list[str] = []
    expected = {
        "alpha-research": "alpha_research",
        "portfolio-backtester": "portfolio_backtester",
        "strategy-pipeline": "strategy_pipeline",
    }
    for repo, package in expected.items():
        repo_root = ROOT / repo
        if not (repo_root / "src" / package / "__init__.py").is_file():
            errors.append(f"{repo}: missing canonical package src/{package}")
    for repo in expected:
        removed_tree = ROOT / repo / "src/cstree"
        if any(removed_tree.rglob("*.py")):
            errors.append(f"{repo}: removed shared namespace source must not exist")
    for repo in expected:
        src = ROOT / repo / "src"
        if src.exists():
            for path in src.rglob("*.py"):
                if "pkgutil import extend_path" in path.read_text(encoding="utf-8"):
                    errors.append(f"shared namespace mechanism: {path.relative_to(ROOT)}")
    project = tomllib.loads((ROOT / "strategy-pipeline/pyproject.toml").read_text(encoding="utf-8"))
    scripts = project["project"]["scripts"]
    expected_scripts = {
        "strategy": "strategy_pipeline.cli:main",
        "strategy-pipeline": "strategy_pipeline.cli:main",
    }
    if scripts != expected_scripts:
        errors.append(f"strategy-pipeline: unexpected console scripts {scripts!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()
    errors = check_manifest()
    if not args.manifest_only:
        errors.extend(check_initialized_layout())
    if errors:
        raise SystemExit("\n".join(errors))
    print(json.dumps({"status": "ok", "manifest_only": args.manifest_only}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
