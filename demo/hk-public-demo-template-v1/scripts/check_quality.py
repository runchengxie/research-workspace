from __future__ import annotations

import ast
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_DIRS = ("src", "scripts", "tests")
FORBIDDEN_WORKSPACE_IMPORTS = {
    "cstree",
    "hk_data_platform",
    "market_data_platform",
    "quant_execution_engine",
}


def _module_root(name: str) -> str:
    return name.split(".", 1)[0]


def _scan_imports() -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for dirname in ACTIVE_DIRS:
        for path in sorted((ROOT / dirname).rglob("*.py")):
            relative = path.relative_to(ROOT)
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
            except SyntaxError:
                issues.append({"path": relative.as_posix(), "check": "python_syntax_error"})
                continue
            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                for module in modules:
                    if _module_root(module) in FORBIDDEN_WORKSPACE_IMPORTS:
                        issues.append({"path": relative.as_posix(), "check": "workspace_import"})
    return issues


def _check_config() -> list[dict[str, str]]:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    issues: list[dict[str, str]] = []
    if "ruff" not in config.get("tool", {}):
        issues.append({"path": "pyproject.toml", "check": "missing_ruff_config"})
    if "pyright" not in config.get("tool", {}):
        issues.append({"path": "pyproject.toml", "check": "missing_pyright_config"})
    return issues


def main() -> int:
    issues = []
    issues.extend(_scan_imports())
    issues.extend(_check_config())
    payload = {
        "status": "passed" if not issues else "failed",
        "issues": issues,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
