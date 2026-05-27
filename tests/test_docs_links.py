from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class DocsLinksTest(unittest.TestCase):
    def test_top_level_markdown_links_resolve(self) -> None:
        markdown_files = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
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
                    missing.append(f"{markdown.relative_to(ROOT)} -> {target}")
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
