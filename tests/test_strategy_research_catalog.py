from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "strategy-research" / "catalog.json"
EXPECTED_STRATEGIES = {
    "daily_watch20",
    "hotsector",
    "style_replica_a80_b20",
    "d11_h5_shadow",
    "dividend_growth_momentum",
    "next_open_to_high",
    "guan_weekly",
}


def _catalog() -> dict[str, object]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_strategy_catalog_is_complete_and_human_navigable() -> None:
    catalog = _catalog()
    assert catalog["schema_version"] == "strategy_research_catalog.v1"
    assert catalog["source_of_truth"] == "strategy-research"
    strategies = catalog["strategies"]
    assert isinstance(strategies, list)
    assert {item["id"] for item in strategies} == EXPECTED_STRATEGIES

    for item in strategies:
        human_spec = item["human_spec"]
        assert isinstance(human_spec, str)
        assert (ROOT / human_spec).is_file(), human_spec
        assert item["lifecycle"]
        assert isinstance(item["production_eligible"], bool)
        assert item["executable_owners"]
        assert "strategy-pipeline" not in item["executable_owners"]


def test_production_state_is_metadata_not_a_pipeline_code_location() -> None:
    strategies = _catalog()["strategies"]
    production = [item for item in strategies if item["production_eligible"]]

    assert [item["id"] for item in production] == ["daily_watch20"]
    assert production[0]["control_plane_owner"] == "strategy-pipeline"
    assert production[0]["human_spec"].startswith("strategy-research/")
    assert "strategy-app" in production[0]["executable_owners"]


def test_strategy_navigation_declares_the_three_layer_boundary() -> None:
    readme = (ROOT / "strategy-research" / "README.md").read_text(encoding="utf-8")
    adr = (ROOT / "docs" / "adr" / "0006-strategy-knowledge-and-runtime-boundaries.md").read_text(
        encoding="utf-8"
    )

    for owner in ("strategy-research", "strategy-app", "strategy-pipeline"):
        assert owner in readme
        assert owner in adr
    assert "代码位置不表达生命周期" in readme
    assert "不得留在 `strategy-app`" in adr
