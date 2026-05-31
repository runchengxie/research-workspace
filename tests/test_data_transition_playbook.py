from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "docs" / "data-transition-playbook.md"


class DataTransitionPlaybookTest(unittest.TestCase):
    def test_playbook_records_current_priority_order(self) -> None:
        text = PLAYBOOK.read_text(encoding="utf-8")
        required = [
            "当前不建议直接开始 A 股完整数据下载",
            "DATA_PLATFORM_ROOT",
            "metadata/current_assets/hk_current.json",
            "metadata/current_assets/a_share_current.json",
            "metadata/dataset_registry.csv",
            "metadata/current_assets/cn_current.json",
            "marketdata rqdata inspect-hk-current",
            "marketdata tushare validate-a-share-daily-clean",
            "cstree run --config default_next",
            "qexec rebalance",
            "FX_CNY_USD",
        ]
        for phrase in required:
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
