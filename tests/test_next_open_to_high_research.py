from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest


def _load_research_module(filename: str, module_name: str):
    research_dir = (
        Path(__file__).resolve().parents[1]
        / "strategy-research"
        / "experiments"
        / "next_open_to_high"
    )
    module_path = research_dir / filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    sys.path.insert(0, str(research_dir))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(research_dir))
    return module


BACKTEST = _load_research_module(
    "a_share_next_open_to_high_backtest.py",
    "a_share_next_open_to_high_backtest_for_tests",
)
MINUTE_AUDIT = _load_research_module(
    "a_share_next_open_to_high_minute_audit.py",
    "a_share_next_open_to_high_minute_audit_for_tests",
)


def _session_times(date: str) -> pd.DatetimeIndex:
    day = pd.Timestamp(date)
    morning = pd.date_range(day + pd.Timedelta(hours=9, minutes=30), periods=121, freq="min")
    afternoon = pd.date_range(day + pd.Timedelta(hours=13, minutes=1), periods=120, freq="min")
    return pd.DatetimeIndex(morning.append(afternoon))


def _flat_session_bars(date: str = "2026-01-06") -> pd.DataFrame:
    times = _session_times(date)
    return pd.DataFrame(
        {
            "trade_time": times,
            "open": [10.0] * len(times),
            "high": [10.1] * len(times),
            "low": [9.9] * len(times),
            "close": [10.0] * len(times),
            "amount": [100.0] * len(times),
        }
    )


def _minute_candidate(**overrides: object) -> pd.Series:
    values: dict[str, Any] = {
        "signal_date": pd.Timestamp("2026-01-05"),
        "entry_date": pd.Timestamp("2026-01-06"),
        "symbol": "000001.SZ",
        "execution_eligible": True,
        "exec_next_up_limit": 11.0,
        "exec_next_down_limit": 9.0,
    }
    values.update(overrides)
    return pd.Series(values)


def test_full_day_outcome_is_not_used_to_decide_entry_eligibility() -> None:
    frame = pd.DataFrame(
        {
            "exec_next_trade_date": [pd.Timestamp("2026-01-06")],
            "market_next_date": [pd.Timestamp("2026-01-06")],
            "next_adj_open": [10.0],
            "next_adj_high": [np.nan],
            "next_adj_close": [np.nan],
            "exec_next_amount": [0.0],
            "exec_next_is_suspended": [False],
            "exec_next_is_st": [False],
            "exec_next_open": [10.0],
            "exec_next_up_limit": [11.0],
        }
    )

    result = BACKTEST.add_execution_fields(frame, block_limit_up_open=True).iloc[0]

    assert bool(result["execution_eligible"])
    assert not bool(result["outcome_available"])
    assert not bool(result["evaluation_eligible"])


@pytest.mark.parametrize(
    ("raw_open", "up_limit"),
    [(np.nan, 11.0), (10.0, np.nan), (10.0, 99999.999)],
)
def test_daily_entry_fails_closed_without_valid_raw_open_and_limit(
    raw_open: float, up_limit: float
) -> None:
    frame = pd.DataFrame(
        {
            "exec_next_trade_date": [pd.Timestamp("2026-01-06")],
            "market_next_date": [pd.Timestamp("2026-01-06")],
            "next_adj_open": [10.0],
            "next_adj_high": [10.5],
            "next_adj_close": [10.2],
            "exec_next_amount": [1_000.0],
            "exec_next_is_suspended": [False],
            "exec_next_is_st": [False],
            "exec_next_open": [raw_open],
            "exec_next_up_limit": [up_limit],
        }
    )

    result = BACKTEST.add_execution_fields(frame, block_limit_up_open=True).iloc[0]

    assert not bool(result["entry_limit_available"])
    assert not bool(result["execution_eligible"])


