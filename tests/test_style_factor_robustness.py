from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.style_factors.robustness_backtest import (
    RobustnessConfig,
    build_constrained_robustness,
)
from src.style_factors.robustness_data import (
    _normalize_trade_dates,
    _require_unique,
    load_robustness_market_data,
)
from src.style_factors.robustness_execution import (
    attempt_pending_orders,
    simulate_leg,
    terminal_event_positions,
)


def test_normalize_trade_dates_accepts_compact_and_iso_values() -> None:
    frame = pd.DataFrame({"trade_date": ["20240102", "2024-01-03"]})

    result = _normalize_trade_dates(frame)

    assert result["trade_date"].tolist() == [
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-03"),
    ]


def test_robustness_loader_rejects_duplicate_market_grain() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")] * 2,
            "symbol": ["000001.SZ"] * 2,
        }
    )

    with pytest.raises(ValueError, match="duplicate"):
        _require_unique(frame, ["trade_date", "symbol"], label="daily_clean")


def test_robustness_loader_uses_dated_stock_st_not_daily_clean_latest_flag(
    tmp_path: Path,
) -> None:
    clean_dir = tmp_path / ("assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data")
    clean_dir.mkdir(parents=True)
    clean = pd.DataFrame(
        {
            "trade_date": ["20240102"],
            "symbol": ["000001.SZ"],
            "close": [10.0],
            "pct_chg": [1.0],
            "amount": [100.0],
            "total_mv": [1000.0],
            "pb": [1.0],
            "pe_ttm": [10.0],
            "turnover_rate": [1.0],
            "dv_ttm": [2.0],
            "ps_ttm": [3.0],
            "is_limit_up": [False],
            "is_limit_down": [False],
            "is_suspended": [False],
            "listed_days": [500],
        }
    )
    clean.to_parquet(clean_dir / "000001.SZ.parquet", index=False)
    universe_path = tmp_path / "assets/universe/a_share_all_full_by_date.csv"
    universe_path.parent.mkdir(parents=True)
    pd.DataFrame({"trade_date": [20240102], "symbol": ["000001.SZ"], "selected": [1]}).to_csv(
        universe_path, index=False
    )
    st_path = tmp_path / ("assets/tushare/a_share/stock_st/a_share_all_stock_st_latest.parquet")
    st_path.parent.mkdir(parents=True)
    pd.DataFrame({"trade_date": ["20240102"], "ts_code": ["000001.SZ"]}).to_parquet(
        st_path, index=False
    )
    instruments_path = tmp_path / (
        "assets/tushare/a_share/instruments/a_share_all_instruments_latest.parquet"
    )
    instruments_path.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "symbol": ["000001.SZ"],
            "list_status": ["L"],
            "list_date": ["19910403"],
            "delist_date": [None],
        }
    ).to_parquet(instruments_path, index=False)

    loaded = load_robustness_market_data(tmp_path, start_date="2024-01-01")

    assert list(loaded.st_history["symbol"]) == ["000001.SZ"]
    assert loaded.metadata["st_history_complete"] is False
    assert "is_st" not in loaded.daily_clean.columns


def test_pending_orders_retry_price_limit_blocked_entry_and_exit() -> None:
    weights = np.array([0.0, 1.0])
    target = np.array([1.0, 0.0])
    pending = np.array([True, True])
    tradable = np.array([True, True])

    weights, pending, traded, blocked_entry, blocked_exit = attempt_pending_orders(
        weights,
        target,
        pending,
        tradable=tradable,
        limit_up=np.array([True, False]),
        limit_down=np.array([False, True]),
        side="long",
    )

    assert traded == 0.0
    assert blocked_entry and blocked_exit
    assert pending.all()

    weights, pending, traded, blocked_entry, blocked_exit = attempt_pending_orders(
        weights,
        target,
        pending,
        tradable=tradable,
        limit_up=np.array([False, False]),
        limit_down=np.array([False, False]),
        side="long",
    )

    assert np.allclose(weights, target)
    assert not pending.any()
    assert traded == 2.0
    assert not blocked_entry and not blocked_exit


