"""Diagnostics that decompose low-turnover signals into observable proxies."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from .liquidity_signals import _residualize_by_date, _standardize_signal

TURNOVER_PROXY_RAW_COLUMNS = (
    "activity_20d_raw",
    "illiquidity_20d_raw",
    "momentum_126_21d_raw",
    "reversal_21d_raw",
)
TURNOVER_PROXY_SCORE_COLUMNS = {
    "activity_20d_raw": "activity_20d_score",
    "illiquidity_20d_raw": "illiquidity_20d_score",
    "momentum_126_21d_raw": "momentum_126_21d_score",
    "reversal_21d_raw": "reversal_21d_score",
}
TURNOVER_DECONFOUNDING_CONTROLS: dict[str, tuple[str, ...]] = {
    "raw": (),
    "size": ("size_score",),
    "size_lowvol": ("size_score", "lowvol_score"),
    "size_lowvol_liquidity": (
        "size_score",
        "lowvol_score",
        "activity_20d_score",
        "illiquidity_20d_score",
    ),
    "size_lowvol_liquidity_returns": (
        "size_score",
        "lowvol_score",
        "activity_20d_score",
        "illiquidity_20d_score",
        "momentum_126_21d_score",
        "reversal_21d_score",
    ),
}
TURNOVER_DECONFOUNDING_SIGNAL_COLUMNS = {
    "raw": "signal_low_turnover",
    **{
        stage: f"signal_low_turnover_residual_{stage}"
        for stage in TURNOVER_DECONFOUNDING_CONTROLS
        if stage != "raw"
    },
}


def _require_columns(frame: pd.DataFrame, columns: set[str], *, label: str) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def _rolling_log_return(
    values: pd.Series,
    *,
    window: int,
    minimum_observations: int,
    shift: int,
) -> pd.Series:
    summed = values.rolling(window, min_periods=minimum_observations).sum().shift(shift)
    return np.expm1(summed)


def build_turnover_proxy_controls(
    daily_clean: pd.DataFrame,
    formation_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Build lagged activity, illiquidity, momentum, and reversal controls.

    Every rolling input is shifted so the formation session itself cannot affect
    a control value. ``tr_close`` is used for return histories to preserve the
    total-return price bridge already used by the robustness data contract.
    """
    _require_columns(
        daily_clean,
        {"trade_date", "symbol", "tr_close", "amount"},
        label="daily_clean",
    )
    dates = pd.DatetimeIndex(formation_dates).normalize()  # ty: ignore[unresolved-attribute]
    dates = dates.sort_values().unique()
    if dates.empty:
        return pd.DataFrame(columns=pd.Index(["trade_date", "symbol", *TURNOVER_PROXY_RAW_COLUMNS]))

    frame = daily_clean[["trade_date", "symbol", "tr_close", "amount"]].copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str)
    frame["tr_close"] = pd.to_numeric(frame["tr_close"], errors="coerce")
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    frame = frame.sort_values(["symbol", "trade_date"]).reset_index(drop=True)

    positive_price = frame["tr_close"].where(frame["tr_close"] > 0)
    frame["log_return_1d"] = np.log(positive_price).groupby(frame["symbol"], sort=False).diff()
    frame["return_1d"] = np.expm1(frame["log_return_1d"])
    frame["log_amount"] = np.log1p(frame["amount"].clip(lower=0))
    positive_amount = frame["amount"].where(frame["amount"] > 0)
    frame["amihud_1d"] = frame["return_1d"].abs() / positive_amount

    grouped = frame.groupby("symbol", sort=False)
    frame["activity_20d_raw"] = grouped["log_amount"].transform(
        lambda values: values.rolling(20, min_periods=15).mean().shift(1)
    )
    frame["illiquidity_20d_raw"] = grouped["amihud_1d"].transform(
        lambda values: values.rolling(20, min_periods=15).mean().shift(1)
    )
    frame["momentum_126_21d_raw"] = grouped["log_return_1d"].transform(
        lambda values: _rolling_log_return(
            values,
            window=105,
            minimum_observations=80,
            shift=21,
        )
    )
    frame["reversal_21d_raw"] = grouped["log_return_1d"].transform(
        lambda values: _rolling_log_return(
            values,
            window=21,
            minimum_observations=15,
            shift=1,
        )
    )

    output_columns = ["trade_date", "symbol", *TURNOVER_PROXY_RAW_COLUMNS]
    return (
        frame.loc[frame["trade_date"].isin(dates), output_columns]
        .drop_duplicates(["trade_date", "symbol"], keep="last")
        .sort_values(["trade_date", "symbol"])
        .reset_index(drop=True)
    )


