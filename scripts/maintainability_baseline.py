#!/usr/bin/env python3
"""Build cross-repo maintainability baseline reports with stdlib-only parsing."""

from __future__ import annotations

import argparse
import ast
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPOS = [
    "research-workspace",
    "market-data-platform",
    "cross-sectional-trees",
    "quant-execution-engine",
]
DEFAULT_THRESHOLDS = {
    "large_file_loc": 500,
    "long_function_lines": 80,
    "complexity": 15,
}
SUBMODULE_DIRS = {
    "cross-sectional-trees",
    "market-data-platform",
    "quant-execution-engine",
}
EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "build",
    "dist",
    "outputs",
}
HK_MARKERS = (
    "alloc-hk",
    "alloc_hk",
    "hk",
    "hk_",
    "hk-",
    "hkdata",
    "longport",
    "rqdata-hk",
)
SCRIPT_DIRS = ("scripts", "project_tools")


@dataclass(frozen=True)
class FunctionMetric:
    path: str
    name: str
    line_count: int
    complexity: int


def _repo_root(name: str) -> Path:
    return ROOT if name == "research-workspace" else ROOT / name


def _skip_path(path: Path, *, repo_name: str) -> bool:
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return True
    return repo_name == "research-workspace" and any(part in SUBMODULE_DIRS for part in path.parts)


def _python_files(repo: Path, *, repo_name: str) -> list[Path]:
    return sorted(
        path
        for path in repo.rglob("*.py")
        if path.is_file() and not _skip_path(path, repo_name=repo_name)
    )


def _count_complexity(node: ast.AST) -> int:
    branches = (
        ast.BoolOp,
        ast.ExceptHandler,
        ast.For,
        ast.If,
        ast.IfExp,
        ast.Match,
        ast.Try,
        ast.While,
        ast.With,
        ast.comprehension,
    )
    return 1 + sum(isinstance(child, branches) for child in ast.walk(node))


def _function_metrics(path: Path, relative: str) -> list[FunctionMetric]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
    except (SyntaxError, UnicodeDecodeError):
        return []
    metrics = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end_lineno = getattr(node, "end_lineno", node.lineno)
        metrics.append(
            FunctionMetric(
                path=relative,
                name=node.name,
                line_count=end_lineno - node.lineno + 1,
                complexity=_count_complexity(node),
            )
        )
    return metrics


def _is_hk_related(relative: str) -> bool:
    lowered = relative.lower()
    return any(marker in lowered for marker in HK_MARKERS)


def _load_pyproject(repo: Path) -> dict[str, Any]:
    path = repo / "pyproject.toml"
    if not path.is_file():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _quality_config(repo: Path) -> dict[str, Any]:
    config = _load_pyproject(repo)
    tool = config.get("tool", {})
    ruff = tool.get("ruff", {})
    ruff_lint = ruff.get("lint", {})
    pyright = tool.get("pyright", {})
    mypy = tool.get("mypy", {})
    return {
        "ruff_select": ruff_lint.get("select", []),
        "ruff_extend_exclude": ruff.get("extend-exclude", []),
        "pyright_include": pyright.get("include", []),
        "pyright_exclude": pyright.get("exclude", []),
        "pyright_type_checking_mode": pyright.get("typeCheckingMode"),
        "mypy_present": bool(mypy),
    }


def _script_inventory(repo: Path) -> list[str]:
    scripts = []
    for dirname in SCRIPT_DIRS:
        root = repo / dirname
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and not _skip_path(path, repo_name=repo.name):
                scripts.append(path.relative_to(repo).as_posix())
    return sorted(scripts)


def build_repo_report(name: str, *, thresholds: dict[str, int]) -> dict[str, Any]:
    repo = _repo_root(name)
    files = _python_files(repo, repo_name=name)
    file_rows = []
    function_rows: list[FunctionMetric] = []
    for path in files:
        relative = path.relative_to(repo).as_posix()
        try:
            loc = len(path.read_text(encoding="utf-8").splitlines())
        except UnicodeDecodeError:
            loc = 0
        file_rows.append({"path": relative, "loc": loc, "hk_related": _is_hk_related(relative)})
        function_rows.extend(_function_metrics(path, relative))

    large_files = [row for row in file_rows if int(row["loc"]) >= thresholds["large_file_loc"]]
    long_functions = [
        row for row in function_rows if row.line_count >= thresholds["long_function_lines"]
    ]
    complex_functions = [row for row in function_rows if row.complexity >= thresholds["complexity"]]
    return {
        "repo": name,
        "root": repo.relative_to(ROOT).as_posix() if repo != ROOT else ".",
        "python_file_count": len(files),
        "python_loc": sum(int(row["loc"]) for row in file_rows),
        "hk_related_file_count": sum(1 for row in file_rows if row["hk_related"]),
        "large_files": sorted(
            large_files,
            key=lambda row: (-int(row["loc"]), str(row["path"])),
        )[:25],
        "long_functions": [
            row.__dict__
            for row in sorted(
                long_functions,
                key=lambda item: (-item.line_count, item.path, item.name),
            )[:25]
        ],
        "complexity_hotspots": [
            row.__dict__
            for row in sorted(
                complex_functions,
                key=lambda item: (-item.complexity, item.path, item.name),
            )[:25]
        ],
        "quality_config": _quality_config(repo),
        "script_inventory": _script_inventory(repo),
    }


def build_baseline(repos: list[str], *, thresholds: dict[str, int]) -> dict[str, Any]:
    return {
        "schema_version": "maintainability_baseline.v1",
        "thresholds": thresholds,
        "repos": [build_repo_report(name, thresholds=thresholds) for name in repos],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--repo", action="append", choices=DEFAULT_REPOS)
    args = parser.parse_args()
    repos = args.repo or DEFAULT_REPOS
    baseline = build_baseline(repos, thresholds=DEFAULT_THRESHOLDS)
    payload = json.dumps(baseline, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
