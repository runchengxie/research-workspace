from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_ENTRY_DOCS = (
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / ".github" / "pull_request_template.md",
)
ACTIVE_DOCS = tuple(
    path
    for path in sorted((ROOT / "docs").rglob("*.md"))
    if "archive" not in path.relative_to(ROOT / "docs").parts
    and "evidence" not in path.relative_to(ROOT / "docs").parts
    and "superpowers" not in path.relative_to(ROOT / "docs").parts
    and "prereg" not in path.name.lower()
)
STYLE_DOCS = (*ROOT_ENTRY_DOCS, *ACTIVE_DOCS)
FORBIDDEN_FRAGMENTS = ("**", "；", "——", "“", "”")
INDIRECT_CONTRAST = re.compile(r"不是[^。]{0,100}而是|而不是")
EXPECTED_SUBMODULES = {
    "market-data-platform",
    "deep-learning-tick-data-prediction",
    "alpha-research",
    "portfolio-backtester",
    "strategy-research",
    "strategy-app",
    "strategy-pipeline",
    "quant-execution-engine",
}


def test_entry_docs_use_concise_chinese_style() -> None:
    offenders: list[str] = []

    for path in STYLE_DOCS:
        text = path.read_text(encoding="utf-8")
        for fragment in FORBIDDEN_FRAGMENTS:
            for match in re.finditer(re.escape(fragment), text):
                line_number = text.count("\n", 0, match.start()) + 1
                offenders.append(f"{path.relative_to(ROOT)}:{line_number}:{fragment}")
        for match in INDIRECT_CONTRAST.finditer(text):
            line_number = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{path.relative_to(ROOT)}:{line_number}:先否定再转折")

    assert offenders == []


def test_e2_is_documented_as_a_promotion_audit() -> None:
    roadmap = (ROOT / "docs" / "roadmap.md").read_text(encoding="utf-8")
    evidence_gate = (ROOT / "docs" / "strategy-evidence-gate.md").read_text(encoding="utf-8")
    strategy_research = (ROOT / "strategy-research" / "README.md").read_text(encoding="utf-8")

    assert "生产准备审计" in roadmap
    assert "不替代当前策略研究" in roadmap
    assert "production-readiness audit" in evidence_gate
    assert "not active strategy research" in evidence_gate
    assert "E2" in strategy_research


def test_public_ci_policy_matches_active_workflow() -> None:
    active = ROOT / ".github" / "workflows" / "contracts.yml"
    obsolete = ROOT / ".github" / "workflows" / "superproject.yml.disabled"
    maintenance = (ROOT / "docs" / "workspace-maintenance.md").read_text(encoding="utf-8")
    quality = (ROOT / "docs" / "quality-governance.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert active.is_file()
    assert not obsolete.exists()
    workflow = active.read_text(encoding="utf-8")
    assert "submodules: false" in workflow
    assert "tests/test_platform_publication.py" in workflow
    assert "tests/test_run_submodule_fail_fast.py" in workflow
    for text in (maintenance, quality, agents):
        assert "public 仓库默认启用 GitHub Actions" in text
        assert "private 仓库默认关闭 GitHub Actions" in text


def test_ci_policy_covers_all_submodules() -> None:
    quality = (ROOT / "docs" / "quality-governance.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    for name in EXPECTED_SUBMODULES:
        assert f"`{name}`" in quality
        assert f"`{name}`" in agents


def test_framework_matrix_matches_current_main_surfaces() -> None:
    matrix = (ROOT / "docs" / "framework-support-matrix.md").read_text(encoding="utf-8")

    assert "`market-data-platform` | 已实现，条件化验证" in matrix
    assert "`alpha-research` | 已实现，条件化验证" in matrix
    assert "`portfolio-backtester` | 仅有接口，差分后端规划中 | 设计参考" in matrix
    assert "`quant-execution-engine` | 范围外 | 范围外 | 仅有通用执行接口" in matrix
    assert "Backtrader 仍处于规划阶段" in matrix
    assert (ROOT / "market-data-platform/src/market_data_platform/integrations/qlib.py").is_file()
    assert (ROOT / "alpha-research/src/alpha_research/backends/native.py").is_file()
    assert (ROOT / "alpha-research/src/alpha_research/backends/qlib.py").is_file()
    assert (ROOT / "portfolio-backtester/src/portfolio_backtester/backends/native.py").is_file()
    vnpy_transport = ROOT / "quant-execution-engine/src/quant_execution_engine/vnpy_transport.py"
    assert not vnpy_transport.exists()


def test_local_hook_installation_is_in_bootstrap_and_maintenance_docs() -> None:
    bootstrap = (ROOT / "docs" / "bootstrap.md").read_text(encoding="utf-8")
    maintenance = (ROOT / "docs" / "workspace-maintenance.md").read_text(encoding="utf-8")

    for text in (bootstrap, maintenance):
        assert "python scripts/install_pre_push_hooks.py --dry-run" in text
        assert "python scripts/install_pre_push_hooks.py --check" in text
    assert "git push --no-verify" in maintenance


def test_root_integration_tests_use_workspace_runner() -> None:
    docs = (
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "docs" / "bootstrap.md",
        ROOT / "docs" / "workspace-maintenance.md",
    )
    stale_command = "uv run --project strategy-pipeline --extra dev python -m pytest tests -q"

    for path in docs:
        text = path.read_text(encoding="utf-8")
        assert "python scripts/run_workspace_tests.py" in text
        assert stale_command not in text


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


def test_active_navigation_does_not_use_internal_as_an_entrypoint() -> None:
    navigation_docs = (
        ROOT / "docs" / "README.md",
        ROOT / "docs" / "platform-workflow.md",
        ROOT / "docs" / "strategy-catalog.md",
    )
    forbidden = "https://github.com/runchengxie/strategy-pipeline-internal"

    assert all(forbidden not in path.read_text(encoding="utf-8") for path in navigation_docs)