def test_loader_retains_signal_row_without_next_day_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-05"]),
            "symbol": ["000001.SZ", "000001.SZ", "600000.SH"],
            "open": [10.0, 11.0, 8.0],
            "high": [10.5, 12.0, 8.5],
            "low": [9.8, 10.8, 7.8],
            "close": [10.2, 11.5, 8.2],
            "pre_close": [10.0, 11.0, 8.0],
            "amount": [1_000.0, 1_100.0, 900.0],
            "total_mv": [10_000.0, 10_500.0, 20_000.0],
            "turnover_rate": [2.0, 2.1, 1.5],
            "is_suspended": [False, False, False],
            "is_st": [False, False, False],
            "listed_days": [100, 101, 100],
            "up_limit": [11.0, 12.1, 8.8],
            "board": ["main", "main", "main"],
            "next_adj_open": [11.0, np.nan, np.nan],
            "next_adj_high": [12.0, np.nan, np.nan],
            "next_adj_close": [11.5, np.nan, np.nan],
            "next_open_to_high": [12.0 / 11.0 - 1.0, np.nan, np.nan],
        }
    )
    monkeypatch.setattr(BACKTEST, "load_daily_clean", lambda *args, **kwargs: raw.copy())
    monkeypatch.setattr(BACKTEST, "add_labels_and_features", lambda frame: frame.copy())
    args = Namespace(
        start_date="2026-01-05",
        end_date="2026-01-06",
        max_symbols=0,
        markets=["SH", "SZ"],
        target="next_open_to_high",
        block_limit_up_open=True,
    )

    _, panel = BACKTEST._load_execution_panel(args, Path("."))
    missing_outcome = panel.loc[
        panel["trade_date"].eq(pd.Timestamp("2026-01-05")) & panel["symbol"].eq("600000.SH")
    ].iloc[0]

    assert missing_outcome["entry_date"] == pd.Timestamp("2026-01-06")
    assert pd.isna(missing_outcome["observed_next_trade_date"])
    assert not bool(missing_outcome["outcome_available"])
    assert not bool(missing_outcome["execution_eligible"])


def test_topk_is_frozen_before_open_and_unfilled_name_is_not_backfilled() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-05"] * 3),
            "symbol": ["000001.SZ", "600000.SH", "000002.SZ"],
            "pred": [3.0, 2.0, 1.0],
            "entry_date": pd.to_datetime(["2026-01-06"] * 3),
            "execution_eligible": [False, True, True],
            "blocked_limit_up_open": [True, False, False],
        }
    )

    selected, daily = BACKTEST.select_daily_candidates(frame, top_k=2)

    assert selected["symbol"].tolist() == ["000001.SZ", "600000.SH"]
    assert daily.loc[0, "filled"] == 1
    assert daily.loc[0, "max_raw_rank_used"] == 2.0


def test_daily_ohlc_proxy_requires_strict_take_profit_cross() -> None:
    selected = pd.DataFrame(
        {
            "symbol": ["000001.SZ"],
            "entry_price": [10.0],
            "next_high_price": [10.8],
            "next_close_price": [10.5],
            "next_amount_cny": [1_000_000.0],
        }
    )

    result = BACKTEST.apply_exit_policy(
        selected,
        take_profit_pct=0.08,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
        participation_rate=0.05,
    )

    assert not bool(result.loc[0, "hit_take_profit"])
    assert result.loc[0, "exit_reason"] == "close"
    assert result.loc[0, "gross_return"] == pytest.approx(0.05)


def test_zero_fill_day_is_retained_as_cash() -> None:
    trades = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-05"]),
            "entry_date": pd.to_datetime(["2026-01-06"]),
            "top_k": [2],
            "exit_policy": ["close"],
            "symbol": ["000001.SZ"],
            "net_return": [0.01],
            "gross_return": [0.012],
            "hit_take_profit": [False],
            "open_to_high": [0.02],
            "open_to_close": [0.012],
            "capacity_cny": [1_000_000.0],
            "raw_rank": [1],
        }
    )
    daily_selection = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-05", "2026-01-06"]),
            "entry_date": pd.to_datetime(["2026-01-06", "2026-01-07"]),
            "top_k": [2, 2],
            "raw_executable": [1, 0],
            "fill_rate": [0.5, 0.0],
            "selection_turnover": [1.0, 1.0],
            "blocked_limit_up_open_raw": [1, 2],
        }
    )

    result = BACKTEST.aggregate_daily_returns(trades, daily_selection)
    cash_day = result.loc[result["signal_date"].eq(pd.Timestamp("2026-01-06"))].iloc[0]

    assert cash_day["filled"] == 0
    assert cash_day["portfolio_return"] == 0.0
    assert cash_day["cash_weight"] == 1.0

    stress = BACKTEST.summarize_cost_stress(trades, [22.0], daily_selection)
    assert stress.loc[0, "days"] == 2


