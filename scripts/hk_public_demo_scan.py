#!/usr/bin/env python3
"""Safety scan for staged HK public demo trees."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

MAX_PUBLIC_FILE_BYTES = 512 * 1024
FORBIDDEN_PARTS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "cache",
    "outputs",
}
FORBIDDEN_SUFFIXES = {
    ".7z",
    ".feather",
    ".gz",
    ".parquet",
    ".pickle",
    ".pkl",
    ".tar",
    ".zst",
    ".zip",
}
FORBIDDEN_TEXT = {
    "absolute_local_path": re.compile(r"(?:/home/|/tmp/|/Users/|[A-Za-z]:\\\\Users\\\\)"),
    "credential_assignment": re.compile(
        r"(?i)(?:token|secret|password|api[_-]?key|access[_-]?key)\s*[:=]\s*[^\s<]+"
    ),
}
FORBIDDEN_WORKSPACE_IMPORTS = {
    "cstree",
    "hk_data_platform",
    "market_data_platform",
    "quant_execution_engine",
}
FORBIDDEN_RUNTIME_IMPORTS = {
    "alpaca",
    "ib_insync",
    "ibkr",
    "longport",
    "rqdatac",
    "tushare",
}
FORBIDDEN_RUNTIME_TEXT = {
    "broker_or_provider_runtime_marker": re.compile(
        r"(?i)\b(rqdata|rqdatac|tushare|longport|ibkr|alpaca|provider[-_ ]?cache)\b"
    ),
}
RUNTIME_TEXT_SUFFIXES = {
    ".cfg",
    ".csv",
    ".ini",
    ".json",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
ARCHIVE_PARTS = {"archive"}
ACTIVE_DEMO_PARTS = {"src", "scripts", "tests", "fixtures", "docs"}
Issue = dict[str, str]


def _issue(relative: Path, check: str) -> Issue:
    return {"path": relative.as_posix(), "check": check}


def _is_active_demo_file(relative: Path) -> bool:
    if any(part in ARCHIVE_PARTS for part in relative.parts):
        return False
    return bool(relative.parts and relative.parts[0] in ACTIVE_DEMO_PARTS)


def _module_root(name: str) -> str:
    return name.split(".", 1)[0]


def _scan_python_imports(path: Path, relative: Path) -> list[Issue]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
    except SyntaxError:
        return [_issue(relative, "python_syntax_error")]

    issues: list[Issue] = []
    for node in ast.walk(tree):
        imported: list[str] = []
        if isinstance(node, ast.Import):
            imported = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported = [node.module]
        for module in imported:
            root = _module_root(module)
            if root in FORBIDDEN_WORKSPACE_IMPORTS:
                issues.append(_issue(relative, "workspace_import"))
            if root in FORBIDDEN_RUNTIME_IMPORTS:
                issues.append(_issue(relative, "runtime_dependency_import"))
    return issues


def _path_metadata_issues(path: Path, relative: Path) -> list[Issue]:
    issues: list[Issue] = []
    if any(part.startswith(".env") or part in FORBIDDEN_PARTS for part in relative.parts):
        issues.append(_issue(relative, "forbidden_path"))
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        issues.append(_issue(relative, "licensed_or_archive_suffix"))
    if path.stat().st_size > MAX_PUBLIC_FILE_BYTES:
        issues.append(_issue(relative, "oversized_file"))
    return issues


def _text_issues(path: Path, relative: Path, text: str) -> list[Issue]:
    issues = [
        _issue(relative, check) for check, pattern in FORBIDDEN_TEXT.items() if pattern.search(text)
    ]
    if _is_active_demo_file(relative) and path.suffix.lower() == ".py":
        issues.extend(_scan_python_imports(path, relative))
    if (
        _is_active_demo_file(relative)
        and path.suffix.lower() in RUNTIME_TEXT_SUFFIXES
        and relative.as_posix() != "export-manifest.json"
    ):
        issues.extend(
            _issue(relative, check)
            for check, pattern in FORBIDDEN_RUNTIME_TEXT.items()
            if pattern.search(text)
        )
    return issues


def _scan_file(path: Path, *, root: Path) -> tuple[str, list[Issue]]:
    relative = path.relative_to(root)
    issues = _path_metadata_issues(path, relative)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        issues.append(_issue(relative, "non_utf8_file"))
    else:
        issues.extend(_text_issues(path, relative, text))
    return relative.as_posix(), issues


def scan_public_tree(root: Path) -> dict[str, Any]:
    issues: list[Issue] = []
    files: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative_text, file_issues = _scan_file(path, root=root)
        files.append(relative_text)
        issues.extend(file_issues)
    return {
        "status": "passed" if not issues else "failed",
        "files_scanned": len(files),
        "files": files,
        "issues": issues,
    }
