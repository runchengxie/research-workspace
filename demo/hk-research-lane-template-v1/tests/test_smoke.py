import json
from pathlib import Path

from hk_cstree import run_smoke


def test_synthetic_hk_research_smoke(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]

    result = run_smoke(root / "fixtures" / "synthetic_hk_prices.csv", tmp_path)

    targets = json.loads(result["targets_path"].read_text(encoding="utf-8"))
    assert result["summary"]["synthetic_only"] is True
    assert result["summary"]["target_contract"] == "quant-execution-engine.targets/v2"
    assert targets["targets"]
    assert {row["market"] for row in targets["targets"]} == {"HK"}
