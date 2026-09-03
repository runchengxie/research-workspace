from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "strategy-catalog.md"


def test_strategy_catalog_documents_current_owners_and_migration_status() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    assert "`strategy-research`" in text
    assert "`strategy-app`" in text
    assert "`strategy-pipeline`" in text
    assert "`quant-execution-engine`" in text
    assert "`strategy-pipeline-internal`" in text
    assert "targets.json" in text


def test_strategy_catalog_links_the_migration_manifest() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    assert "migrations/strategy-pipeline-internal-migration-manifest.md" in text
