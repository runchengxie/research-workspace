from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
EXPECTED_SUBMODULES = {
    "market-data-platform",
    "cross-sectional-trees",
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


if __name__ == "__main__":
    unittest.main()
