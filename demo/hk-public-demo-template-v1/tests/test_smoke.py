from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hk_strategy_demo.pipeline import run_demo  # noqa: E402


class SmokeTest(unittest.TestCase):
    def test_synthetic_workflow_generates_summary_and_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_demo(ROOT / "fixtures" / "synthetic_prices.csv", tmp)
            summary = json.loads(Path(result["summary_path"]).read_text(encoding="utf-8"))
            targets = json.loads(Path(result["targets_path"]).read_text(encoding="utf-8"))

        self.assertEqual("passed", summary["status"])
        self.assertEqual("synthetic_fixture_only", summary["data_policy"])
        self.assertEqual(2, len(targets["targets"]))
        self.assertTrue(all(row["market"] == "HK" for row in targets["targets"]))


if __name__ == "__main__":
    unittest.main()
