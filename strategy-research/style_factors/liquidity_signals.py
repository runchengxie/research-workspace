"""Turnover lookbacks and exposure-controlled low-turnover research signals."""

from __future__ import annotations

from collections import deque
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd

from .data import _partition_date
from .helpers import merge_sw_industry_pit

BASE_SIGNAL_LABELS = {
    "turnover_1d": "月末单日换手率",
    "turnover_mean_20d": "20 日平均换手率",
    "turnover_median_20d": "20 日中位换手率",
    "turnover_mean_60d": "60 日平均换手率",
    "turnover_median_60d": "60 日中位换手率",
}


def liquidity_signal_labels() -> dict[str, str]:
    labels = dict(BASE_SIGNAL_LABELS)
    labels.update(
        {
            f"{name}_neutral": f"{label}，剔除市值和低波动影响"
            for name, label in BASE_SIGNAL_LABELS.items()
        }
    )
    return labels


def liquidity_signal_columns() -> dict[str, str]:
    return {name: f"signal_{name}" for name in liquidity_signal_labels()}


def _read_turnover_partition(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path, columns=["symbol", "turnover_rate"])
    frame = frame.drop_duplicates("symbol", keep="last").copy()
    frame["turnover_rate"] = pd.to_numeric(frame["turnover_rate"], errors="coerce")
    frame["turnover_rate"] = frame["turnover_rate"].clip(lower=0.01, upper=100)
    return frame.dropna(subset=["symbol", "turnover_rate"])


def _aggregate_turnover_window(
    frames: list[pd.DataFrame],
    *,
    window: int,
    minimum_observations: int,
) -> pd.DataFrame:
    selected = frames[-window:]
    if not selected:
        return pd.DataFrame(columns=["symbol", "mean", "median", "observations"])
    combined = pd.concat(selected, ignore_index=True)
    summary = (
        combined.groupby("symbol", sort=False)["turnover_rate"]
        .agg(mean="mean", median="median", observations="count")
        .reset_index()
    )
    incomplete = summary["observations"] < minimum_observations
    summary.loc[incomplete, ["mean", "median"]] = np.nan
    return summary


