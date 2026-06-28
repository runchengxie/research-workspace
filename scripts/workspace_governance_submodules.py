"""Submodule check manifest governance gates."""

from __future__ import annotations

import json
from pathlib import Path

from workspace_governance_common import Check

SUBMODULE_CHECKS_MANIFEST = "scripts/submodule_checks.json"
REQUIRED_SUBMODULE_GOVERNANCE_GATES = {
    "market-data-platform": {
        "profile": "lint",
        "command": [
            "uv",
            "run",
            "--extra",
            "dev",
            "python",
            "scripts/dev/architecture_governance.py",
            "--check",
        ],
        "reason": "data-platform HK split boundary gate",
    },
    "strategy-pipeline": {
        "profile": "lint",
        "command": ["scripts/dev/run_tests.sh", "maintainability"],
        "reason": "strategy-research maintainability ratchet",
    },
}


def _submodule_profile_commands(
    manifest: dict[str, object],
    *,
    submodule: str,
    profile: str,
) -> list[object]:
    submodules = manifest.get("submodules")
    if not isinstance(submodules, dict):
        return []
    config = submodules.get(submodule)
    if not isinstance(config, dict):
        return []
    profiles = config.get("profiles")
    if not isinstance(profiles, dict):
        return []
    commands = profiles.get(profile)
    return commands if isinstance(commands, list) else []


def check_submodule_governance_gates(root: Path) -> list[Check]:
    manifest_path = root / SUBMODULE_CHECKS_MANIFEST
    if not manifest_path.is_file():
        return [
            Check(
                "ERROR",
                "submodule-governance-gates",
                f"Missing {SUBMODULE_CHECKS_MANIFEST}.",
            )
        ]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [
            Check(
                "ERROR",
                "submodule-governance-gates",
                f"Invalid {SUBMODULE_CHECKS_MANIFEST}: {exc}",
            )
        ]
    if not isinstance(manifest, dict):
        return [
            Check(
                "ERROR",
                "submodule-governance-gates",
                f"{SUBMODULE_CHECKS_MANIFEST} must contain an object.",
            )
        ]

    issues: list[str] = []
    for submodule, gate in REQUIRED_SUBMODULE_GOVERNANCE_GATES.items():
        profile = str(gate["profile"])
        command = gate["command"]
        reason = str(gate["reason"])
        commands = _submodule_profile_commands(manifest, submodule=submodule, profile=profile)
        if command not in commands:
            issues.append(f"{submodule}:{profile} missing {reason}")
        full_commands = _submodule_profile_commands(manifest, submodule=submodule, profile="full")
        if "@lint" not in full_commands:
            issues.append(f"{submodule}:full does not include @lint")

    if issues:
        return [
            Check(
                "ERROR",
                "submodule-governance-gates",
                "Submodule governance gates are not wired into delegated checks: "
                + "; ".join(issues),
            )
        ]
    return [
        Check(
            "OK",
            "submodule-governance-gates",
            "Delegated lint/full checks include required repo-local governance gates.",
        )
    ]
