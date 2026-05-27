from __future__ import annotations

import configparser
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PATHS = {
    "market-data-platform",
    "cross-sectional-trees",
    "rqdata-hk-depth-snapshots",
    "quant-execution-engine",
}


class GitmodulesTest(unittest.TestCase):
    def test_expected_submodules_are_registered(self) -> None:
        parser = configparser.ConfigParser()
        parser.read(ROOT / ".gitmodules", encoding="utf-8")
        paths = {parser.get(section, "path") for section in parser.sections()}
        self.assertEqual(EXPECTED_PATHS, paths)

    def test_submodule_urls_use_https(self) -> None:
        parser = configparser.ConfigParser()
        parser.read(ROOT / ".gitmodules", encoding="utf-8")
        for section in parser.sections():
            url = parser.get(section, "url")
            self.assertTrue(url.startswith("https://"), section)

    def test_readme_mentions_each_submodule(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for path in EXPECTED_PATHS:
            self.assertIn(path, readme)


if __name__ == "__main__":
    unittest.main()
