"""README coverage check for the research-workspace superproject."""

from __future__ import annotations

from pathlib import Path

from doctor_common import EXPECTED_SUBMODULES
from workspace_governance import Check


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
