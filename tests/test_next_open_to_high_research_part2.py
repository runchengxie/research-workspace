from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tests._next_open_shared import (
    BACKTEST,
    MINUTE_AUDIT,
    _flat_session_bars,
    _session_times,
)


def test_same_entry_benchmark_keeps_unavailable_names_as_cash() -> None:
    candidates = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-05"] * 3),
            "entry_date": pd.to_datetime(["2026-01-06"] * 3),
            "symbol": ["000001.SZ", "600000.SH", "000002.SZ"],
            "execution_eligible": [True, True, False],
            "exec_next_up_limit": [11.0, 11.0, 11.0],
            "exec_next_down_limit": [9.0, 9.0, 9.0],
        }
    )
    times = _session_times("2026-01-06")
    minute = pd.DataFrame(
        {
            "ts_code": ["000001.SZ"] * len(times),
            "trade_time": times,
            "open": [10.0] * len(times),
            "high": [10.1] * len(times),
            "low": [9.9] * len(times),
            "close": [10.0] * len(times),
            "amount": [100.0] * len(times),
        }
    )
    minute.loc[2, ["open", "high", "low", "close"]] = [10.5, 10.9, 10.4, 10.8]

    result, _ = MINUTE_AUDIT.audit_benchmark_day_with_bands(
        candidates,
        minute,
        entry_bar_index=1,
        take_profit_pct=0.08,
        strict_cross=True,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
    )

    assert result["benchmark_slots"] == 3
    assert result["benchmark_executable"] == 2
    assert result["benchmark_audited"] == 1
    assert result["benchmark_cash_weight"] == pytest.approx(2.0 / 3.0)
    assert result["benchmark_return"] == pytest.approx(0.08 / 3.0)


def test_same_entry_benchmark_fails_closed_without_up_limit() -> None:
    candidates = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-05"]),
            "entry_date": pd.to_datetime(["2026-01-06"]),
            "symbol": ["000001.SZ"],
            "execution_eligible": [True],
            "exec_next_up_limit": [np.nan],
            "exec_next_down_limit": [9.0],
        }
    )
    minute = _flat_session_bars().assign(ts_code="000001.SZ")

    result, _ = MINUTE_AUDIT.audit_benchmark_day_with_bands(
        candidates,
        minute,
        entry_bar_index=1,
        take_profit_pct=0.08,
        strict_cross=True,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
    )

    assert result["benchmark_audited"] == 0
    assert result["benchmark_entry_limit_unavailable"] == 1
    assert result["benchmark_cash_weight"] == 1.0
    assert result["benchmark_return"] == 0.0


def test_same_entry_benchmark_accepts_receipted_guan_sparse_grid() -> None:
    candidates = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-05"]),
            "entry_date": pd.to_datetime(["2026-01-06"]),
            "symbol": ["000001.SZ"],
            "execution_eligible": [True],
            "exec_next_up_limit": [11.0],
            "exec_next_down_limit": [9.0],
        }
    )
    minute = (
        _flat_session_bars()
        .drop(index=[0, 50, 238, 239])
        .reset_index(drop=True)
        .assign(ts_code="000001.SZ")
    )

    guan, _ = MINUTE_AUDIT.audit_benchmark_day_with_bands(
        candidates,
        minute,
        entry_bar_index=1,
        take_profit_pct=0.08,
        strict_cross=True,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
        minute_source="guan_deal",
    )
    tushare, _ = MINUTE_AUDIT.audit_benchmark_day_with_bands(
        candidates,
        minute,
        entry_bar_index=1,
        take_profit_pct=0.08,
        strict_cross=True,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
        minute_source="tushare_full_day",
    )

    assert guan["benchmark_audited"] == 1
    assert tushare["benchmark_audited"] == 0


def test_active_return_uses_exposure_matched_same_entry_benchmark() -> None:
    selected = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-05"]),
            "entry_date": pd.to_datetime(["2026-01-06"]),
            "portfolio_return": [0.02],
            "cash_weight": [0.5],
        }
    )
    benchmark = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-05"]),
            "entry_date": pd.to_datetime(["2026-01-06"]),
            "benchmark_return": [0.009],
            "benchmark_executed_mean_return": [0.01],
        }
    )

    result = MINUTE_AUDIT.attach_exposure_matched_benchmark(selected, benchmark)

    assert result.loc[0, "benchmark_exposure_matched_return"] == pytest.approx(0.005)
    assert result.loc[0, "active_return"] == pytest.approx(0.015)


