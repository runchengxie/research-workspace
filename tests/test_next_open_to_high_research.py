from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from tests._next_open_shared import (
    BACKTEST,
    MINUTE_AUDIT,
    _flat_session_bars,
    _minute_candidate,
)


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
