"""Top-level script import boundary checks."""

from __future__ import annotations

import ast
from pathlib import Path

from doctor_common import FORBIDDEN_SCRIPT_IMPORTS
from workspace_governance import Check


def _iter_imported_modules(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [f"<syntax-error:{exc.lineno}>"]

    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def _is_forbidden_import(module: str) -> bool:
    return any(
        module == forbidden or module.startswith(f"{forbidden}.")
        for forbidden in FORBIDDEN_SCRIPT_IMPORTS
    )


def check_script_import_boundaries(root: Path) -> list[Check]:
    scripts_root = root / "scripts"
    if not scripts_root.is_dir():
        return [Check("WARN", "script-import-boundary", "scripts/ is missing.")]

    violations: list[str] = []
    for script in sorted(scripts_root.glob("*.py")):
        for module in _iter_imported_modules(script):
            if module.startswith("<syntax-error:"):
                violations.append(f"{script.relative_to(root)} has {module}")
            elif _is_forbidden_import(module):
                violations.append(f"{script.relative_to(root)} imports {module}")

    if violations:
        return [
            Check(
                "ERROR",
                "script-import-boundary",
                "Top-level scripts import submodule Python packages: " + "; ".join(violations),
            )
        ]
    return [
        Check(
            "OK",
            "script-import-boundary",
            "Top-level scripts do not import submodule Python packages.",
        )
    ]