def test_signal_limit_band_is_based_only_on_signal_day_prices() -> None:
    frame = pd.DataFrame(
        {
            "pre_close": [10.0, 10.0, 10.0, np.nan],
            "up_limit": [10.5, 11.0, 12.0, np.nan],
        }
    )

    result = BACKTEST.add_signal_limit_band(frame)

    assert result["limit_band"].tolist() == ["05pct", "10pct", "20pct", "unknown"]


def test_daily_benchmark_retains_zero_execution_day_as_cash() -> None:
    test = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-05"] * 2),
            "symbol": ["000001.SZ", "600000.SH"],
            "evaluation_eligible": [False, False],
        }
    )
    args = Namespace(
        take_profit_pct=[0.08],
        include_close_exit=False,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
        participation_rate=0.05,
    )

    result = BACKTEST.matched_universe_benchmark(test, args, BACKTEST.apply_exit_policy)

    assert len(result) == 1
    assert result.loc[0, "benchmark_slots"] == 2
    assert result.loc[0, "benchmark_executed"] == 0
    assert result.loc[0, "benchmark_return"] == 0.0


def test_limit_band_benchmark_matches_selected_audited_band_weights() -> None:
    selected_daily = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-05"]),
            "entry_date": pd.to_datetime(["2026-01-06"]),
            "portfolio_return": [0.02],
        }
    )
    trades = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-05"] * 2),
            "entry_date": pd.to_datetime(["2026-01-06"] * 2),
            "limit_band": ["20pct", "10pct"],
            "status": ["audited", "minute_missing"],
        }
    )
    benchmark_bands = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-05"] * 2),
            "entry_date": pd.to_datetime(["2026-01-06"] * 2),
            "limit_band": ["10pct", "20pct"],
            "benchmark_executed_mean_return": [0.03, 0.01],
        }
    )

    result = MINUTE_AUDIT.attach_limit_band_matched_benchmark(
        selected_daily, trades, benchmark_bands, top_k=2
    )

    assert result.loc[0, "benchmark_limit_band_matched_return"] == pytest.approx(0.005)
    assert result.loc[0, "within_band_active_return"] == pytest.approx(0.015)


def test_minute_audit_selection_loader_excludes_bse(tmp_path: Path) -> None:
    path = tmp_path / "selected.csv"
    pd.DataFrame(
        {
            "signal_date": ["2026-01-05"] * 3,
            "entry_date": ["2026-01-06"] * 3,
            "symbol": ["000001.SZ", "600000.SH", "920270.BJ"],
            "top_k": [20] * 3,
        }
    ).to_csv(path, index=False)
    args = Namespace(
        top_k=20,
        markets=["SH", "SZ"],
        start_date=None,
        end_date=None,
    )

    selections, legacy, load_audit = MINUTE_AUDIT._load_selections(path, args)

    assert selections["symbol"].tolist() == ["000001.SZ", "600000.SH"]
    assert legacy
    assert load_audit["audit_rows"] == 2


def test_minute_selection_loader_audits_nat_and_window_exclusions(tmp_path: Path) -> None:
    path = tmp_path / "selected.csv"
    pd.DataFrame(
        {
            "signal_date": ["2026-01-05", "2026-01-06", "2026-01-08"],
            "entry_date": ["2026-01-06", "not-a-date", "2026-01-09"],
            "symbol": ["000001.SZ", "600000.SH", "000002.SZ"],
            "top_k": [20] * 3,
        }
    ).to_csv(path, index=False)
    args = Namespace(
        top_k=20,
        markets=["SH", "SZ"],
        start_date="2026-01-06",
        end_date="2026-01-07",
    )

    selections, _, load_audit = MINUTE_AUDIT._load_selections(path, args)

    assert selections["symbol"].tolist() == ["000001.SZ"]
    assert load_audit == {
        "input_rows_after_policy_market": 3,
        "input_signal_days": 3,
        "invalid_entry_date_rows": 1,
        "before_start_rows": 0,
        "after_end_rows": 1,
        "after_end_signal_days": 1,
        "audit_rows": 1,
        "audit_signal_days": 1,
        "audit_entry_days": 1,
    }


def test_minute_selection_loader_rejects_more_than_fixed_top_k(tmp_path: Path) -> None:
    path = tmp_path / "selected.csv"
    pd.DataFrame(
        {
            "signal_date": ["2026-01-05"] * 3,
            "entry_date": ["2026-01-06"] * 3,
            "symbol": ["000001.SZ", "600000.SH", "000002.SZ"],
            "top_k": [2] * 3,
        }
    ).to_csv(path, index=False)
    args = Namespace(
        top_k=2,
        markets=["SH", "SZ"],
        start_date=None,
        end_date=None,
    )

    with pytest.raises(ValueError, match="exceeds fixed Top-K denominator"):
        MINUTE_AUDIT._load_selections(path, args)