def test_minute_audit_retains_all_missing_day_as_cash() -> None:
    trades = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-05"] * 2),
            "entry_date": pd.to_datetime(["2026-01-06"] * 2),
            "symbol": ["000001.SZ", "600000.SH"],
            "status": ["minute_missing", "signal_unfilled"],
            "net_return": [np.nan, np.nan],
        }
    )

    result = MINUTE_AUDIT._daily_returns(trades, top_k=2)

    assert len(result) == 1
    assert result.loc[0, "audited_names"] == 0
    assert result.loc[0, "portfolio_return"] == 0.0
    assert result.loc[0, "cash_weight"] == 1.0


def test_empty_symbol_day_does_not_invoke_arrow_filter(tmp_path: Path) -> None:
    result = MINUTE_AUDIT._load_day(tmp_path / "missing.parquet", [])

    assert result.empty
    assert set(result.columns) == {
        "ts_code",
        "trade_time",
        "open",
        "high",
        "low",
        "close",
        "vol",
        "amount",
    }


def test_split_filters_training_labels_but_retains_test_ranking_universe() -> None:
    panel = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2025-12-30", "2025-12-31", "2026-01-05", "2026-01-06"]),
            "symbol": ["000001.SZ"] * 4,
            "same_next_session": [True, True, True, True],
            "outcome_available": [True, True, False, True],
            "next_open_to_high": [0.01, 0.02, np.nan, 0.03],
            "entry_date": pd.to_datetime(["2025-12-31", "2026-01-05", "2026-01-06", "2026-01-07"]),
        }
    )
    args = Namespace(
        train_end="2025-12-31",
        train_sample_per_date=0,
        random_state=42,
        target="next_open_to_high",
    )

    train, train_sample, test = BACKTEST._split_panel(panel, args)

    assert train["trade_date"].dt.strftime("%Y%m%d").tolist() == ["20251230"]
    assert train["entry_date"].max() <= pd.Timestamp(args.train_end)
    assert train_sample.equals(train)
    assert test["trade_date"].dt.strftime("%Y%m%d").tolist() == ["20260105", "20260106"]


def test_default_market_universe_excludes_bse() -> None:
    parser = BACKTEST.build_parser()

    assert parser.parse_args([]).markets == ["SH", "SZ"]
    with pytest.raises(SystemExit):
        parser.parse_args(["--markets", "SH,US"])


def test_minute_audit_requires_later_bar_to_cross_target() -> None:
    bars = _flat_session_bars()
    bars.loc[2, ["open", "high", "low", "close"]] = [10.5, 10.8, 10.4, 10.7]
    bars.loc[3, ["open", "high", "low", "close"]] = [10.7, 10.81, 10.6, 10.8]
    candidate = _minute_candidate()

    strict = MINUTE_AUDIT.audit_candidate(
        candidate,
        bars,
        entry_bar_index=1,
        take_profit_pct=0.08,
        strict_cross=True,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
        participation_rate=0.05,
    )
    touch = MINUTE_AUDIT.audit_candidate(
        candidate,
        bars,
        entry_bar_index=1,
        take_profit_pct=0.08,
        strict_cross=False,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
        participation_rate=0.05,
    )

    assert strict["exit_time"] == pd.Timestamp("2026-01-06 09:33")
    assert touch["exit_time"] == pd.Timestamp("2026-01-06 09:32")
    assert strict["gross_return"] == pytest.approx(0.08)


