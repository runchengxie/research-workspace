#!/usr/bin/env python3
"""Run superproject-owned quality profiles without scanning submodule source."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PlannedCommand:
    name: str
    command: tuple[str, ...]


def _ruff_command(*args: str) -> tuple[str, ...]:
    resolved = shutil.which("ruff")
    if resolved:
        return (resolved, *args)
    return ("uv", "run", "--with", "ruff", "ruff", *args)


def plan_commands(profile: str, *, demo_stage: str | None = None) -> list[PlannedCommand]:
    commands = {
        "lint": [
            PlannedCommand("ruff-check", _ruff_command("check", "scripts", "tests")),
            PlannedCommand("ruff-format", _ruff_command("format", "--check", "scripts", "tests")),
        ],
        "secrets": [
            PlannedCommand(
                "secret-scan",
                (
                    sys.executable,
                    str(ROOT / "scripts" / "scan_workspace_secrets.py"),
                    *(("--demo-stage", demo_stage) if demo_stage else ()),
                ),
            )
        ],
    }
    if profile == "hard":
        return [*commands["lint"], *commands["secrets"]]
    if profile in commands:
        return commands[profile]
    raise ValueError(f"Unknown quality profile: {profile}")


def _display(command: tuple[str, ...]) -> str:
    return " ".join(command)


def run_commands(commands: list[PlannedCommand], *, dry_run: bool) -> int:
    failed = 0
    for item in commands:
        if dry_run:
            print(f"[DRY-RUN] {item.name}: {_display(item.command)}")
            continue
        result = subprocess.run(item.command, cwd=ROOT, check=False)
        status = "OK" if result.returncode == 0 else "ERROR"
        print(f"[{status}] {item.name}: {_display(item.command)}")
        failed += int(result.returncode != 0)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("lint", "secrets", "hard"), default="hard")
    parser.add_argument("--demo-stage", help="Also scan an exported 港股 public-demo staging tree.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return run_commands(
        plan_commands(args.profile, demo_stage=args.demo_stage),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
