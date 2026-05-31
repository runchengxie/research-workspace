#!/usr/bin/env python3
"""Read-only checks for the research-workspace superproject."""

from __future__ import annotations

import argparse
import ast
import configparser
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


EXPECTED_SUBMODULES = {
    "market-data-platform": "marketdata",
    "cross-sectional-trees": "cstree",
    "quant-execution-engine": "qexec",
}

FORBIDDEN_TOP_LEVEL_PATTERNS = (".env", ".env.*", ".envrc", ".envrc.*")
FORBIDDEN_TOP_LEVEL_DIRS = ("artifacts", "outputs", "data", "cache")
FORBIDDEN_SCRIPT_IMPORTS = {
    "cstree",
    "hk_data_platform",
    "market_data_platform",
    "quant_execution_engine",
}


@dataclass(frozen=True)
class Check:
    severity: str
    code: str
    message: str


def parse_gitmodules(root: Path) -> dict[str, str]:
    path = root / ".gitmodules"
    if not path.is_file():
        return {}
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    submodules: dict[str, str] = {}
    for section in parser.sections():
        if not section.startswith("submodule "):
            continue
        name = section.removeprefix("submodule ").strip().strip('"')
        sub_path = parser.get(section, "path", fallback="").strip()
        if name and sub_path:
            submodules[name] = sub_path
    return submodules


def _git_status_short(path: Path) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", "-C", str(path), "status", "--short"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _public_command_candidates(root: Path, submodule_path: str, command: str) -> list[Path]:
    repo = root / submodule_path
    return [
        repo / ".venv" / "bin" / command,
        repo / ".venv" / "Scripts" / f"{command}.exe",
    ]


def _has_valid_shebang(path: Path) -> bool:
    try:
        first_line = path.read_bytes().splitlines()[0].decode("utf-8", errors="ignore")
    except (IndexError, OSError):
        return False
    if not first_line.startswith("#!"):
        return True
    interpreter = first_line[2:].strip().split(" ", 1)[0]
    if interpreter == "/usr/bin/env":
        return True
    if interpreter.startswith("/"):
        return Path(interpreter).exists()
    return True


def resolve_public_command(root: Path, submodule_path: str, command: str) -> str | None:
    for candidate in _public_command_candidates(root, submodule_path, command):
        if candidate.is_file() and os.access(candidate, os.X_OK) and _has_valid_shebang(candidate):
            return str(candidate)
    resolved = shutil.which(command)
    return resolved


def check_gitmodules(root: Path) -> list[Check]:
    checks: list[Check] = []
    submodules = parse_gitmodules(root)
    if not submodules:
        return [Check("ERROR", "gitmodules", "Missing or empty .gitmodules.")]

    expected_paths = set(EXPECTED_SUBMODULES)
    actual_paths = set(submodules.values())
    missing = sorted(expected_paths - actual_paths)
    extra = sorted(actual_paths - expected_paths)
    if missing:
        checks.append(
            Check("ERROR", "gitmodules", f"Missing expected submodule paths: {', '.join(missing)}")
        )
    if extra:
        checks.append(
            Check("WARN", "gitmodules", f"Unexpected submodule paths: {', '.join(extra)}")
        )
    if not missing:
        checks.append(Check("OK", "gitmodules", "Expected submodule paths are present."))
    return checks


def check_readme(root: Path) -> list[Check]:
    readme = root / "README.md"
    if not readme.is_file():
        return [Check("ERROR", "readme", "README.md is missing.")]
    text = readme.read_text(encoding="utf-8")
    missing = [path for path in EXPECTED_SUBMODULES if path not in text]
    if missing:
        return [
            Check(
                "WARN",
                "readme-submodules",
                f"README.md does not mention expected submodules: {', '.join(missing)}",
            )
        ]
    return [Check("OK", "readme-submodules", "README.md mentions expected submodules.")]


def check_submodule_state(root: Path) -> list[Check]:
    checks: list[Check] = []
    for path in EXPECTED_SUBMODULES:
        repo = root / path
        if not repo.exists():
            checks.append(Check("ERROR", "submodule-init", f"{path} is missing."))
            continue
        if not (repo / ".git").exists():
            checks.append(Check("ERROR", "submodule-init", f"{path} is not initialized."))
            continue
        code, stdout, stderr = _git_status_short(repo)
        if code != 0:
            detail = stderr or "git status failed"
            checks.append(Check("WARN", "submodule-status", f"{path}: {detail}"))
        elif stdout:
            checks.append(Check("WARN", "submodule-dirty", f"{path} has local changes."))
        else:
            checks.append(Check("OK", "submodule-clean", f"{path} is clean."))
    return checks