@pytest.mark.parametrize(
    ("candidate_overrides", "entry_amount", "expected_reason"),
    [
        ({"exec_next_up_limit": 10.0}, 100.0, "limit_up_0931"),
        ({}, 0.0, "nonpositive_entry_amount"),
        ({"exec_next_up_limit": np.nan}, 100.0, "missing_or_invalid_up_limit"),
    ],
)
def test_minute_entry_fail_closed_when_not_demonstrably_tradable(
    candidate_overrides: dict[str, Any],
    entry_amount: float,
    expected_reason: str,
) -> None:
    bars = _flat_session_bars()
    bars.loc[1, "amount"] = entry_amount

    result = MINUTE_AUDIT.audit_candidate(
        _minute_candidate(**candidate_overrides),
        bars,
        entry_bar_index=1,
        take_profit_pct=0.08,
        strict_cross=True,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
        participation_rate=0.05,
    )

    assert result["status"] == "minute_entry_blocked"
    assert expected_reason in result["entry_block_reasons"]
    assert np.isnan(result["net_return"])


def test_signal_unfilled_keeps_daily_gate_reason() -> None:
    result = MINUTE_AUDIT.audit_candidate(
        _minute_candidate(
            execution_eligible=False,
            entry_limit_available=False,
            blocked_limit_up_open=False,
        ),
        pd.DataFrame(),
        entry_bar_index=1,
        take_profit_pct=0.08,
        strict_cross=True,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
        participation_rate=0.05,
    )

    assert result["status"] == "signal_unfilled"
    assert result["signal_unfilled_reasons"] == "daily_missing_or_invalid_open_limit"


def test_minute_close_at_down_limit_is_diagnosed_but_marked_to_close() -> None:
    bars = _flat_session_bars()
    bars.loc[len(bars) - 1, ["open", "high", "low", "close"]] = [9.0, 9.0, 9.0, 9.0]

    result = MINUTE_AUDIT.audit_candidate(
        _minute_candidate(),
        bars,
        entry_bar_index=1,
        take_profit_pct=0.08,
        strict_cross=True,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
        participation_rate=0.05,
    )

    assert result["status"] == "audited"
    assert result["exit_reason"] == "close"
    assert result["close_exit_at_down_limit"]
    assert result["net_return"] == pytest.approx(-0.10)


def test_guan_sparse_full_day_uses_exact_entry_and_close_timestamps() -> None:
    bars = _flat_session_bars().drop(index=[0, 50, 238, 239]).reset_index(drop=True)

    guan = MINUTE_AUDIT.audit_candidate(
        _minute_candidate(),
        bars,
        entry_bar_index=1,
        take_profit_pct=0.08,
        strict_cross=True,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
        participation_rate=0.05,
        minute_source="guan_deal",
    )
    tushare = MINUTE_AUDIT.audit_candidate(
        _minute_candidate(),
        bars,
        entry_bar_index=1,
        take_profit_pct=0.08,
        strict_cross=True,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
        participation_rate=0.05,
        minute_source="tushare_full_day",
    )

    assert guan["status"] == "audited"
    assert guan["entry_time"] == pd.Timestamp("2026-01-06 09:31")
    assert guan["exit_time"] == pd.Timestamp("2026-01-06 15:00")
    assert tushare["status"] == "minute_incomplete"


def test_minute_audit_leaves_incomplete_session_in_cash() -> None:
    bars = pd.DataFrame(
        {
            "trade_time": pd.to_datetime(["2026-01-06 09:30", "2026-01-06 09:31"]),
            "open": [10.0, 10.0],
            "high": [10.1, 10.1],
            "low": [9.9, 9.9],
            "close": [10.0, 10.0],
            "amount": [100.0, 100.0],
        }
    )
    candidate = pd.Series(
        {
            "signal_date": pd.Timestamp("2026-01-05"),
            "entry_date": pd.Timestamp("2026-01-06"),
            "symbol": "000001.SZ",
            "execution_eligible": True,
        }
    )

    result = MINUTE_AUDIT.audit_candidate(
        candidate,
        bars,
        entry_bar_index=1,
        take_profit_pct=0.08,
        strict_cross=True,
        entry_slippage_bps=0.0,
        exit_slippage_bps=0.0,
        round_trip_cost_bps=0.0,
        participation_rate=0.05,
    )

    assert result["status"] == "minute_incomplete"
    assert np.isnan(result["net_return"])


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
