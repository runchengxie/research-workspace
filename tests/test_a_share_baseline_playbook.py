from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "playbooks" / "a-share-baseline.md"


def test_a_share_baseline_playbook_records_current_boundaries() -> None:
    text = DOCUMENT.read_text(encoding="utf-8")

    assert "`market-data-platform`" in text
    assert "`alpha-research`" in text
    assert "`portfolio-backtester`" in text
    assert "`strategy-app`" in text
    assert "`strategy-pipeline`" in text
    assert "`baseline_reproducible`" in text
    assert "`production_strategy_evidence`" in text
    assert "`config.used.yml`" in text


def test_a_share_baseline_playbook_is_indexed() -> None:
    index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    assert "[playbooks/a-share-baseline.md](playbooks/a-share-baseline.md)" in index
