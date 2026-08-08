"""Selected-name minute execution checks for next-open-to-high research."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

SUPPORTED_MINUTE_SOURCES = {"tushare_full_day", "guan_deal", "guan_annual_minbar"}


def canonical_session_times(entry_date: pd.Timestamp) -> pd.DatetimeIndex:
    date = cast(pd.Timestamp, pd.Timestamp(entry_date)).normalize()
    morning = pd.date_range(date + pd.Timedelta(hours=9, minutes=30), periods=121, freq="min")
    afternoon = pd.date_range(date + pd.Timedelta(hours=13, minutes=1), periods=120, freq="min")
    return pd.DatetimeIndex(morning.append(afternoon))


def is_complete_session(
    bars: pd.DataFrame,
    entry_date: pd.Timestamp,
    minute_source: str = "tushare_full_day",
) -> bool:
    actual = pd.DatetimeIndex(pd.to_datetime(bars["trade_time"]))
    expected = canonical_session_times(entry_date)
    if minute_source == "tushare_full_day":
        return actual.equals(expected)
    if minute_source not in {"guan_deal", "guan_annual_minbar"}:
        return False
    expected_set = set(expected)
    return (
        actual.is_monotonic_increasing
        and actual.is_unique
        and len(actual) >= 2
        and all(timestamp in expected_set for timestamp in actual)
        and expected[1] in actual
        and expected[-1] in actual
    )


def load_minute_source_contracts(
    manifest_path: Path,
    minute_root: Path,
) -> dict[pd.Timestamp, str]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("status") != "passed" or payload.get("quality_status") != "passed":
        raise ValueError("Minute coverage manifest is not passed")
    manifest_output = Path(str(payload.get("output_dir", ""))).expanduser().resolve()
    if manifest_output != minute_root.resolve():
        raise ValueError(
            f"Minute coverage manifest output {manifest_output} does not match "
            f"{minute_root.resolve()}"
        )
    result: dict[pd.Timestamp, str] = {}
    for record in payload.get("daily", []):
        source = str(record.get("canonical_source", ""))
        if record.get("valid") is not True or source not in SUPPORTED_MINUTE_SOURCES:
            continue
        date = cast(pd.Timestamp, pd.to_datetime(str(record["date"]), format="%Y%m%d"))
        result[date] = source
    if not result:
        raise ValueError("Minute coverage manifest contains no supported valid daily contracts")
    return result


def source_contract_summary(sources: dict[pd.Timestamp, str]) -> dict[str, int]:
    return dict(sorted(Counter(sources.values()).items()))


def _valid_daily_limit(value: Any, reference: float) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result) or result <= 0 or reference <= 0:
        return None
    return result if 0.5 <= result / reference <= 1.5 else None


def _bool_value(value: Any, default: bool = False) -> bool:
    if value is None or pd.isna(value):
        return default
    return bool(value)


def _bool_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(False, index=frame.index, dtype=bool)
    return frame[column].astype("boolean").fillna(False).astype(bool)


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _candidate_base(candidate: pd.Series, minute_source: str) -> dict[str, Any]:
    return {
        "signal_date": candidate["signal_date"],
        "entry_date": candidate["entry_date"],
        "symbol": candidate["symbol"],
        "limit_band": candidate.get("limit_band", "unknown"),
        "board": candidate.get("board"),
        "signal_limit_pct_raw": candidate.get("signal_limit_pct_raw"),
        "minute_source": minute_source,
        "daily_entry_limit_available": _bool_value(
            candidate.get("entry_limit_available"), default=False
        ),
        "daily_blocked_limit_up_open": _bool_value(candidate.get("blocked_limit_up_open")),
        "daily_blocked_not_next_session": _bool_value(candidate.get("blocked_not_next_session")),
    }


def _signal_unfilled_result(base: dict[str, Any]) -> dict[str, Any]:
    reasons = []
    if not base["daily_entry_limit_available"]:
        reasons.append("daily_missing_or_invalid_open_limit")
    if base["daily_blocked_limit_up_open"]:
        reasons.append("daily_open_at_limit_up")
    if base["daily_blocked_not_next_session"]:
        reasons.append("not_next_market_session")
    if not reasons:
        reasons.append("other_daily_entry_gate")
    return {
        **base,
        "status": "signal_unfilled",
        "signal_unfilled_reasons": ",".join(reasons),
        "net_return": np.nan,
    }


def _entry_diagnostics(candidate: pd.Series, entry_bar: pd.Series) -> dict[str, Any]:
    entry_reference = float(entry_bar["close"])
    entry_amount = float(pd.to_numeric(entry_bar["amount"], errors="coerce"))
    daily_up_limit = _valid_daily_limit(candidate.get("exec_next_up_limit"), entry_reference)
    daily_down_limit = _valid_daily_limit(candidate.get("exec_next_down_limit"), entry_reference)
    return {
        "entry_time": entry_bar["trade_time"],
        "entry_reference": entry_reference,
        "entry_bar_amount": entry_amount,
        "entry_bar_amount_positive": math.isfinite(entry_amount) and entry_amount > 0,
        "daily_up_limit": daily_up_limit,
        "daily_down_limit": daily_down_limit,
        "entry_limit_available": daily_up_limit is not None,
        "entry_reference_vs_up_limit_bps": (
            (entry_reference / daily_up_limit - 1.0) * 10000.0
            if daily_up_limit is not None
            else None
        ),
        "entry_blocked_limit_up_0931": bool(
            daily_up_limit is not None and entry_reference >= daily_up_limit * 0.999
        ),
    }


def _add_daily_ohlc_diagnostic(
    result: dict[str, Any],
    candidate: pd.Series,
    *,
    take_profit_pct: float,
    entry_slippage_bps: float,
    exit_slippage_bps: float,
    round_trip_cost_bps: float,
) -> None:
    daily_columns = {"exec_next_open", "exec_next_high", "exec_next_close"}
    if not daily_columns.issubset(candidate.index):
        return
    daily_entry = float(candidate["exec_next_open"])
    daily_high = float(candidate["exec_next_high"])
    daily_close = float(candidate["exec_next_close"])
    daily_target = daily_entry * (1.0 + take_profit_pct)
    daily_hit = daily_high > daily_target
    daily_exit = daily_target if daily_hit else daily_close
    daily_entry_price = daily_entry * (1.0 + entry_slippage_bps / 10000.0)
    daily_exit_price = daily_exit * (1.0 - exit_slippage_bps / 10000.0)
    result["daily_ohlc_target_hit"] = daily_hit
    result["daily_ohlc_net_return"] = (
        daily_exit_price / daily_entry_price - 1.0 - round_trip_cost_bps / 10000.0
    )


def _audited_path_result(
    candidate: pd.Series,
    bars: pd.DataFrame,
    base: dict[str, Any],
    entry: dict[str, Any],
    entry_date: pd.Timestamp,
    expected_entry_time: pd.Timestamp,
    *,
    take_profit_pct: float,
    strict_cross: bool,
    entry_slippage_bps: float,
    exit_slippage_bps: float,
    round_trip_cost_bps: float,
    participation_rate: float,
) -> dict[str, Any]:
    entry_reference = float(entry["entry_reference"])
    later = bars.loc[pd.to_datetime(bars["trade_time"]).gt(expected_entry_time)]
    target = entry_reference * (1.0 + take_profit_pct)
    touch = later.loc[pd.to_numeric(later["high"], errors="coerce").ge(target)]
    cross = later.loc[pd.to_numeric(later["high"], errors="coerce").gt(target)]
    hit_rows = cross if strict_cross else touch
    hit = not hit_rows.empty
    close_bar = bars.loc[
        pd.to_datetime(bars["trade_time"]).eq(canonical_session_times(entry_date)[-1])
    ].iloc[0]
    if hit:
        exit_reference = target
        exit_time = hit_rows.iloc[0]["trade_time"]
        exit_reason = "take_profit_cross" if strict_cross else "take_profit_touch"
    else:
        exit_reference = float(close_bar["close"])
        exit_time = close_bar["trade_time"]
        exit_reason = "close"
    entry_price = entry_reference * (1.0 + entry_slippage_bps / 10000.0)
    exit_price = exit_reference * (1.0 - exit_slippage_bps / 10000.0)
    close_exit = exit_reason == "close"
    daily_down_limit = entry["daily_down_limit"]
    close_limit_available = close_exit and daily_down_limit is not None
    opening_amount = pd.to_numeric(bars.iloc[:5]["amount"], errors="coerce").fillna(0.0).sum()
    result = {
        **base,
        **entry,
        "status": "audited",
        "bar_count": len(bars),
        "target_price": target,
        "target_touched": not touch.empty,
        "target_crossed": not cross.empty,
        "exit_time": exit_time,
        "exit_reference": exit_reference,
        "exit_reason": exit_reason,
        "gross_return": exit_reference / entry_reference - 1.0,
        "net_return": exit_price / entry_price - 1.0 - round_trip_cost_bps / 10000.0,
        "opening_5bar_capacity_cny": opening_amount * participation_rate,
        "minute_open": float(bars.iloc[0]["open"]),
        "minute_high": float(bars["high"].max()),
        "minute_close": float(close_bar["close"]),
        "close_exit_limit_available": close_limit_available,
        "close_exit_at_down_limit": bool(
            close_limit_available and exit_reference <= daily_down_limit * 1.001
        ),
        "bar_level_target_fill_upper_bound": hit,
        "entry_completed_bar_close_upper_bound": True,
    }
    _add_daily_ohlc_diagnostic(
        result,
        candidate,
        take_profit_pct=take_profit_pct,
        entry_slippage_bps=entry_slippage_bps,
        exit_slippage_bps=exit_slippage_bps,
        round_trip_cost_bps=round_trip_cost_bps,
    )
    return result


def audit_candidate(
    candidate: pd.Series,
    bars: pd.DataFrame,
    *,
    entry_bar_index: int,
    take_profit_pct: float,
    strict_cross: bool,
    entry_slippage_bps: float,
    exit_slippage_bps: float,
    round_trip_cost_bps: float,
    participation_rate: float,
    minute_source: str = "tushare_full_day",
) -> dict[str, Any]:
    base = _candidate_base(candidate, minute_source)
    if not bool(candidate["execution_eligible"]):
        return _signal_unfilled_result(base)
    if bars.empty:
        return {**base, "status": "minute_missing", "net_return": np.nan}
    entry_date = cast(pd.Timestamp, pd.Timestamp(candidate["entry_date"]))
    if not is_complete_session(bars, entry_date, minute_source):
        return {**base, "status": "minute_incomplete", "net_return": np.nan}

    numeric = bars[["open", "high", "low", "close", "amount"]].apply(pd.to_numeric, errors="coerce")
    valid = (
        numeric[["open", "high", "low", "close"]].gt(0).all(axis=1)
        & numeric["high"].ge(numeric[["open", "close", "low"]].max(axis=1))
        & numeric["low"].le(numeric[["open", "close", "high"]].min(axis=1))
    )
    if not valid.all():
        return {**base, "status": "minute_invalid", "net_return": np.nan}

    expected_entry_time = canonical_session_times(entry_date)[entry_bar_index]
    entry_rows = bars.loc[pd.to_datetime(bars["trade_time"]).eq(expected_entry_time)]
    if len(entry_rows) != 1:
        return {**base, "status": "minute_incomplete", "net_return": np.nan}
    entry = _entry_diagnostics(candidate, entry_rows.iloc[0])
    if (
        not entry["entry_limit_available"]
        or entry["entry_blocked_limit_up_0931"]
        or not entry["entry_bar_amount_positive"]
    ):
        reasons = []
        if not entry["entry_limit_available"]:
            reasons.append("missing_or_invalid_up_limit")
        if entry["entry_blocked_limit_up_0931"]:
            reasons.append("limit_up_0931")
        if not entry["entry_bar_amount_positive"]:
            reasons.append("nonpositive_entry_amount")
        return {
            **base,
            **entry,
            "status": "minute_entry_blocked",
            "entry_block_reasons": ",".join(reasons),
            "net_return": np.nan,
        }
    return _audited_path_result(
        candidate,
        bars,
        base,
        entry,
        entry_date,
        expected_entry_time,
        take_profit_pct=take_profit_pct,
        strict_cross=strict_cross,
        entry_slippage_bps=entry_slippage_bps,
        exit_slippage_bps=exit_slippage_bps,
        round_trip_cost_bps=round_trip_cost_bps,
        participation_rate=participation_rate,
    )


def execution_diagnostic_summary(trades: pd.DataFrame) -> dict[str, Any]:
    assessed = (
        trades.loc[trades["entry_reference"].notna()]
        if "entry_reference" in trades
        else trades.iloc[0:0]
    )
    audited = trades.loc[trades["status"].eq("audited")]
    close_exits = audited.loc[
        audited.get("exit_reason", pd.Series(index=audited.index, dtype="object")).eq("close")
    ]
    entry_available = _bool_column(assessed, "entry_limit_available")
    close_available = _bool_column(close_exits, "close_exit_limit_available")
    entry_rows = len(assessed)
    entry_available_rows = int(entry_available.sum())
    entry_unavailable_rows = entry_rows - entry_available_rows
    entry_nonpositive_rows = int((~_bool_column(assessed, "entry_bar_amount_positive")).sum())
    entry_limit_blocked_rows = int(_bool_column(assessed, "entry_blocked_limit_up_0931").sum())
    entry_blocked_rows = int(trades["status"].eq("minute_entry_blocked").sum())
    close_rows = len(close_exits)
    close_available_rows = int(close_available.sum())
    close_down_limit_rows = int(_bool_column(close_exits, "close_exit_at_down_limit").sum())
    target_fill_rows = int(_bool_column(audited, "bar_level_target_fill_upper_bound").sum())
    candidate_rows = len(trades)
    daily_limit_unavailable_rows = int((~_bool_column(trades, "daily_entry_limit_available")).sum())
    daily_limit_up_rows = int(_bool_column(trades, "daily_blocked_limit_up_open").sum())
    daily_not_next_rows = int(_bool_column(trades, "daily_blocked_not_next_session").sum())
    unfilled = trades.loc[trades["status"].eq("signal_unfilled")]
    return {
        "candidate_rows": candidate_rows,
        "daily_entry_limit_unavailable_rows": daily_limit_unavailable_rows,
        "daily_entry_limit_unavailable_rate": _rate(daily_limit_unavailable_rows, candidate_rows),
        "daily_blocked_limit_up_open_rows": daily_limit_up_rows,
        "daily_blocked_limit_up_open_rate": _rate(daily_limit_up_rows, candidate_rows),
        "daily_blocked_not_next_session_rows": daily_not_next_rows,
        "daily_blocked_not_next_session_rate": _rate(daily_not_next_rows, candidate_rows),
        "signal_unfilled_rows": len(unfilled),
        "signal_unfilled_reason_counts": unfilled.get(
            "signal_unfilled_reasons", pd.Series(index=unfilled.index, dtype="object")
        )
        .fillna("unspecified")
        .value_counts()
        .to_dict(),
        "entry_diagnostic_rows": entry_rows,
        "entry_limit_available_rows": entry_available_rows,
        "entry_limit_available_rate": _rate(entry_available_rows, entry_rows),
        "entry_limit_unavailable_rows": entry_unavailable_rows,
        "entry_limit_unavailable_rate": _rate(entry_unavailable_rows, entry_rows),
        "entry_bar_nonpositive_amount_rows": entry_nonpositive_rows,
        "entry_bar_nonpositive_amount_rate": _rate(entry_nonpositive_rows, entry_rows),
        "entry_blocked_limit_up_0931_rows": entry_limit_blocked_rows,
        "entry_blocked_limit_up_0931_rate": _rate(entry_limit_blocked_rows, entry_rows),
        "entry_blocked_rows": entry_blocked_rows,
        "entry_blocked_rate": _rate(entry_blocked_rows, entry_rows),
        "close_exit_rows": close_rows,
        "close_exit_limit_available_rows": close_available_rows,
        "close_exit_limit_available_rate": _rate(close_available_rows, close_rows),
        "close_exit_limit_unavailable_rows": close_rows - close_available_rows,
        "close_exit_at_down_limit_rows": close_down_limit_rows,
        "close_exit_at_down_limit_rate": _rate(close_down_limit_rows, close_rows),
        "bar_level_target_fill_upper_bound_rows": target_fill_rows,
        "bar_level_target_fill_upper_bound_rate": _rate(target_fill_rows, len(audited)),
    }
