from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hk_strategy_demo.allocation import build_targets, select_top  # noqa: E402
from hk_strategy_demo.data import load_prices  # noqa: E402
from hk_strategy_demo.pipeline import run_demo  # noqa: E402
from hk_strategy_demo.research import Score, rank_trailing_returns  # noqa: E402


class UnitTest(unittest.TestCase):
    def test_load_prices_sorts_rows(self) -> None:
        prices = load_prices(ROOT / "fixtures" / "synthetic_prices.csv")
        self.assertEqual(["00005.HK", "00700.HK", "00941.HK"], sorted(prices))
        self.assertEqual("2026-05-27", prices["00005.HK"][0][0])

    def test_rank_trailing_returns_uses_symbol_tie_break(self) -> None:
        ranked = rank_trailing_returns(
            {
                "00700.HK": [("2026-05-27", 10.0), ("2026-05-29", 11.0)],
                "00005.HK": [("2026-05-27", 20.0), ("2026-05-29", 22.0)],
            }
        )
        self.assertEqual(["00005.HK", "00700.HK"], [row.symbol for row in ranked])

    def test_select_top_rejects_invalid_top_n(self) -> None:
        with self.assertRaisesRegex(ValueError, "top_n must be positive"):
            select_top([Score(symbol="00005.HK", score=0.1)], 0)

    def test_targets_use_equal_weights_and_standard_market(self) -> None:
        targets = build_targets(
            [
                Score(symbol="00005.HK", score=0.1),
                Score(symbol="00700.HK", score=0.2),
            ],
            asof="2026-05-29",
        )
        rows = cast("list[dict[str, object]]", targets["targets"])
        self.assertEqual(0.5, rows[0]["target_weight"])
        self.assertTrue(all(row["market"] == "HK" for row in rows))

    def test_run_demo_preserves_schema_versions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_demo(ROOT / "fixtures" / "synthetic_prices.csv", tmp)
        self.assertEqual("hk_strategy_demo.summary.v1", result["summary"]["schema_version"])
        self.assertEqual("hk-cross-sectional-strategy-demo", result["targets"]["source"])


if __name__ == "__main__":
    unittest.main()