def load_turnover_lookbacks(
    data_root: Path,
    formation_dates: pd.DatetimeIndex,
    *,
    minimum_coverage: float = 0.75,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Read daily-basic partitions once and materialize formation-date lookbacks."""
    dates = pd.DatetimeIndex(formation_dates).normalize().sort_values().unique()
    if dates.empty:
        raise ValueError("formation_dates is empty")
    if not 0 < minimum_coverage <= 1:
        raise ValueError("minimum_coverage must be in (0, 1]")

    directory = data_root / "assets/tushare/a_share/daily_basic/a_share_all_daily_basic_latest/data"
    if not directory.is_dir():
        raise FileNotFoundError(f"daily_basic directory does not exist: {directory}")

    scan_start = dates.min() - pd.Timedelta(days=120)
    scan_end = dates.max()
    dated_paths = [
        (date, path)
        for path in sorted(directory.glob("trade_date=*"))
        if (date := _partition_date(path)) is not None
        and pd.notna(date)
        and scan_start <= date <= scan_end
    ]
    formation_set = set(dates)
    history: deque[pd.DataFrame] = deque(maxlen=60)
    outputs: list[pd.DataFrame] = []
    minimum_20d = ceil(20 * minimum_coverage)
    minimum_60d = ceil(60 * minimum_coverage)

    for trade_date, path in dated_paths:
        frame = _read_turnover_partition(path)
        history.append(frame)
        if trade_date not in formation_set:
            continue

        history_frames = list(history)
        current = frame.rename(columns={"turnover_rate": "turnover_1d"})
        summary_20d = _aggregate_turnover_window(
            history_frames,
            window=20,
            minimum_observations=minimum_20d,
        ).rename(
            columns={
                "mean": "turnover_mean_20d",
                "median": "turnover_median_20d",
                "observations": "turnover_observations_20d",
            }
        )
        summary_60d = _aggregate_turnover_window(
            history_frames,
            window=60,
            minimum_observations=minimum_60d,
        ).rename(
            columns={
                "mean": "turnover_mean_60d",
                "median": "turnover_median_60d",
                "observations": "turnover_observations_60d",
            }
        )
        output = current.merge(summary_20d, on="symbol", how="left", validate="one_to_one")
        output = output.merge(summary_60d, on="symbol", how="left", validate="one_to_one")
        output.insert(0, "trade_date", trade_date)
        outputs.append(output)

    if not outputs:
        raise ValueError("no turnover lookbacks matched the requested formation dates")
    result = pd.concat(outputs, ignore_index=True)
    metadata: dict[str, object] = {
        "source_partition_count": len(dated_paths),
        "formation_dates_requested": len(dates),
        "formation_dates_produced": int(result["trade_date"].nunique()),
        "minimum_coverage": minimum_coverage,
        "minimum_observations_20d": minimum_20d,
        "minimum_observations_60d": minimum_60d,
    }
    return result, metadata


def _standardize_signal(
    values: pd.Series,
    trade_dates: pd.Series,
    industries: pd.Series,
) -> pd.Series:
    frame = pd.DataFrame(
        {"value": values.astype(float), "trade_date": trade_dates, "industry": industries}
    )
    grouped = frame.groupby("trade_date", sort=False)["value"]
    lower = grouped.transform(lambda series: series.quantile(0.01))
    upper = grouped.transform(lambda series: series.quantile(0.99))
    frame["value"] = frame["value"].clip(lower=lower, upper=upper, axis=0)
    industry_mean = frame.groupby(["trade_date", "industry"], sort=False, dropna=False)[
        "value"
    ].transform("mean")
    demeaned = frame["value"] - industry_mean
    date_grouped = demeaned.groupby(frame["trade_date"], sort=False)
    standardized = (demeaned - date_grouped.transform("mean")) / date_grouped.transform(
        "std"
    ).replace(0, np.nan)
    standardized.index = values.index
    return standardized


def build_liquidity_control_panel(
    daily: pd.DataFrame,
    basics: pd.DataFrame,
    formation_dates: pd.DatetimeIndex,
    *,
    sw_membership: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build formation-date size and low-volatility controls without other factors."""
    prices = daily[["trade_date", "symbol", "close", "amount"]].copy()
    prices = prices[prices["amount"] > 0].sort_values(["symbol", "trade_date"])
    prices["return_1d"] = prices.groupby("symbol", sort=False)["close"].pct_change()
    prices["volatility_21d"] = prices.groupby("symbol", sort=False)["return_1d"].transform(
        lambda series: series.rolling(21, min_periods=10).std().shift(1)
    )
    dates = pd.DatetimeIndex(formation_dates).normalize()
    controls = prices[prices["trade_date"].isin(dates)].copy()
    basic_columns = ["trade_date", "symbol", "total_mv"]
    controls = controls.merge(
        basics[basic_columns],
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    controls = controls[controls["total_mv"] > 0].copy()
    controls["size_raw"] = np.log(controls["total_mv"] + 1)
    controls["lowvol_raw"] = -controls["volatility_21d"]
    controls = merge_sw_industry_pit(controls, sw_membership)
    controls["size_score"] = _standardize_signal(
        controls["size_raw"], controls["trade_date"], controls["industry_l1"]
    )
    controls["lowvol_score"] = _standardize_signal(
        controls["lowvol_raw"], controls["trade_date"], controls["industry_l1"]
    )
    return controls[["trade_date", "symbol", "industry_l1", "size_score", "lowvol_score"]].copy()


def _residualize_by_date(
    frame: pd.DataFrame,
    signal_column: str,
    control_columns: tuple[str, ...],
    *,
    minimum_sample: int = 30,
) -> pd.Series:
    residuals = pd.Series(np.nan, index=frame.index, dtype=float)
    for _trade_date, group in frame.groupby("trade_date", sort=False):
        columns = [signal_column, *control_columns]
        valid = group[columns].dropna()
        if len(valid) < minimum_sample:
            continue
        design = np.column_stack(
            [np.ones(len(valid)), *(valid[column].to_numpy() for column in control_columns)]
        )
        target = valid[signal_column].to_numpy()
        coefficients, *_rest = np.linalg.lstsq(design, target, rcond=None)
        residuals.loc[valid.index] = target - design @ coefficients
    grouped = residuals.groupby(frame["trade_date"], sort=False)
    return (residuals - grouped.transform("mean")) / grouped.transform("std").replace(0, np.nan)


def _mean_cross_sectional_correlation(
    frame: pd.DataFrame,
    left: str,
    right: str,
) -> float:
    correlations = [
        group[left].corr(group[right])
        for _trade_date, group in frame.groupby("trade_date", sort=False)
    ]
    return float(pd.Series(correlations).replace([np.inf, -np.inf], np.nan).mean())


def build_liquidity_signal_panel(
    turnover: pd.DataFrame,
    controls: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build industry-adjusted and jointly exposure-neutralized signal variants."""
    panel = controls.merge(
        turnover,
        on=["trade_date", "symbol"],
        how="inner",
        validate="one_to_one",
    )
    diagnostic_rows: list[dict[str, object]] = []
    for variant, _label in BASE_SIGNAL_LABELS.items():
        signal_column = f"signal_{variant}"
        panel[signal_column] = _standardize_signal(
            -panel[variant], panel["trade_date"], panel["industry_l1"]
        )
        neutral_variant = f"{variant}_neutral"
        neutral_column = f"signal_{neutral_variant}"
        panel[neutral_column] = _residualize_by_date(
            panel,
            signal_column,
            ("size_score", "lowvol_score"),
        )

        for name, column, neutralized in (
            (variant, signal_column, False),
            (neutral_variant, neutral_column, True),
        ):
            diagnostic_rows.append(
                {
                    "variant": name,
                    "neutralized": neutralized,
                    "formation_observations": int(panel[column].notna().sum()),
                    "formation_coverage": float(panel[column].notna().mean()),
                    "mean_size_correlation": _mean_cross_sectional_correlation(
                        panel, column, "size_score"
                    ),
                    "mean_lowvol_correlation": _mean_cross_sectional_correlation(
                        panel, column, "lowvol_score"
                    ),
                }
            )
    diagnostics = pd.DataFrame(diagnostic_rows)
    return panel, diagnostics
