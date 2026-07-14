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
    output = subprocess.check_output(["git", "ls-tree", "HEAD", path], cwd=ROOT, text=True).strip()
    if not output:
        raise RuntimeError(f"missing gitlink: {path}")
    mode, object_type, sha, name = output.split(maxsplit=3)
    if mode != "160000" or object_type != "commit" or name != path:
        raise RuntimeError(f"invalid gitlink entry for {path}: {output}")
    return sha


def check_manifest() -> list[str]:
    manifest = load_manifest()
    errors: list[str] = []
    for repo, package in manifest["packages"].items():
        actual = gitlink_sha(repo)
        if actual != package["commit"]:
            errors.append(f"{repo}: gitlink {actual} != manifest {package['commit']}")
    if manifest["compatibility"]["owner"] != "strategy-pipeline":
        errors.append("legacy compatibility owner must be strategy-pipeline")
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
    for repo in ("alpha-research", "portfolio-backtester"):
        legacy_tree = ROOT / repo / "src/cstree"
        if any(legacy_tree.rglob("*.py")):
            errors.append(f"{repo}: legacy src/cstree must not exist")
    compat = ROOT / "strategy-pipeline/src/cstree"
    actual = {path.name for path in compat.glob("*.py")} if compat.exists() else set()
    if actual != {"__init__.py", "__main__.py"}:
        errors.append(f"strategy-pipeline: unexpected compatibility files {sorted(actual)}")
    for repo in expected:
        src = ROOT / repo / "src"
        if src.exists():
            for path in src.rglob("*.py"):
                if "pkgutil import extend_path" in path.read_text(encoding="utf-8"):
                    errors.append(f"shared namespace mechanism: {path.relative_to(ROOT)}")
    project = tomllib.loads((ROOT / "strategy-pipeline/pyproject.toml").read_text(encoding="utf-8"))
    scripts = project["project"]["scripts"]
    if scripts.get("strategy") != "strategy_pipeline.cli:main":
        errors.append("strategy-pipeline: canonical strategy CLI missing")
    if scripts.get("cstree") != "strategy_pipeline.legacy_cli:main":
        errors.append("strategy-pipeline: cstree compatibility CLI missing")
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
