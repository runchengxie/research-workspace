"""Hong Kong private archive governance checks."""

from __future__ import annotations

import json
from pathlib import Path

from doctor_common import HK_PRIVATE_ARCHIVE_MANIFEST
from workspace_governance import Check


def check_hk_private_archive_governance(root: Path) -> list[Check]:
    manifest_path = root / HK_PRIVATE_ARCHIVE_MANIFEST
    if not manifest_path.is_file():
        return [
            Check(
                "ERROR",
                "hk-private-archive",
                f"Missing {HK_PRIVATE_ARCHIVE_MANIFEST}.",
            )
        ]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [Check("ERROR", "hk-private-archive", f"Invalid private archive manifest: {exc}")]
    repository = manifest.get("archive_repository", {})
    expected = {
        "visibility": "private",
        "maintenance": "paused",
        "purpose": "restore_only",
        "workspace_integration": "external_not_submodule",
    }
    mismatches = [
        f"{key}={repository.get(key)!r}"
        for key, value in expected.items()
        if repository.get(key) != value
    ]
    archive_name = str(repository.get("name", "")).strip()
    integration_text = "\n".join(
        [
            (root / ".gitmodules").read_text(encoding="utf-8"),
            (root / "scripts" / "submodule_checks.json").read_text(encoding="utf-8"),
        ]
    )
    if archive_name and archive_name in integration_text:
        mismatches.append(f"{archive_name} is configured as an active workspace dependency")
    if mismatches:
        return [
            Check(
                "ERROR",
                "hk-private-archive",
                "Private archive governance mismatch: " + "; ".join(mismatches),
            )
        ]
    return [
        Check(
            "OK",
            "hk-private-archive",
            (f"{archive_name} 保持私有、暂停维护、恢复专用状态，并且不在 submodule graph 中。"),
        )
    ]
