"""Vectorized same-entry minute benchmark helpers for next-open-to-high research."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from a_share_next_open_to_high_minute_execution import canonical_session_times


def _complete_session_symbols(
    bars: pd.DataFrame,
    entry_date: pd.Timestamp,
    minute_source: str,
) -> set[str]:
    expected = canonical_session_times(entry_date)
    valid_time = bars["trade_time"].isin(expected)
    entry_time = expected[1]
    close_time = expected[-1]
    coverage = (
        bars.assign(
            _valid_time=valid_time,
            _entry_time=bars["trade_time"].eq(entry_time),
            _close_time=bars["trade_time"].eq(close_time),
        )
        .groupby("ts_code", sort=False)
        .agg(
            rows=("trade_time", "size"),
            valid_times=("_valid_time", "sum"),
            entry_rows=("_entry_time", "sum"),
            close_rows=("_close_time", "sum"),
        )
    )
    if minute_source == "tushare_full_day":
        complete = coverage["rows"].eq(len(expected)) & coverage["valid_times"].eq(len(expected))
    elif minute_source in {"guan_deal", "guan_annual_minbar"}:
        complete = (
            coverage["valid_times"].eq(coverage["rows"])
            & coverage["entry_rows"].eq(1)
            & coverage["close_rows"].eq(1)
        )
    else:
        complete = pd.Series(False, index=coverage.index)
    return set(coverage.index[complete])


def load_benchmark_universe(path: Path, args: Any) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    required = {
        "trade_date",
        "entry_date",
        "symbol",
        "execution_eligible",
        "entry_limit_available",
        "blocked_limit_up_open",
        "blocked_not_next_session",
        "limit_band",
        "pre_close",
        "up_limit",
        "board",
        "exec_next_up_limit",
        "exec_next_down_limit",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Benchmark universe is missing columns: {sorted(missing)}")
    frame = frame.rename(columns={"trade_date": "signal_date"})
    frame["signal_date"] = pd.to_datetime(frame["signal_date"])
    frame["entry_date"] = pd.to_datetime(frame["entry_date"])
    suffix = frame["symbol"].str.rsplit(".", n=1).str[-1].str.upper()
    frame = frame.loc[suffix.isin(args.markets)].copy()
    if args.start_date:
        frame = frame.loc[frame["entry_date"].ge(pd.Timestamp(args.start_date))]
    if args.end_date:
        frame = frame.loc[frame["entry_date"].le(pd.Timestamp(args.end_date))]
    if frame.empty or frame.duplicated(["signal_date", "symbol"]).any():
        raise ValueError("Benchmark universe is empty or has duplicate signal_date/symbol keys")
    for column in (
        "execution_eligible",
        "entry_limit_available",
        "blocked_limit_up_open",
        "blocked_not_next_session",
    ):
        frame[column] = frame[column].astype("boolean").fillna(False).astype(bool)
    frame["limit_band"] = frame["limit_band"].astype("string").fillna("unknown")
    return frame.sort_values(["entry_date", "symbol"])


def _audit_benchmark_detail(
    candidates: pd.DataFrame,
    minute: pd.DataFrame,
    *,
    entry_bar_index: int,
    take_profit_pct: float,
    strict_cross: bool,
    entry_slippage_bps: float,
    exit_slippage_bps: float,
    round_trip_cost_bps: float,
    minute_source: str = "tushare_full_day",
) -> pd.DataFrame:
    executable = candidates.loc[
        candidates["execution_eligible"],
        ["symbol", "limit_band", "exec_next_up_limit", "exec_next_down_limit"],
    ]
    if minute.empty or executable.empty:
        return pd.DataFrame()

    bars = minute.loc[minute["ts_code"].isin(executable["symbol"])].copy()
    numeric_columns = ["open", "high", "low", "close", "amount"]
    numeric = bars[numeric_columns].apply(pd.to_numeric, errors="coerce")
    bars[numeric_columns] = numeric
    valid_row = (
        numeric[["open", "high", "low", "close"]].gt(0).all(axis=1)
        & numeric["high"].ge(numeric[["open", "close", "low"]].max(axis=1))
        & numeric["low"].le(numeric[["open", "close", "high"]].min(axis=1))
    )
    invalid_symbols = set(bars.loc[~valid_row, "ts_code"])
    bars = bars.loc[~bars["ts_code"].isin(invalid_symbols)].copy()
    entry_date = candidates.iloc[0]["entry_date"]
    complete_symbols = _complete_session_symbols(bars, entry_date, minute_source)
    bars = bars.loc[bars["ts_code"].isin(complete_symbols)].copy()
    entry_time = canonical_session_times(entry_date)[entry_bar_index]
    entry = bars.loc[bars["trade_time"].eq(entry_time), ["ts_code", "close", "amount"]].rename(
        columns={"close": "entry_reference", "amount": "entry_bar_amount"}
    )
    later = bars.loc[bars["trade_time"].gt(entry_time)]
    path = (
        later.groupby("ts_code", sort=False)
        .agg(path_high=("high", "max"), exit_reference=("close", "last"))
        .reset_index()
    )
    detail = executable.merge(entry, left_on="symbol", right_on="ts_code", how="inner")
    detail = detail.merge(path, on="ts_code", how="inner")
    if detail.empty:
        return detail

    up_limit = pd.to_numeric(detail["exec_next_up_limit"], errors="coerce")
    down_limit = pd.to_numeric(detail["exec_next_down_limit"], errors="coerce")
    up_ratio = up_limit / detail["entry_reference"]
    down_ratio = down_limit / detail["entry_reference"]
    detail["entry_limit_available"] = up_limit.gt(0) & up_ratio.between(0.5, 1.5)
    detail["close_limit_available"] = down_limit.gt(0) & down_ratio.between(0.5, 1.5)
    detail["entry_bar_amount_positive"] = detail["entry_bar_amount"].gt(0)
    detail["entry_blocked_limit_up_0931"] = detail["entry_limit_available"] & detail[
        "entry_reference"
    ].ge(up_limit * 0.999)
    detail["entry_allowed"] = (
        detail["entry_limit_available"]
        & detail["entry_bar_amount_positive"]
        & ~detail["entry_blocked_limit_up_0931"]
    )
    target = detail["entry_reference"] * (1.0 + take_profit_pct)
    hit = detail["path_high"].gt(target) if strict_cross else detail["path_high"].ge(target)
    exit_reference = detail["exit_reference"].where(~hit, target)
    gross = exit_reference / detail["entry_reference"] - 1.0
    entry_price = detail["entry_reference"] * (1.0 + entry_slippage_bps / 10000.0)
    exit_price = exit_reference * (1.0 - exit_slippage_bps / 10000.0)
    net = exit_price / entry_price - 1.0 - round_trip_cost_bps / 10000.0
    detail["target_crossed"] = hit & detail["entry_allowed"]
    detail["gross_return"] = gross.where(detail["entry_allowed"])
    detail["net_return"] = net.where(detail["entry_allowed"])
    close_exit = detail["entry_allowed"] & ~hit
    detail["close_exit"] = close_exit
    detail["close_exit_limit_available"] = close_exit & detail["close_limit_available"]
    detail["close_exit_at_down_limit"] = detail["close_exit_limit_available"] & exit_reference.le(
        down_limit * 1.001
    )
    detail["bar_level_target_fill_upper_bound"] = detail["entry_allowed"] & hit
    detail["minute_source"] = minute_source
    return detail


def _benchmark_result(candidates: pd.DataFrame, detail: pd.DataFrame) -> dict[str, Any]:
    first = candidates.iloc[0]
    slots = len(candidates)
    execution_eligible = candidates["execution_eligible"].astype(bool)
    executable = int(execution_eligible.sum())
    entry_limit_available = candidates.get(
        "entry_limit_available", pd.Series(True, index=candidates.index)
    ).astype(bool)
    blocked_limit_up = candidates.get(
        "blocked_limit_up_open", pd.Series(False, index=candidates.index)
    ).astype(bool)
    blocked_not_next = candidates.get(
        "blocked_not_next_session", pd.Series(False, index=candidates.index)
    ).astype(bool)
    known_unexecutable = ~entry_limit_available | blocked_limit_up | blocked_not_next
    base = {
        "signal_date": first["signal_date"],
        "entry_date": first["entry_date"],
        "benchmark_slots": slots,
        "benchmark_executable": executable,
        "benchmark_daily_entry_limit_unavailable": int((~entry_limit_available).sum()),
        "benchmark_daily_blocked_limit_up_open": int(blocked_limit_up.sum()),
        "benchmark_daily_blocked_not_next_session": int(blocked_not_next.sum()),
        "benchmark_daily_other_unexecutable": int(
            ((~execution_eligible) & ~known_unexecutable).sum()
        ),
    }
    if detail.empty:
        return _empty_result(base)
    audited = detail.loc[detail["entry_allowed"]]
    audited_count = len(audited)
    gross_sum = float(audited["gross_return"].sum())
    net_sum = float(audited["net_return"].sum())
    close_exits = audited.loc[audited["close_exit"]]
    return {
        **base,
        "benchmark_audited": audited_count,
        "benchmark_invested_weight": audited_count / slots,
        "benchmark_cash_weight": 1.0 - audited_count / slots,
        "benchmark_target_cross_rate": (
            float(audited["target_crossed"].mean()) if audited_count else None
        ),
        "benchmark_gross_return_sum": gross_sum,
        "benchmark_net_return_sum": net_sum,
        "benchmark_return": net_sum / slots,
        "benchmark_executed_mean_return": (
            float(audited["net_return"].mean()) if audited_count else 0.0
        ),
        "benchmark_minute_missing_or_incomplete": executable - len(detail),
        "benchmark_entry_limit_unavailable": int((~detail["entry_limit_available"]).sum()),
        "benchmark_entry_nonpositive_amount": int((~detail["entry_bar_amount_positive"]).sum()),
        "benchmark_entry_blocked_limit_up_0931": int(detail["entry_blocked_limit_up_0931"].sum()),
        "benchmark_close_exit_count": len(close_exits),
        "benchmark_close_exit_limit_unavailable": int(
            (~close_exits["close_exit_limit_available"]).sum()
        ),
        "benchmark_close_exit_at_down_limit": int(close_exits["close_exit_at_down_limit"].sum()),
        "benchmark_bar_level_target_fill_upper_bound": int(
            audited["bar_level_target_fill_upper_bound"].sum()
        ),
    }


def audit_benchmark_day_with_bands(
    candidates: pd.DataFrame,
    minute: pd.DataFrame,
    **execution_kwargs: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if "limit_band" not in candidates.columns:
        candidates = candidates.assign(limit_band="unknown")
    detail = _audit_benchmark_detail(candidates, minute, **execution_kwargs)
    broad = _benchmark_result(candidates, detail)
    bands: list[dict[str, Any]] = []
    for limit_band, band_candidates in candidates.groupby("limit_band", observed=True, sort=True):
        band_detail = (
            detail.loc[detail["limit_band"].eq(limit_band)] if not detail.empty else detail
        )
        bands.append(
            {**_benchmark_result(band_candidates, band_detail), "limit_band": str(limit_band)}
        )
    return broad, bands


def audit_benchmark_day(
    candidates: pd.DataFrame,
    minute: pd.DataFrame,
    **execution_kwargs: Any,
) -> dict[str, Any]:
    broad, _ = audit_benchmark_day_with_bands(candidates, minute, **execution_kwargs)
    return broad


def _empty_result(base: dict[str, Any]) -> dict[str, Any]:
    return {
        **base,
        "benchmark_audited": 0,
        "benchmark_invested_weight": 0.0,
        "benchmark_cash_weight": 1.0,
        "benchmark_target_cross_rate": None,
        "benchmark_gross_return_sum": 0.0,
        "benchmark_net_return_sum": 0.0,
        "benchmark_return": 0.0,
        "benchmark_executed_mean_return": 0.0,
        "benchmark_minute_missing_or_incomplete": base["benchmark_executable"],
        "benchmark_entry_limit_unavailable": 0,
        "benchmark_entry_nonpositive_amount": 0,
        "benchmark_entry_blocked_limit_up_0931": 0,
        "benchmark_close_exit_count": 0,
        "benchmark_close_exit_limit_unavailable": 0,
        "benchmark_close_exit_at_down_limit": 0,
        "benchmark_bar_level_target_fill_upper_bound": 0,
    }


def attach_exposure_matched_benchmark(
    selected_daily: pd.DataFrame,
    benchmark_daily: pd.DataFrame,
) -> pd.DataFrame:
    output = selected_daily.merge(
        benchmark_daily,
        on=["signal_date", "entry_date"],
        how="left",
        validate="one_to_one",
    )
    if output["benchmark_return"].isna().any():
        raise ValueError("Same-entry minute benchmark does not cover every selected date")
    output["selected_invested_weight"] = 1.0 - output["cash_weight"]
    output["benchmark_exposure_matched_return"] = (
        output["benchmark_executed_mean_return"] * output["selected_invested_weight"]
    )
    output["broad_active_return"] = (
        output["portfolio_return"] - output["benchmark_exposure_matched_return"]
    )
    output["active_return"] = output["broad_active_return"]
    return output


def attach_limit_band_matched_benchmark(
    selected_daily: pd.DataFrame,
    selected_trades: pd.DataFrame,
    benchmark_bands: pd.DataFrame,
    top_k: int,
) -> pd.DataFrame:
    audited = selected_trades.loc[selected_trades["status"].eq("audited")]
    selected_bands = (
        audited.groupby(["signal_date", "entry_date", "limit_band"], observed=True, sort=True)
        .size()
        .rename("selected_band_audited")
        .reset_index()
    )
    weighted = benchmark_bands.merge(
        selected_bands,
        on=["signal_date", "entry_date", "limit_band"],
        how="left",
        validate="one_to_one",
    )
    weighted["selected_band_audited"] = weighted["selected_band_audited"].fillna(0).astype(int)
    weighted["selected_band_weight"] = weighted["selected_band_audited"] / top_k
    weighted["limit_band_benchmark_contribution"] = (
        weighted["benchmark_executed_mean_return"] * weighted["selected_band_weight"]
    )
    reconstructed = (
        weighted.groupby(["signal_date", "entry_date"], sort=True)
        .agg(
            benchmark_limit_band_matched_return=(
                "limit_band_benchmark_contribution",
                "sum",
            ),
            benchmark_limit_band_matched_weight=("selected_band_weight", "sum"),
        )
        .reset_index()
    )
    output = selected_daily.merge(
        reconstructed,
        on=["signal_date", "entry_date"],
        how="left",
        validate="one_to_one",
    )
    if output["benchmark_limit_band_matched_return"].isna().any():
        raise ValueError("Limit-band benchmark does not cover every selected date")
    if "selected_invested_weight" in output.columns and not np.allclose(
        output["benchmark_limit_band_matched_weight"],
        output["selected_invested_weight"],
        rtol=0.0,
        atol=1e-12,
    ):
        raise ValueError("Limit-band weights do not reconstruct selected invested weight")
    output["within_band_active_return"] = (
        output["portfolio_return"] - output["benchmark_limit_band_matched_return"]
    )
    output["active_return"] = output["within_band_active_return"]
    return output


def validate_benchmark_decomposition(
    benchmark_daily: pd.DataFrame,
    benchmark_bands: pd.DataFrame,
) -> None:
    sum_columns = [
        "benchmark_slots",
        "benchmark_executable",
        "benchmark_daily_entry_limit_unavailable",
        "benchmark_daily_blocked_limit_up_open",
        "benchmark_daily_blocked_not_next_session",
        "benchmark_daily_other_unexecutable",
        "benchmark_audited",
        "benchmark_gross_return_sum",
        "benchmark_net_return_sum",
        "benchmark_minute_missing_or_incomplete",
        "benchmark_entry_limit_unavailable",
        "benchmark_entry_nonpositive_amount",
        "benchmark_entry_blocked_limit_up_0931",
        "benchmark_close_exit_count",
        "benchmark_close_exit_limit_unavailable",
        "benchmark_close_exit_at_down_limit",
        "benchmark_bar_level_target_fill_upper_bound",
    ]
    decomposed = (
        benchmark_bands.groupby(["signal_date", "entry_date"], sort=True)[sum_columns]
        .sum()
        .reset_index()
    )
    expected = benchmark_daily[["signal_date", "entry_date", *sum_columns]]
    check = expected.merge(
        decomposed,
        on=["signal_date", "entry_date"],
        suffixes=("_broad", "_bands"),
        how="outer",
        validate="one_to_one",
    )
    if len(check) != len(expected):
        raise ValueError("Limit-band benchmark dates do not match broad benchmark dates")
    for column in sum_columns:
        if not np.allclose(
            check[f"{column}_broad"],
            check[f"{column}_bands"],
            rtol=0.0,
            atol=1e-10,
        ):
            raise ValueError(f"Limit-band benchmark does not reconstruct {column}")


def benchmark_execution_diagnostic_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {}
    diagnostic_columns = [
        "benchmark_daily_entry_limit_unavailable",
        "benchmark_daily_blocked_limit_up_open",
        "benchmark_daily_blocked_not_next_session",
        "benchmark_daily_other_unexecutable",
        "benchmark_minute_missing_or_incomplete",
        "benchmark_entry_limit_unavailable",
        "benchmark_entry_nonpositive_amount",
        "benchmark_entry_blocked_limit_up_0931",
        "benchmark_close_exit_count",
        "benchmark_close_exit_limit_unavailable",
        "benchmark_close_exit_at_down_limit",
        "benchmark_bar_level_target_fill_upper_bound",
    ]
    result: dict[str, Any] = {column: int(frame[column].sum()) for column in diagnostic_columns}
    slots = int(frame["benchmark_slots"].sum())
    executable = int(frame["benchmark_executable"].sum())
    audited = int(frame["benchmark_audited"].sum())
    entry_rows = executable - result["benchmark_minute_missing_or_incomplete"]
    close_rows = result["benchmark_close_exit_count"]
    result.update(
        {
            "benchmark_slots": slots,
            "benchmark_executable": executable,
            "benchmark_audited": audited,
            "benchmark_audited_slot_rate": audited / slots if slots else None,
            "benchmark_entry_diagnostic_rows": entry_rows,
            "benchmark_entry_limit_unavailable_rate": (
                result["benchmark_entry_limit_unavailable"] / entry_rows if entry_rows else None
            ),
            "benchmark_entry_blocked_limit_up_0931_rate": (
                result["benchmark_entry_blocked_limit_up_0931"] / entry_rows if entry_rows else None
            ),
            "benchmark_close_exit_at_down_limit_rate": (
                result["benchmark_close_exit_at_down_limit"] / close_rows if close_rows else None
            ),
            "benchmark_bar_level_target_fill_upper_bound_rate": (
                result["benchmark_bar_level_target_fill_upper_bound"] / audited if audited else None
            ),
        }
    )
    return result


def _aggregate_exposure(
    daily: pd.DataFrame,
    *,
    scope: str,
    weight_column: str,
    row_column: str,
) -> pd.DataFrame:
    total_dates = daily[["signal_date", "entry_date"]].drop_duplicates().shape[0]
    total_rows = daily[row_column].sum()
    result = (
        daily.groupby("limit_band", observed=True, sort=True)
        .agg(
            rows=(row_column, "sum"),
            dates_present=("signal_date", "nunique"),
            daily_weight_sum=(weight_column, "sum"),
        )
        .reset_index()
    )
    result["row_share"] = result["rows"] / max(total_rows, 1)
    result["daily_weight_mean"] = result.pop("daily_weight_sum") / max(total_dates, 1)
    result["total_dates"] = total_dates
    result.insert(0, "scope", scope)
    return result


def summarize_limit_band_exposure(
    selected_trades: pd.DataFrame,
    benchmark_bands: pd.DataFrame,
    top_k: int,
) -> pd.DataFrame:
    selected = selected_trades.loc[selected_trades["status"].eq("audited")]
    selected_daily = (
        selected.groupby(["signal_date", "entry_date", "limit_band"], observed=True, sort=True)
        .size()
        .rename("selected_rows")
        .reset_index()
    )
    selected_daily["daily_weight"] = selected_daily["selected_rows"] / top_k
    universe_daily = benchmark_bands.copy()
    universe_daily["daily_weight"] = universe_daily["benchmark_slots"] / universe_daily.groupby(
        ["signal_date", "entry_date"]
    )["benchmark_slots"].transform("sum")
    return pd.concat(
        [
            _aggregate_exposure(
                selected_daily,
                scope="selected_audited",
                weight_column="daily_weight",
                row_column="selected_rows",
            ),
            _aggregate_exposure(
                universe_daily,
                scope="signal_universe",
                weight_column="daily_weight",
                row_column="benchmark_slots",
            ),
        ],
        ignore_index=True,
    )
