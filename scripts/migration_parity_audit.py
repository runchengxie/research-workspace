"""Inventory and compare source trees without importing project code."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "build",
    "dist",
    "outputs",
    "data",
    "artifacts",
    "node_modules",
    "site",
    "published",
    ".worktrees",
}


def collect_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    """Return eligible files below *root*, sorted by relative path."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"root is not a directory: {root}")
    paths = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in suffixes
        and not any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts)
    ]
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def collect_python_symbols(path: Path) -> list[dict[str, Any]]:
    """Extract qualified classes/functions/methods from a Python file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        return [{"kind": "parse_error", "name": type(exc).__name__, "line": 1}]

    symbols: list[dict[str, Any]] = []

    def visit(node: ast.AST, parents: tuple[str, ...] = ()) -> None:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            symbols.append(
                {
                    "kind": kind,
                    "name": ".".join((*parents, node.name)),
                    "line": node.lineno,
                }
            )
            parents = (*parents, node.name)
        for child in ast.iter_child_nodes(node):
            visit(child, parents)

    visit(tree)
    return symbols


def _file_record(root: Path, path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    text = content.decode("utf-8", errors="replace")
    record: dict[str, Any] = {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "loc": len(text.splitlines()),
        "nonblank_loc": sum(bool(line.strip()) for line in text.splitlines()),
    }
    if path.suffix == ".py":
        record["symbols"] = collect_python_symbols(path)
    return record


def build_inventory(root: Path) -> dict[str, Any]:
    """Build a deterministic inventory for Python and Markdown files."""
    root = root.resolve()
    records = [_file_record(root, path) for path in collect_files(root, (".py", ".md"))]
    summary = {
        "files": len(records),
        "python_files": sum(record["path"].endswith(".py") for record in records),
        "python_loc": sum(record["loc"] for record in records if record["path"].endswith(".py")),
        "python_nonblank_loc": sum(
            record["nonblank_loc"] for record in records if record["path"].endswith(".py")
        ),
        "markdown_files": sum(record["path"].endswith(".md") for record in records),
        "markdown_loc": sum(record["loc"] for record in records if record["path"].endswith(".md")),
        "markdown_nonblank_loc": sum(
            record["nonblank_loc"] for record in records if record["path"].endswith(".md")
        ),
    }
    return {"root": str(root), "summary": summary, "files": records}


def _symbol_keys(inventory: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {
        (record["path"], symbol["kind"], symbol["name"])
        for record in inventory["files"]
        if record["path"].endswith(".py")
        for symbol in record.get("symbols", [])
        if symbol["kind"] != "parse_error"
    }


def _symbol_name_keys(inventory: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (symbol["kind"], symbol["name"])
        for record in inventory["files"]
        if record["path"].endswith(".py")
        for symbol in record.get("symbols", [])
        if symbol["kind"] != "parse_error"
    }


def compare_inventories(old: dict[str, Any], new: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare one legacy inventory against one or more target inventories."""
    new_records = [record for inventory in new for record in inventory["files"]]
    old_by_path = {record["path"]: record for record in old["files"]}
    new_by_path = {record["path"]: record for record in new_records}
    old_names = {Path(path).name for path in old_by_path}
    new_names = {Path(path).name for path in new_by_path}
    old_symbols = _symbol_keys(old)
    new_symbols = {
        (record["path"], kind, name)
        for record in new_records
        if record["path"].endswith(".py")
        for kind, name in ((symbol["kind"], symbol["name"]) for symbol in record.get("symbols", []))
        if kind != "parse_error"
    }
    old_symbol_names = _symbol_name_keys(old)
    new_symbol_names = {
        (kind, name)
        for record in new_records
        if record["path"].endswith(".py")
        for kind, name in ((symbol["kind"], symbol["name"]) for symbol in record.get("symbols", []))
        if kind != "parse_error"
    }
    return {
        "old_summary": old["summary"],
        "new_summary": {
            key: sum(inventory["summary"][key] for inventory in new) for key in old["summary"]
        },
        "exact_path_matches": sorted(set(old_by_path) & set(new_by_path)),
        "old_paths_absent": sorted(set(old_by_path) - set(new_by_path)),
        "new_paths_not_in_old": sorted(set(new_by_path) - set(old_by_path)),
        "exact_hash_matches": sorted(
            path
            for path in set(old_by_path) & set(new_by_path)
            if old_by_path[path]["sha256"] == new_by_path[path]["sha256"]
        ),
        "basename_candidates": sorted(old_names & new_names),
        "old_symbol_keys_absent_by_exact_path": sorted(old_symbols - new_symbols),
        "old_symbol_names_absent_globally": sorted(old_symbol_names - new_symbol_names),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--new", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    old = build_inventory(args.old)
    new = [build_inventory(root) for root in args.new]
    report = {
        "old": old,
        "new": new,
        "comparison": compare_inventories(old, new),
        "exclusions": sorted(EXCLUDED_DIRS),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["comparison"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
