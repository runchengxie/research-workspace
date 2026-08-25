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
    "niu_men_line",
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

    # 生产资格是 catalog 中显式声明的 metadata 字段，不是代码位置。
    # 截至 2026-08-17，所有策略的生产证据均未达标（capacity/turnover_cost
    # 为 pending、final OOS 为书面替代、broker operational_approval=false），
    # 因此没有策略被标记为 production_eligible，包括曾错误标记的 daily_watch20。
    production = [item for item in strategies if item["production_eligible"]]
    assert production == []

    daily_watch20 = next(item for item in strategies if item["id"] == "daily_watch20")
    assert daily_watch20["production_eligible"] is False
    assert daily_watch20["control_plane_owner"] == "strategy-pipeline"
    assert daily_watch20["human_spec"].startswith("strategy-research/")
    assert "strategy-app" in daily_watch20["executable_owners"]


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
