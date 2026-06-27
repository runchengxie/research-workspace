from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "docs" / "data-transition-playbook.md"


class DataTransitionPlaybookTest(unittest.TestCase):
    def test_playbook_records_current_priority_order(self) -> None:
        text = PLAYBOOK.read_text(encoding="utf-8")
        required = [
            "DATA_PLATFORM_ROOT",
            "metadata/current_assets/a_share_current.json",
            "metadata/frozen_markets/hk.json",
            "metadata/dataset_registry.csv",
            "metadata/current_assets/cn_current.json",
            "marketdata migration freeze-hk",
            "marketdata migration hydrate-hk",
            "marketdata tushare validate-a-share-daily-clean",
            "cstree run --config default_next",
            "qexec rebalance",
            "FX_CNY_USD",
        ]
        for phrase in required:
            self.assertIn(phrase, text)

    def test_playbook_separates_baseline_holding_and_broker_readiness(self) -> None:
        text = PLAYBOOK.read_text(encoding="utf-8")
        required = [
            "A 股 baseline 持仓建议验收",
            "market-data-platform",
            "alpha-research",
            "portfolio-backtester",
            "cross-sectional-trees",
            "quant-execution-engine",
            "positions_current*.csv",
            "targets.json.lineage.json",
            "`market-data-platform` 不训练模型、不选择持仓",
            "不能推导\n`broker_trading_enabled`",
            "`production_strategy_evidence`",
        ]
        for phrase in required:
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
