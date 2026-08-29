"""Shared imports, constants and cross-domain helpers for workspace doctor checks."""

from __future__ import annotations

import configparser
import os
import shutil
import subprocess
from pathlib import Path

EXPECTED_SUBMODULES: dict[str, str | None] = {
    "market-data-platform": "marketdata",
    "alpha-research": None,
    "portfolio-backtester": None,
    "strategy-pipeline": "strategy",
    "quant-execution-engine": "qexec",
    "strategy-app": None,
    "deep-learning-tick-data-prediction": None,
    "strategy-research": None,
}

DATA_PLATFORM_ROOT_CANDIDATES = (
    Path.home() / "data" / "market-data-platform",
    Path("/data/market-data-platform"),
)
FORBIDDEN_TOP_LEVEL_PATTERNS = (".env", ".env.*", ".envrc", ".envrc.*")
FORBIDDEN_TOP_LEVEL_DIRS = ("artifacts", "outputs", "data", "cache")
FORBIDDEN_TOP_LEVEL_SHARED_CODE_DIRS = ("_shared",)
FORBIDDEN_SCRIPT_IMPORTS = {
    "cstree",
    "hk_data_platform",
    "market_data_platform",
    "quant_execution_engine",
}
HK_PRIVATE_ARCHIVE_MANIFEST = "docs/hk-private-archive-manifest.yml"
SHARED_HOOK_NAMES = ("pre-commit", "pre-push")


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
        capture_output=True,
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


def _configured_hooks_path(repository: Path) -> Path | None:
    completed = subprocess.run(
        ["git", "-C", str(repository), "config", "--local", "--get", "core.hooksPath"],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    configured = Path(completed.stdout.strip()).expanduser()
    if not configured.is_absolute():
        configured = repository / configured
    return configured.resolve()


def _repository_toplevel(repository: Path) -> Path | None:
    completed = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--show-toplevel"],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    return Path(completed.stdout.strip()).resolve()
