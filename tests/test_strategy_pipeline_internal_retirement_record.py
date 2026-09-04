from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "docs" / "migrations" / "strategy-pipeline-internal-retirement-record.md"


def test_retirement_record_starts_at_the_post_freeze_baseline() -> None:
    text = RECORD.read_text(encoding="utf-8")

    assert "> status: pre-retirement-baseline" in text
    assert "> audit_date: 2026-09-05" in text
    assert "internal 最后可用提交" in text
    assert "strategy-research 已记录 internal runner 路径为 archive-only" in text
    assert "维护周期计数为 0/2" in text
    assert "不能替代正式下线评审" in text