def _mean_cross_sectional_correlation(
    frame: pd.DataFrame,
    left: str,
    right: str,
) -> float:
    if left == right:
        return 1.0 if frame[left].notna().any() else float("nan")
    values = [
        group[left].corr(group[right])
        for _date, group in frame[["trade_date", left, right]]
        .dropna()
        .groupby("trade_date", sort=False)
    ]
    if not values:
        return float("nan")
    return float(pd.Series(values, dtype=float).replace([np.inf, -np.inf], np.nan).mean())


def _mean_cross_sectional_std(frame: pd.DataFrame, column: str) -> float:
    values = (
        frame[["trade_date", column]]
        .dropna()
        .groupby("trade_date", sort=False)[column]
        .std(ddof=0)
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    return float(values.mean()) if not values.empty else float("nan")


def build_turnover_deconfounding_ladder(
    signal_panel: pd.DataFrame,
    proxy_controls: pd.DataFrame,
    *,
    minimum_sample: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Residualize low turnover through an ordered ladder of observable proxies."""
    _require_columns(
        signal_panel,
        {
            "trade_date",
            "symbol",
            "industry_l1",
            "size_score",
            "lowvol_score",
            "signal_low_turnover",
        },
        label="signal_panel",
    )
    _require_columns(
        proxy_controls,
        {"trade_date", "symbol", *TURNOVER_PROXY_RAW_COLUMNS},
        label="proxy_controls",
    )
    panel = signal_panel.merge(
        proxy_controls,
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    ).copy()
    for raw_column, score_column in TURNOVER_PROXY_SCORE_COLUMNS.items():
        panel[score_column] = _standardize_signal(
            panel[raw_column],
            panel["trade_date"],
            panel["industry_l1"],
        )

    raw_signal_std = _mean_cross_sectional_std(panel, "signal_low_turnover")
    diagnostic_rows: list[dict[str, object]] = []
    for stage, controls in TURNOVER_DECONFOUNDING_CONTROLS.items():
        signal_column = TURNOVER_DECONFOUNDING_SIGNAL_COLUMNS[stage]
        if controls:
            panel[signal_column] = _residualize_by_date(
                panel,
                "signal_low_turnover",
                controls,
                minimum_sample=minimum_sample,
            )
        control_correlations = [
            abs(_mean_cross_sectional_correlation(panel, signal_column, control))
            for control in controls
        ]
        finite_control_correlations = [
            value for value in control_correlations if np.isfinite(value)
        ]
        stage_std = _mean_cross_sectional_std(panel, signal_column)
        diagnostic_rows.append(
            {
                "stage": stage,
                "signal_column": signal_column,
                "control_columns": "|".join(controls),
                "non_null_observations": int(panel[signal_column].notna().sum()),
                "raw_signal_correlation": _mean_cross_sectional_correlation(
                    panel,
                    signal_column,
                    "signal_low_turnover",
                ),
                "mean_cross_sectional_std": stage_std,
                "mean_cross_sectional_std_ratio": (
                    stage_std / raw_signal_std
                    if np.isfinite(stage_std) and np.isfinite(raw_signal_std) and raw_signal_std > 0
                    else float("nan")
                ),
                "max_abs_control_correlation": (
                    max(finite_control_correlations)
                    if finite_control_correlations
                    else float("nan")
                ),
            }
        )
    return panel, pd.DataFrame(diagnostic_rows)


def _rank_bucket(values: pd.Series, bucket_count: int) -> pd.Series:
    rank = values.rank(method="first", ascending=True)
    return np.ceil(rank * bucket_count / len(values)).astype(int)


def _forward_return_for_date(
    daily_returns: pd.DataFrame,
    *,
    formation_date: pd.Timestamp,
    next_formation_date: pd.Timestamp,
) -> pd.Series:
    window = daily_returns.loc[
        (daily_returns.index > formation_date) & (daily_returns.index <= next_formation_date)
    ]
    return (1.0 + window).prod(axis=0, min_count=1) - 1.0


def summarize_turnover_anatomy(
    panel: pd.DataFrame,
    daily_returns: pd.DataFrame,
    *,
    formation_dates: pd.DatetimeIndex,
    calendar_dates: pd.DatetimeIndex | None = None,
    stage_columns: Mapping[str, str] | None = None,
    sample_label: str,
    bucket_count: int = 10,
) -> pd.DataFrame:
    """Separate the low-turnover long leg from high-turnover avoidance returns."""
    if bucket_count < 2:
        raise ValueError("bucket_count must be at least 2")
    stages = dict(stage_columns or TURNOVER_DECONFOUNDING_SIGNAL_COLUMNS)
    _require_columns(panel, {"trade_date", "symbol", *stages.values()}, label="panel")
    selected_dates = pd.DatetimeIndex(formation_dates).normalize()  # ty: ignore[unresolved-attribute]
    selected_dates = selected_dates.sort_values().unique()
    if selected_dates.empty:
        return pd.DataFrame()

    returns = daily_returns.copy()
    returns.index = pd.DatetimeIndex(returns.index).normalize()  # ty: ignore[unresolved-attribute]
    if calendar_dates is None:
        calendar = pd.DatetimeIndex(pd.to_datetime(panel["trade_date"]).dt.normalize().unique())
    else:
        calendar = pd.DatetimeIndex(calendar_dates).normalize()  # ty: ignore[unresolved-attribute]
    calendar = calendar.sort_values().unique()
    if calendar.empty:
        return pd.DataFrame()

    rows_by_stage: dict[str, list[dict[str, float]]] = {stage: [] for stage in stages}
    normalized_trade_dates = pd.to_datetime(panel["trade_date"]).dt.normalize()
    for formation_date in selected_dates:
        position = int(calendar.searchsorted(formation_date))
        if position >= len(calendar) or calendar[position] != formation_date:
            continue
        next_date = calendar[position + 1] if position + 1 < len(calendar) else returns.index.max()
        forward = _forward_return_for_date(
            returns,
            formation_date=formation_date,
            next_formation_date=next_date,
        )
        cross = panel.loc[
            normalized_trade_dates.eq(formation_date),
            ["symbol", *stages.values()],
        ].drop_duplicates("symbol")
        for stage, signal_column in stages.items():
            valid = cross[["symbol", signal_column]].copy()
            valid["forward_return"] = valid["symbol"].map(forward)
            valid[signal_column] = pd.to_numeric(valid[signal_column], errors="coerce")
            valid["forward_return"] = pd.to_numeric(valid["forward_return"], errors="coerce")
            valid = valid.dropna(subset=[signal_column, "forward_return"])
            if len(valid) < bucket_count:
                continue
            valid["bucket"] = _rank_bucket(valid[signal_column], bucket_count)
            low_turnover = float(
                valid.loc[valid["bucket"].eq(bucket_count), "forward_return"].mean()
            )
            high_turnover = float(valid.loc[valid["bucket"].eq(1), "forward_return"].mean())
            rows_by_stage[stage].append(
                {
                    "rank_ic": float(
                        valid[signal_column].corr(valid["forward_return"], method="spearman")
                    ),
                    "low_turnover_leg_return": low_turnover,
                    "high_turnover_leg_return": high_turnover,
                    "low_minus_high_return": low_turnover - high_turnover,
                    "observations": float(len(valid)),
                }
            )

    summary_rows: list[dict[str, object]] = []
    for stage, rows in rows_by_stage.items():
        if not rows:
            continue
        frame = pd.DataFrame(rows)
        summary_rows.append(
            {
                "sample": sample_label,
                "stage": stage,
                "signal_column": stages[stage],
                "formation_dates": len(frame),
                "observations": int(frame["observations"].sum()),
                "mean_rank_ic": float(frame["rank_ic"].mean()),
                "median_rank_ic": float(frame["rank_ic"].median()),
                "low_turnover_leg_return": float(frame["low_turnover_leg_return"].mean()),
                "high_turnover_leg_return": float(frame["high_turnover_leg_return"].mean()),
                "low_minus_high_return": float(frame["low_minus_high_return"].mean()),
            }
        )
    return pd.DataFrame(summary_rows)


__all__ = [
    "TURNOVER_DECONFOUNDING_CONTROLS",
    "TURNOVER_DECONFOUNDING_SIGNAL_COLUMNS",
    "TURNOVER_PROXY_RAW_COLUMNS",
    "TURNOVER_PROXY_SCORE_COLUMNS",
    "build_turnover_deconfounding_ladder",
    "build_turnover_proxy_controls",
    "summarize_turnover_anatomy",
]
