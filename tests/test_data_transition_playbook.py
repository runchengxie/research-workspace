from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "docs" / "data-transition-playbook.md"


class DataTransitionPlaybookTest(unittest.TestCase):
    def test_playbook_records_current_priority_order(self) -> None:
        text = PLAYBOOK.read_text(encoding="utf-8")
        required = [
            "截至 2026-06-01，A 股中期窗口数据已发布，港股转入冷存储",
            "DATA_PLATFORM_ROOT",
            "metadata/current_assets/hk_current.json",
            "metadata/current_assets/a_share_current.json",
            "metadata/frozen_markets/hk.json",
            "metadata/dataset_registry.csv",
            "metadata/current_assets/cn_current.json",
            "marketdata rqdata inspect-hk-current",
            "marketdata migration freeze-hk",
            "marketdata migration hydrate-hk",
            "marketdata tushare validate-a-share-daily-clean",
            "cstree run --config default_next",
            "qexec rebalance",
            "FX_CNY_USD",
        ]
        for phrase in required:
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
