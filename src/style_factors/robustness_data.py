"""Load the bounded data contract used by constrained style-factor robustness runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

DAILY_CLEAN_COLUMNS = [
    "trade_date",
    "symbol",
    "close",
    "pct_chg",
    "amount",
    "total_mv",
    "pb",
    "pe_ttm",
    "turnover_rate",
    "dv_ttm",
    "ps_ttm",
    "is_limit_up",
    "is_limit_down",
    "is_suspended",
    "listed_days",
]


@dataclass(frozen=True)
class RobustnessMarketData:
    """Frames and provenance required by the robustness backtest."""

    daily_clean: pd.DataFrame
    universe: pd.DataFrame
    st_history: pd.DataFrame
    instruments: pd.DataFrame
    metadata: dict[str, Any]


def _require_unique(frame: pd.DataFrame, keys: list[str], *, label: str) -> None:
    duplicates = frame.duplicated(keys, keep=False)
    if duplicates.any():
        sample = frame.loc[duplicates, keys].head(5).to_dict(orient="records")
        raise ValueError(f"{label} has duplicate {keys} keys; sample={sample}")


def _filter_date_window(
    frame: pd.DataFrame,
    *,
    start_date: str | pd.Timestamp | None,
    end_date: str | pd.Timestamp | None,
) -> pd.DataFrame:
    start = pd.to_datetime(start_date) if start_date is not None else None
    end = pd.to_datetime(end_date) if end_date is not None else None
    if start is not None:
        frame = frame[frame["trade_date"] >= start]
    if end is not None:
        frame = frame[frame["trade_date"] <= end]
    return frame.copy()


def _normalize_trade_dates(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    compact = (
        frame["trade_date"]
        .astype("string")
        .str.strip()
        .str.slice(0, 10)
        .str.replace("-", "", regex=False)
    )
    frame["trade_date"] = pd.to_datetime(
        compact,
        format="%Y%m%d",
        errors="coerce",
    )
    return frame.dropna(subset=["trade_date"])


def _load_daily_clean(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None,
    end_date: str | pd.Timestamp | None,
) -> pd.DataFrame:
    data_dir = data_root / "assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data"
    if not data_dir.is_dir():
        raise FileNotFoundError(f"daily_clean data directory not found: {data_dir}")
    frame = pd.read_parquet(data_dir, columns=DAILY_CLEAN_COLUMNS)
    frame = _normalize_trade_dates(frame)
    frame = _filter_date_window(frame, start_date=start_date, end_date=end_date)
    if frame.empty:
        raise ValueError("daily_clean is empty in the requested robustness window")
    _require_unique(frame, ["trade_date", "symbol"], label="daily_clean")
    return frame.sort_values(["trade_date", "symbol"]).reset_index(drop=True)


def _load_universe(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None,
    end_date: str | pd.Timestamp | None,
) -> pd.DataFrame:
    path = data_root / "assets/universe/a_share_all_full_by_date.csv"
    if not path.is_file():
        raise FileNotFoundError(f"universe_by_date file not found: {path}")
    frame = pd.read_csv(path, usecols=["trade_date", "symbol", "selected"])
    frame = _normalize_trade_dates(frame)
    frame = _filter_date_window(frame, start_date=start_date, end_date=end_date)
    frame = frame[frame["selected"].eq(1)].drop(columns="selected")
    if frame.empty:
        raise ValueError("universe_by_date is empty in the requested robustness window")
    _require_unique(frame, ["trade_date", "symbol"], label="universe_by_date")
    return frame.sort_values(["trade_date", "symbol"]).reset_index(drop=True)


def _load_st_history(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None,
    end_date: str | pd.Timestamp | None,
) -> pd.DataFrame:
    path = data_root / "assets/tushare/a_share/stock_st/a_share_all_stock_st_latest.parquet"
    if not path.is_file():
        return pd.DataFrame(columns=["trade_date", "symbol"])
    frame = pd.read_parquet(path, columns=["trade_date", "ts_code"])
    frame = frame.rename(columns={"ts_code": "symbol"})
    frame = _normalize_trade_dates(frame)
    frame = _filter_date_window(frame, start_date=start_date, end_date=end_date)
    _require_unique(frame, ["trade_date", "symbol"], label="stock_st")
    return frame.sort_values(["trade_date", "symbol"]).reset_index(drop=True)


def _load_instruments(data_root: Path) -> pd.DataFrame:
    path = data_root / "assets/tushare/a_share/instruments/a_share_all_instruments_latest.parquet"
    if not path.is_file():
        raise FileNotFoundError(f"instruments file not found: {path}")
    frame = pd.read_parquet(
        path,
        columns=["symbol", "list_status", "list_date", "delist_date"],
    )
    for column in ("list_date", "delist_date"):
        frame[column] = pd.to_datetime(
            frame[column].astype("string"),
            format="%Y%m%d",
            errors="coerce",
        )
    _require_unique(frame, ["symbol"], label="instruments")
    return frame.reset_index(drop=True)


def _coverage_metadata(
    daily_clean: pd.DataFrame,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    instruments: pd.DataFrame,
) -> dict[str, Any]:
    st_start = st_history["trade_date"].min() if not st_history.empty else None
    st_end = st_history["trade_date"].max() if not st_history.empty else None
    return {
        "daily_clean_rows": len(daily_clean),
        "daily_clean_symbols": int(daily_clean["symbol"].nunique()),
        "daily_clean_start": daily_clean["trade_date"].min().date().isoformat(),
        "daily_clean_end": daily_clean["trade_date"].max().date().isoformat(),
        "price_limit_source": "daily_clean limit flags derived from limit_status/stk_limit",
        "universe_rows": len(universe),
        "universe_symbols": int(universe["symbol"].nunique()),
        "universe_rebalance_dates": int(universe["trade_date"].nunique()),
        "universe_start": universe["trade_date"].min().date().isoformat(),
        "universe_end": universe["trade_date"].max().date().isoformat(),
        "st_rows": len(st_history),
        "st_symbols": int(st_history["symbol"].nunique()) if not st_history.empty else 0,
        "st_start": st_start.date().isoformat() if st_start is not None else None,
        "st_end": st_end.date().isoformat() if st_end is not None else None,
        "st_history_complete": False,
        "st_policy": "exact_stock_st_dates_only; pre-coverage dates remain unknown",
        "delisted_instruments": int(instruments["delist_date"].notna().sum()),
    }


def load_robustness_market_data(
    data_root: Path,
    *,
    start_date: str | pd.Timestamp | None = "2015-01-01",
    end_date: str | pd.Timestamp | None = None,
) -> RobustnessMarketData:
    """Load daily_clean, formation-date universe, dated ST rows and instruments."""
    daily_clean = _load_daily_clean(
        data_root,
        start_date=start_date,
        end_date=end_date,
    )
    universe = _load_universe(
        data_root,
        start_date=start_date,
        end_date=end_date,
    )
    st_history = _load_st_history(
        data_root,
        start_date=start_date,
        end_date=end_date,
    )
    instruments = _load_instruments(data_root)
    metadata = _coverage_metadata(daily_clean, universe, st_history, instruments)
    return RobustnessMarketData(
        daily_clean=daily_clean,
        universe=universe,
        st_history=st_history,
        instruments=instruments,
        metadata=metadata,
    )
