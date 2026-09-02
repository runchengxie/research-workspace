from datetime import datetime

import pytest

from research_contracts.research_clock import ResearchClock, validate_research_clock


def valid_payload():
    return {
        "schema_version": "research.clock.v1",
        "timezone": "Asia/Shanghai",
        "information_cutoff_at": "2026-09-02T15:00:00+08:00",
        "signal_at": "2026-09-02T15:01:00+08:00",
        "decision_at": "2026-09-02T15:02:00+08:00",
        "earliest_order_at": "2026-09-03T09:15:00+08:00",
        "execution_window_start_at": "2026-09-03T09:30:00+08:00",
        "execution_window_end_at": "2026-09-03T10:00:00+08:00",
        "valuation_at": "2026-09-03T15:00:00+08:00",
        "timing_policy_id": "a-share.close-next-open.v1",
        "trading_calendar_ref": "sse-szse-20260902",
    }


def test_research_clock_round_trip():
    clock = ResearchClock.from_mapping(valid_payload())
    restored = ResearchClock.from_mapping(clock.to_mapping())
    assert restored == clock
    assert isinstance(clock.signal_at, datetime)


def test_research_clock_rejects_naive_datetime():
    payload = valid_payload()
    payload["signal_at"] = "2026-09-02T15:01:00"
    with pytest.raises(ValueError, match="signal_at must be timezone-aware"):
        ResearchClock.from_mapping(payload)


def test_research_clock_rejects_invalid_order():
    payload = valid_payload()
    payload["decision_at"] = "2026-09-02T14:59:00+08:00"
    with pytest.raises(ValueError, match="signal_at must be <= decision_at"):
        ResearchClock.from_mapping(payload)


def test_execution_aware_clock_requires_execution_window():
    payload = valid_payload()
    payload["execution_window_start_at"] = None
    with pytest.raises(ValueError, match="execution_window_start_at is required"):
        validate_research_clock(payload, require_execution=True)


def test_diagnostic_clock_allows_missing_execution_window():
    payload = valid_payload()
    payload["earliest_order_at"] = None
    payload["execution_window_start_at"] = None
    payload["execution_window_end_at"] = None
    clock = validate_research_clock(payload, require_execution=False)
    assert clock.execution_window_start_at is None
