from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "metric-ownership.md"


def test_metric_ownership_document_records_current_public_owners() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    assert "`alpha_research.metrics`" in text
    assert "`portfolio-backtester`" in text
    assert "`strategy-pipeline`" in text
    assert "`summarize_period_returns`" in text
    assert "`deflated_sharpe_ratio`" in text


def test_metric_ownership_document_is_linked_from_docs_index() -> None:
    index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    assert "[metric-ownership.md](metric-ownership.md)" in index