def test_delisting_event_maps_to_first_market_date_on_or_after_delist() -> None:
    instruments = pd.DataFrame({"symbol": ["A"], "delist_date": [pd.Timestamp("2024-01-06")]})
    trading_dates = pd.DatetimeIndex(["2024-01-05", "2024-01-08"])

    events = terminal_event_positions(instruments, trading_dates, {"A": 0})

    assert list(events) == [pd.Timestamp("2024-01-08")]
    assert events[pd.Timestamp("2024-01-08")].tolist() == [0]


def test_close_execution_starts_exposure_on_following_return_interval() -> None:
    dates = pd.DatetimeIndex(["2024-01-02", "2024-01-03"])
    returns = pd.DataFrame({"A": [0.10, 0.20]}, index=dates)
    matrices = (
        np.ones((2, 1), dtype=bool),
        np.zeros((2, 1), dtype=bool),
        np.zeros((2, 1), dtype=bool),
    )

    result = simulate_leg(
        returns,
        matrices,
        {dates[0]: {"A": 1.0}},
        {},
        side="long",
        terminal_return=-0.5,
    )

    assert result.returns.tolist() == [0.0, 0.20]
    assert result.traded_notional.tolist() == [1.0, 0.0]


def test_terminal_mark_liquidates_position_after_applying_stress_return() -> None:
    dates = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"])
    returns = pd.DataFrame({"A": [0.0, np.nan, 0.50]}, index=dates)
    matrices = (
        np.ones((3, 1), dtype=bool),
        np.zeros((3, 1), dtype=bool),
        np.zeros((3, 1), dtype=bool),
    )

    result = simulate_leg(
        returns,
        matrices,
        {dates[0]: {"A": 1.0}},
        {dates[1]: np.asarray([0], dtype=int)},
        side="long",
        terminal_return=-0.5,
    )

    assert result.returns.tolist() == [0.0, -0.5, 0.0]
    assert result.terminal_events == 1


def _small_robustness_frames() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, dict[str, pd.Series]],
]:
    dates = pd.bdate_range("2024-01-02", periods=70)
    formation_dates = pd.DatetimeIndex([dates[20], dates[40], dates[60]])
    symbols = [f"{index:06d}.SZ" for index in range(60)]
    market_rows = []
    factor_rows = []
    for symbol_number, symbol in enumerate(symbols):
        for day_number, date in enumerate(dates):
            market_rows.append(
                {
                    "trade_date": date,
                    "symbol": symbol,
                    "pct_chg": (symbol_number - 30) / 1000 + day_number / 10000,
                    "amount": 1000.0,
                    "is_limit_up": False,
                    "is_limit_down": False,
                    "listed_days": 500,
                }
            )
        for date in formation_dates:
            factor_rows.append(
                {
                    "trade_date": date,
                    "symbol": symbol,
                    "factor_size_z": float(symbol_number),
                }
            )
    daily_clean = pd.DataFrame(market_rows)
    factors = pd.DataFrame(factor_rows)
    universe = pd.DataFrame(
        [{"trade_date": date, "symbol": symbol} for date in formation_dates for symbol in symbols]
    )
    baseline_series = pd.Series(0.0001, index=dates[21:], name="size")
    baseline = {"size": {"long_short": baseline_series}}
    return factors, daily_clean, universe, baseline


def test_constrained_profile_charges_actual_turnover_costs() -> None:
    factors, daily_clean, universe, baseline = _small_robustness_frames()
    artifacts = build_constrained_robustness(
        factors,
        daily_clean,
        universe,
        pd.DataFrame(columns=["trade_date", "symbol"]),
        pd.DataFrame(columns=["symbol", "delist_date"]),
        baseline,
        config=RobustnessConfig(
            transaction_cost_bps=10.0,
            cost_scenarios_bps=(0.0, 10.0),
            delist_scenarios=(-0.5,),
        ),
    )

    gross = artifacts.gross_results["size"]["long_short"]
    net = artifacts.net_results["size"]["long_short"]
    costs = artifacts.net_results["size"]["transaction_cost"]
    assert np.allclose(net, gross - costs)
    assert costs.sum() > 0
    assert set(artifacts.comparison["profile"]) == {
        "raw_gross_matched_window",
        "constrained_gross",
        "constrained_net",
    }
