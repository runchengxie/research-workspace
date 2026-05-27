#!/usr/bin/env python3
"""Delegate quality checks to submodules without inspecting their internals."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path(__file__).with_name("submodule_checks.json")


@dataclass(frozen=True)
class SubmoduleConfig:
    name: str
    path: Path
    profiles: dict[str, list[Any]]


@dataclass(frozen=True)
class PlannedCommand:
    submodule: str
    cwd: Path
    command: tuple[str, ...]


@dataclass(frozen=True)
class CheckResult:
    severity: str
    submodule: str
    command: tuple[str, ...]
    message: str


class ManifestError(ValueError):
    """Raised when the submodule check manifest is invalid."""


def _as_string_list(value: Any, *, context: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ManifestError(f"{context} must be a non-empty command array")
    if not all(isinstance(part, str) and part for part in value):
        raise ManifestError(f"{context} must contain only non-empty strings")
    return value


def _safe_relative_path(value: Any, *, context: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{context} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ManifestError(f"{context} must stay inside the workspace")
    return path


def load_manifest(path: Path) -> dict[str, SubmoduleConfig]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"{path} is not valid JSON: {exc}") from exc

    submodules = raw.get("submodules")
    if not isinstance(submodules, dict) or not submodules:
        raise ManifestError("manifest must define a non-empty 'submodules' object")

    configs: dict[str, SubmoduleConfig] = {}
    for name, value in submodules.items():
        if not isinstance(name, str) or not name:
            raise ManifestError("submodule names must be non-empty strings")
        if not isinstance(value, dict):
            raise ManifestError(f"{name} must be an object")
        path = _safe_relative_path(value.get("path", name), context=f"{name}.path")
        profiles = value.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            raise ManifestError(f"{name}.profiles must be a non-empty object")
        normalized_profiles: dict[str, list[Any]] = {}
        for profile, commands in profiles.items():
            if not isinstance(profile, str) or not profile:
                raise ManifestError(f"{name}.profiles has an invalid profile name")
            if not isinstance(commands, list):
                raise ManifestError(f"{name}.{profile} must be a command list")
            normalized_profiles[profile] = commands
        configs[name] = SubmoduleConfig(name=name, path=path, profiles=normalized_profiles)
    return configs


def _expand_profile(
    config: SubmoduleConfig,
    profile: str,
    *,
    stack: tuple[str, ...] = (),
) -> list[tuple[str, ...]]:
    if profile in stack:
        cycle = " -> ".join((*stack, profile))
        raise ManifestError(f"{config.name}.{profile} contains a profile cycle: {cycle}")
    if profile not in config.profiles:
        raise ManifestError(f"{config.name} does not define profile '{profile}'")

    commands: list[tuple[str, ...]] = []
    for index, entry in enumerate(config.profiles[profile], start=1):
        context = f"{config.name}.{profile}[{index}]"
        if isinstance(entry, str):
            if not entry.startswith("@") or entry == "@":
                raise ManifestError(f"{context} string entries must be @profile references")
            commands.extend(_expand_profile(config, entry[1:], stack=(*stack, profile)))
            continue
        commands.append(tuple(_as_string_list(entry, context=context)))
    return commands


def available_profiles(configs: dict[str, SubmoduleConfig]) -> list[str]:
    profiles = {profile for config in configs.values() for profile in config.profiles}
    return sorted(profiles)


def plan_commands(
    root: Path,
    configs: dict[str, SubmoduleConfig],
    *,
    profile: str,
    submodules: list[str] | None = None,
) -> list[PlannedCommand]:
    selected_names = submodules or sorted(configs)
    missing = [name for name in selected_names if name not in configs]
    if missing:
        raise ManifestError(f"unknown submodule(s): {', '.join(missing)}")

    planned: list[PlannedCommand] = []
    for name in selected_names:
        config = configs[name]
        cwd = root / config.path
        for command in _expand_profile(config, profile):
            planned.append(PlannedCommand(submodule=name, cwd=cwd, command=command))
    return planned


def _format_command(command: tuple[str, ...]) -> str:
    return " ".join(command)


def run_planned_commands(
    planned: list[PlannedCommand],
    *,
    timeout: int,
    dry_run: bool,
    fail_fast: bool,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for item in planned:
        if not item.cwd.is_dir():
            result = CheckResult(
                "ERROR",
                item.submodule,
                item.command,
                f"missing submodule directory: {item.cwd}",
            )
            results.append(result)
            if fail_fast:
                break
            continue

        if dry_run:
            results.append(CheckResult("DRY-RUN", item.submodule, item.command, str(item.cwd)))
            continue

        try:
            completed = subprocess.run(
                list(item.command),
                cwd=item.cwd,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        except (FileNotFoundError, PermissionError) as exc:
            results.append(CheckResult("ERROR", item.submodule, item.command, str(exc)))
            if fail_fast:
                break
            continue
        except subprocess.TimeoutExpired:
            results.append(
                CheckResult("ERROR", item.submodule, item.command, f"timed out after {timeout}s")
            )
            if fail_fast:
                break
            continue

        if completed.returncode == 0:
            results.append(CheckResult("OK", item.submodule, item.command, "passed"))
            continue

        detail = (completed.stderr or completed.stdout).strip().splitlines()
        message = detail[-1] if detail else f"exit code {completed.returncode}"
        results.append(CheckResult("ERROR", item.submodule, item.command, message))
        if fail_fast:
            break
    return results


def render_results(results: list[CheckResult]) -> str:
    lines = [
        f"[{result.severity}] {result.submodule}: "
        f"{_format_command(result.command)}: {result.message}"
        for result in results
    ]
    ok = sum(1 for result in results if result.severity == "OK")
    dry_run = sum(1 for result in results if result.severity == "DRY-RUN")
    errors = sum(1 for result in results if result.severity == "ERROR")
    lines.append(f"Summary: ok={ok} dry_run={dry_run} errors={errors}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run manifest-defined checks inside submodules.",
    )
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--profile", default="smoke")
    parser.add_argument(
        "--submodule",
        action="append",
        help="Limit to one submodule. May be provided multiple times.",
    )
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--list-profiles", action="store_true")
    args = parser.parse_args(argv)

    try:
        configs = load_manifest(Path(args.manifest))
        if args.list_profiles:
            for profile in available_profiles(configs):
                print(profile)
            return 0

        planned = plan_commands(
            Path(args.root).resolve(),
            configs,
            profile=args.profile,
            submodules=args.submodule,
        )
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    results = run_planned_commands(
        planned,
        timeout=args.timeout,
        dry_run=args.dry_run,
        fail_fast=args.fail_fast,
    )
    print(render_results(results))
    return 1 if any(result.severity == "ERROR" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
