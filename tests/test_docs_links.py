from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
EXPECTED_SUBMODULES = {
    "alpha-research",
    "market-data-platform",
    "portfolio-backtester",
    "strategy-pipeline",
    "quant-execution-engine",
}


def _uninitialized_submodule_for(path: Path) -> str | None:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return None
    if not relative.parts:
        return None
    submodule = relative.parts[0]
    if submodule not in EXPECTED_SUBMODULES:
        return None
    if not (ROOT / submodule / ".git").exists():
        return submodule
    return None


class DocsLinksTest(unittest.TestCase):
    def test_top_level_markdown_links_resolve(self) -> None:
        markdown_files = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
        missing: list[str] = []
        for markdown in markdown_files:
            text = markdown.read_text(encoding="utf-8")
            for match in LINK_RE.finditer(text):
                target = match.group(1).strip()
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                target = target.split("#", 1)[0]
                if not target:
                    continue
                if " " in target and not target.startswith("<"):
                    continue
                target = target.strip("<>")
                resolved = (markdown.parent / target).resolve()
                if not resolved.exists():
                    submodule = _uninitialized_submodule_for(resolved)
                    if submodule:
                        missing.append(
                            f"{markdown.relative_to(ROOT)} -> {target} "
                            f"(points into uninitialized submodule {submodule}; "
                            "run: git submodule update --init --recursive)"
                        )
                    else:
                        missing.append(f"{markdown.relative_to(ROOT)} -> {target}")
        self.assertEqual([], missing)

    def test_docs_index_links_root_architecture_and_contributing(self) -> None:
        docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")

        self.assertTrue((ROOT / "ARCHITECTURE.md").is_file())
        self.assertTrue((ROOT / "CONTRIBUTING.md").is_file())
        self.assertIn("[../ARCHITECTURE.md](../ARCHITECTURE.md)", docs_index)
        self.assertIn("[../CONTRIBUTING.md](../CONTRIBUTING.md)", docs_index)

    def test_documentation_lifecycle_owner_template_covers_active_submodules(self) -> None:
        lifecycle = (ROOT / "docs" / "documentation-lifecycle.md").read_text(encoding="utf-8")

        self.assertIn("> owner: workspace |", lifecycle)
        for submodule in EXPECTED_SUBMODULES:
            self.assertIn(submodule, lifecycle)

    def test_docs_preserve_hk_restore_only_boundary(self) -> None:
        docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        archive_index = (ROOT / "docs" / "archive" / "hk" / "README.md").read_text(encoding="utf-8")

        self.assertIn("restore-only archive", docs_index)
        self.assertIn("source_of_truth: yes", archive_index)
        self.assertIn("public demo 路线已经退役", archive_index)

    def test_hk_archive_records_are_outside_primary_path(self) -> None:
        archive_index = (ROOT / "docs" / "archive" / "hk" / "README.md").read_text(encoding="utf-8")

        self.assertIn("records/hk-cold-freeze-20260526.md", archive_index)
        self.assertIn("records/hk-research-cold-storage-20260601.md", archive_index)
        self.assertNotIn("release-notes/", archive_index)
        self.assertNotIn("session-handoffs/", archive_index)

    def test_docs_preserve_canonical_a_share_contract_name(self) -> None:
        contracts = (ROOT / "docs" / "contracts.md").read_text(encoding="utf-8")
        playbook = (ROOT / "docs" / "data-transition-playbook.md").read_text(encoding="utf-8")

        self.assertIn("metadata/current_assets/a_share_current.json", contracts)
        self.assertIn("metadata/current_assets/a_share_current.json", playbook)
        self.assertIn("metadata/current_assets/cn_current.json", playbook)
        self.assertIn("历史兼容 alias", playbook)
        self.assertIn("不能作为新的 A 股权威入口", playbook)

    def test_docs_preserve_cross_module_artifact_contracts(self) -> None:
        contracts = (ROOT / "docs" / "contracts.md").read_text(encoding="utf-8")

        for phrase in (
            "cstree.signals",
            "signals.meta.json",
            "cstree.positions_by_rebalance",
            "positions_by_rebalance.csv",
            "quant-execution-engine.targets/v2",
            "targets.json.lineage.json",
        ):
            self.assertIn(phrase, contracts)

    def test_strategy_satellites_preserve_stage3_core_chain(self) -> None:
        satellites = (ROOT / "docs" / "strategy-satellites.md").read_text(encoding="utf-8")

        self.assertNotIn(
            "`market-data-platform` → `strategy-pipeline` → `quant-execution-engine`",
            satellites,
        )
        for phrase in (
            "`market-data-platform` → `alpha-research`",
            "`portfolio-backtester` → `strategy-pipeline`",
            "signals.parquet + signals.meta.json",
            "positions_by_rebalance.csv + backtest evidence",
            "targets.json + targets.json.lineage.json",
            "五段核心架构",
        ):
            self.assertIn(phrase, satellites)


if __name__ == "__main__":
    unittest.main()