def check_public_clis(root: Path) -> list[Check]:
    checks: list[Check] = []
    for path, command in EXPECTED_SUBMODULES.items():
        resolved = resolve_public_command(root, path, command)
        if resolved:
            checks.append(Check("OK", "cli", f"{command} resolves to {resolved}."))
        else:
            existing = [candidate for candidate in _public_command_candidates(root, path, command) if candidate.is_file()]
            broken = [
                candidate
                for candidate in existing
                if not os.access(candidate, os.X_OK) or not _has_valid_shebang(candidate)
            ]
            if broken:
                checks.append(
                    Check(
                        "WARN",
                        "cli",
                        f"{command} entrypoint exists but is not runnable: {broken[0]}",
                    )
                )
                continue
            checks.append(
                Check(
                    "WARN",
                    "cli",
                    f"{command} is not on PATH and no {path}/.venv command was found.",
                )
            )
    return checks


def check_data_platform_root() -> list[Check]:
    root_text = os.environ.get("DATA_PLATFORM_ROOT", "").strip()
    if not root_text:
        return [
            Check(
                "WARN",
                "data-platform-root",
                "DATA_PLATFORM_ROOT is not set; current contract checks are skipped.",
            )
        ]

    artifact_root = Path(root_text).expanduser()
    checks: list[Check] = []
    if not artifact_root.exists():
        return [
            Check(
                "WARN",
                "data-platform-root",
                f"DATA_PLATFORM_ROOT does not exist: {artifact_root}",
            )
        ]

    checks.append(Check("OK", "data-platform-root", f"DATA_PLATFORM_ROOT={artifact_root}"))
    current_root = artifact_root / "metadata" / "current_assets"
    hk_contract = current_root / "hk_current.json"
    a_share_contract = current_root / "a_share_current.json"
    legacy_cn_contract = current_root / "cn_current.json"
    dataset_registry = artifact_root / "metadata" / "dataset_registry.csv"
    if hk_contract.is_file():
        checks.append(Check("OK", "current-contract", f"Found {hk_contract}."))
    else:
        checks.append(Check("WARN", "current-contract", f"Missing {hk_contract}."))
    if a_share_contract.is_file():
        checks.append(Check("OK", "current-contract", f"Found {a_share_contract}."))
    else:
        checks.append(Check("WARN", "current-contract", f"Missing {a_share_contract}."))
    if legacy_cn_contract.exists():
        checks.append(
            Check(
                "WARN",
                "current-contract-alias",
                f"Legacy alias exists; do not use as canonical A-share entry: {legacy_cn_contract}.",
            )
        )
    if dataset_registry.is_file():
        checks.append(Check("OK", "dataset-registry", f"Found {dataset_registry}."))
    else:
        checks.append(Check("WARN", "dataset-registry", f"Missing {dataset_registry}."))
    return checks


def check_top_level_outputs(root: Path) -> list[Check]:
    checks: list[Check] = []
    leaked_files: list[str] = []
    for pattern in FORBIDDEN_TOP_LEVEL_PATTERNS:
        for candidate in root.glob(pattern):
            if candidate.name == ".env.example":
                continue
            leaked_files.append(candidate.name)
    if leaked_files:
        checks.append(
            Check("ERROR", "top-level-secrets", f"Forbidden top-level env files: {', '.join(sorted(leaked_files))}")
        )
    else:
        checks.append(Check("OK", "top-level-secrets", "No forbidden top-level env files found."))

    leaked_dirs = [name for name in FORBIDDEN_TOP_LEVEL_DIRS if (root / name).exists()]
    if leaked_dirs:
        checks.append(
            Check("WARN", "top-level-artifacts", f"Top-level generated/data dirs found: {', '.join(leaked_dirs)}")
        )
    else:
        checks.append(Check("OK", "top-level-artifacts", "No top-level data/cache/output dirs found."))
    return checks


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
                "Top-level scripts import submodule Python packages: "
                + "; ".join(violations),
            )
        ]
    return [
        Check(
            "OK",
            "script-import-boundary",
            "Top-level scripts do not import submodule Python packages.",
        )
    ]


def run_checks(root: Path) -> list[Check]:
    root = root.resolve()
    checks: list[Check] = []
    checks.extend(check_gitmodules(root))
    checks.extend(check_readme(root))
    checks.extend(check_submodule_state(root))
    checks.extend(check_public_clis(root))
    checks.extend(check_data_platform_root())
    checks.extend(check_top_level_outputs(root))
    checks.extend(check_script_import_boundaries(root))
    return checks


def render_checks(checks: list[Check]) -> str:
    lines = [f"[{check.severity}] {check.code}: {check.message}" for check in checks]
    errors = sum(1 for check in checks if check.severity == "ERROR")
    warnings = sum(1 for check in checks if check.severity == "WARN")
    lines.append(f"Summary: errors={errors} warnings={warnings}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run read-only workspace health checks.")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures. Useful before bumping submodule pointers.",
    )
    args = parser.parse_args(argv)

    checks = run_checks(Path(args.root))
    print(render_checks(checks))
    has_errors = any(check.severity == "ERROR" for check in checks)
    has_warnings = any(check.severity == "WARN" for check in checks)
    if has_errors or (args.strict and has_warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
