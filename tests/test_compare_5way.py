from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "strategy-research" / "experiments" / "qlib_pilot" / "compare_5way.py"
SPEC = importlib.util.spec_from_file_location("compare_5way", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
compare_5way = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compare_5way)


def _daily_row(
    trade_date: str,
    symbol: str,
    pct_chg: float,
    *,
    listed_days: int = 100,
) -> dict[str, object]:
    pre_close = 10.0
    return {
        "trade_date": trade_date,
        "symbol": symbol,
        "pct_chg": pct_chg,
        "close": pre_close * (1 + pct_chg / 100),
        "pre_close": pre_close,
        "listed_days": listed_days,
        "is_suspended": False,
    }


def test_effective_rebalance_dates_apply_membership_after_rebalance() -> None:
    mapping = compare_5way._effective_rebalance_dates(
        pd.Series(["20200102", "20200103", "20200106", "20200107"]),
        pd.Series(["20200102", "20200106"]),
    )

    assert mapping.to_dict("records") == [
        {"trade_date": "20200103", "rebalance_date": "20200102"},
        {"trade_date": "20200106", "rebalance_date": "20200102"},
        {"trade_date": "20200107", "rebalance_date": "20200106"},
    ]


def test_equal_weight_top800_uses_pit_membership_and_zero_for_suspension(
    tmp_path: Path,
) -> None:
    universe = pd.DataFrame(
        [
            {"trade_date": "20200102", "symbol": "A", "liq_metric": 100.0},
            {"trade_date": "20200102", "symbol": "B", "liq_metric": 90.0},
            {"trade_date": "20200102", "symbol": "C", "liq_metric": 80.0},
            {"trade_date": "20200106", "symbol": "B", "liq_metric": 100.0},
            {"trade_date": "20200106", "symbol": "C", "liq_metric": 90.0},
            {"trade_date": "20200106", "symbol": "A", "liq_metric": 80.0},
        ]
    )
    universe_path = tmp_path / "universe.csv"
    universe.to_csv(universe_path, index=False)

    daily_dir = tmp_path / "daily"
    daily_dir.mkdir()
    rows = {
        "A": [
            _daily_row("20200102", "A", 0.0),
            _daily_row("20200106", "A", 20.0),
            _daily_row("20200107", "A", 0.0),
        ],
        "B": [
            _daily_row("20200102", "B", 0.0),
            _daily_row("20200103", "B", 0.0),
            _daily_row("20200106", "B", 0.0),
            _daily_row("20200107", "B", 0.0),
        ],
        "C": [
            _daily_row("20200102", "C", 0.0),
            _daily_row("20200103", "C", 0.0),
            _daily_row("20200106", "C", 0.0),
            _daily_row("20200107", "C", 30.0),
        ],
    }
    for symbol, records in rows.items():
        pd.DataFrame(records).to_parquet(daily_dir / f"{symbol}.parquet", index=False)

    returns = compare_5way.series_equal_weight_top800(
        str(universe_path),
        str(daily_dir),
        "20200102",
        "20200107",
        top_n=2,
        min_listed_days=60,
        max_workers=2,
    )

    assert returns.index.strftime("%Y%m%d").tolist() == [
        "20200103",
        "20200106",
        "20200107",
    ]
    assert returns.tolist() == pytest.approx([0.0, 0.10, 0.15])
    assert returns.attrs["missing_return_rows_filled_zero"] == 1
    assert returns.attrs["membership_effective"] == "next_trading_day"
