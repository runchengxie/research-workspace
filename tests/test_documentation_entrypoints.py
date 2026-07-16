from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY_DOCS = (
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / ".github" / "pull_request_template.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "bootstrap.md",
    ROOT / "docs" / "documentation-lifecycle.md",
    ROOT / "docs" / "framework-adapter-release.md",
    ROOT / "docs" / "platform-workflow.md",
    ROOT / "docs" / "release-checklist.md",
    ROOT / "docs" / "strategy-satellites.md",
    ROOT / "docs" / "workspace-maintenance.md",
    ROOT / "docs" / "quality-governance.md",
)
FORBIDDEN_FRAGMENTS = ("**", "；", "——", "“", "”")
INDIRECT_CONTRAST = re.compile(r"不是[^。]{0,100}而是|而不是")


def test_entry_docs_use_concise_chinese_style() -> None:
    offenders: list[str] = []

    for path in ENTRY_DOCS:
        text = path.read_text(encoding="utf-8")
        for fragment in FORBIDDEN_FRAGMENTS:
            for match in re.finditer(re.escape(fragment), text):
                line_number = text.count("\n", 0, match.start()) + 1
                offenders.append(f"{path.relative_to(ROOT)}:{line_number}:{fragment}")
        for match in INDIRECT_CONTRAST.finditer(text):
            line_number = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{path.relative_to(ROOT)}:{line_number}:先否定再转折")

    assert offenders == []


def test_disabled_workflow_status_is_documented() -> None:
    active = ROOT / ".github" / "workflows" / "superproject.yml"
    disabled = ROOT / ".github" / "workflows" / "superproject.yml.disabled"
    maintenance = (ROOT / "docs" / "workspace-maintenance.md").read_text(encoding="utf-8")
    quality = (ROOT / "docs" / "quality-governance.md").read_text(encoding="utf-8")

    assert not active.exists()
    assert disabled.is_file()
    assert "当前没有启用顶层 GitHub Actions workflow" in maintenance
    assert "目前没有活动 GitHub Actions workflow" in quality


def test_local_hook_installation_is_in_bootstrap_and_maintenance_docs() -> None:
    bootstrap = (ROOT / "docs" / "bootstrap.md").read_text(encoding="utf-8")
    maintenance = (ROOT / "docs" / "workspace-maintenance.md").read_text(encoding="utf-8")

    for text in (bootstrap, maintenance):
        assert "python scripts/install_pre_push_hooks.py --dry-run" in text
        assert "python scripts/install_pre_push_hooks.py --check" in text
    assert "git push --no-verify" in maintenance


def test_removed_mypy_is_not_delegated() -> None:
    manifest = (ROOT / "scripts" / "submodule_checks.json").read_text(encoding="utf-8").lower()
    maintenance = (ROOT / "docs" / "workspace-maintenance.md").read_text(encoding="utf-8").lower()
    quality = (ROOT / "docs" / "quality-governance.md").read_text(encoding="utf-8").lower()
    release = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8").lower()

    assert "mypy" not in manifest
    assert "mypy_advisory" not in maintenance
    assert "mypy_advisory" not in quality
    assert "mypy_advisory" not in release


def test_documented_submodule_profiles_exist() -> None:
    manifest = json.loads((ROOT / "scripts" / "submodule_checks.json").read_text())
    available = {
        profile for config in manifest["submodules"].values() for profile in config["profiles"]
    }
    documented: list[tuple[Path, str]] = []
    paths = (ROOT / "README.md", ROOT / "AGENTS.md", *sorted((ROOT / "docs").glob("*.md")))
    pattern = re.compile(r"run_submodule_checks\.py\s+--profile\s+([a-z0-9_-]+)")
    for path in paths:
        for profile in pattern.findall(path.read_text(encoding="utf-8")):
            documented.append((path, profile))
    invalid = [
        f"{path.relative_to(ROOT)}:{profile}"
        for path, profile in documented
        if profile not in available
    ]
    assert documented
    assert invalid == []
