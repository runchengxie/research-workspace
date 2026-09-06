"""Checks that the workspace remains an integration layer, not a second owner."""

from __future__ import annotations

import json
from pathlib import Path

from workspace_governance_common import Check

_REQUIRED_TARGET_DOCS = (
    "ARCHITECTURE.md",
    "docs/governance/repository-naming-map.md",
    "docs/governance/target-contract-ownership-map.md",
    "docs/governance/public-private-boundary-matrix.md",
    "docs/evidence/target-repository-version-manifest-2026-09-06.json",
)
_ALLOWED_ROOT_PACKAGES = {"research_contracts"}


def _target_manifest_check(root: Path) -> Check:
    relative = "docs/evidence/target-repository-version-manifest-2026-09-06.json"
    path = root / relative
    if not path.is_file():
        return Check("ERROR", "integration-layer", f"Missing {relative}.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Check("ERROR", "integration-layer", f"Invalid {relative}: {exc}")
    if not isinstance(payload, dict):
        return Check("ERROR", "integration-layer", f"{relative} must contain an object.")
    required = {"schema_version", "status", "workspace", "staging_targets", "compatibility_gates"}
    missing = sorted(required - payload.keys())
    if missing:
        return Check(
            "ERROR",
            "integration-layer",
            f"{relative} is missing required fields: {', '.join(missing)}.",
        )
    targets = payload["staging_targets"]
    if not isinstance(targets, dict) or not {"quant-platform", "quant-research"}.issubset(targets):
        return Check(
            "ERROR",
            "integration-layer",
            f"{relative} must record quant-platform and quant-research staging targets.",
        )
    return Check("OK", "integration-layer", "Target repository manifest is complete.")


def check_integration_layer(root: Path) -> list[Check]:
    """Verify target governance exists and root source has no business owner package."""

    missing = [relative for relative in _REQUIRED_TARGET_DOCS if not (root / relative).is_file()]
    checks: list[Check] = []
    if missing:
        checks.append(
            Check(
                "ERROR",
                "integration-layer",
                "Missing target architecture documents: " + ", ".join(missing),
            )
        )

    source_root = root / "src"
    unexpected = []
    if source_root.is_dir():
        for child in sorted(source_root.iterdir()):
            if child.is_dir() and (child / "__init__.py").is_file():
                if child.name not in _ALLOWED_ROOT_PACKAGES:
                    unexpected.append(child.name)
    if unexpected:
        checks.append(
            Check(
                "ERROR",
                "integration-layer",
                "Root src contains business-owner packages: " + ", ".join(unexpected),
            )
        )

    checks.append(_target_manifest_check(root))
    if not checks:
        checks.append(
            Check("OK", "integration-layer", "Workspace has no root business-owner packages.")
        )
    elif all(check.severity == "OK" for check in checks):
        checks.append(
            Check("OK", "integration-layer", "Workspace remains a thin integration layer.")
        )
    return checks


__all__ = ["check_integration_layer"]
