"""Workspace-local environment file helpers."""

from __future__ import annotations

import os
from pathlib import Path

TOP_LEVEL_ENV_FILE = ".env"
TOP_LEVEL_ENV_EXAMPLE = ".env.example"
SAFE_TOP_LEVEL_ENV_KEYS = {"DATA_PLATFORM_ROOT"}


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            values[key] = value
    return values


def env_file_issues(path: Path) -> list[str]:
    issues: list[str] = []
    if not path.is_file():
        return issues
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            issues.append("invalid line without KEY=VALUE")
            continue
        key = line.split("=", 1)[0].strip()
        if key not in SAFE_TOP_LEVEL_ENV_KEYS:
            issues.append(f"{key} is not allowlisted")
    return issues


def data_platform_root_text(root: Path | None) -> tuple[str, str]:
    from_env = os.environ.get("DATA_PLATFORM_ROOT", "").strip()
    if from_env:
        return from_env, "environment"
    if root is not None:
        from_file = parse_env_file(root / TOP_LEVEL_ENV_FILE).get("DATA_PLATFORM_ROOT", "").strip()
        if from_file:
            return from_file, TOP_LEVEL_ENV_FILE
    return "", ""
