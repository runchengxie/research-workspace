from pathlib import Path

REFERENCE = (
    Path(__file__).parents[1]
    / "strategy-research"
    / "research"
    / "references"
    / "market_intel_entity_ids.md"
)


def test_market_intel_entity_reference_identifies_the_external_sibling_owner() -> None:
    text = REFERENCE.read_text(encoding="utf-8")

    assert "`market-intel`（外部兄弟仓库）" in text
    assert "market-intel（即 `market-data-platform` submodule）" not in text
    assert "权威定义在 `market-intel` 内维护" in text
