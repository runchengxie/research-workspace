from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY_DOCS = (
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "bootstrap.md",
    ROOT / "docs" / "workspace-maintenance.md",
    ROOT / "docs" / "quality-governance.md",
)
FORBIDDEN_FRAGMENTS = ("不是", "而是", "**", "；", "——", "“", "”")


def test_entry_docs_use_concise_chinese_style() -> None:
    offenders: list[str] = []

    for path in ENTRY_DOCS:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            for fragment in FORBIDDEN_FRAGMENTS:
                if fragment in line:
                    offenders.append(f"{path.relative_to(ROOT)}:{line_number}:{fragment}")

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

    assert "mypy" not in manifest
    assert "mypy_advisory" not in maintenance
    assert "mypy_advisory" not in quality
