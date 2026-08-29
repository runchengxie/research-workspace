"""Double-sort and cross-sectional inference for microcap mechanism research."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .size_turnover_double_sort import build_double_sort

REGRESSORS = (
    "log_market_cap",
    "illiquidity_60d",
    "max_return_21d",
    "ivol_60d",
    "turnover_lagged_mean_60d",
    "factor_quality",
)

DOUBLE_SORT_CHARACTERISTICS = (
    "illiquidity_60d",
    "max_return_21d",
    "ivol_60d",
    "turnover_lagged_mean_60d",
    "factor_quality",
)


def _require_unique(frame: pd.DataFrame, *, label: str) -> None:
    required = {"trade_date", "symbol"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")
    if frame.duplicated(["trade_date", "symbol"]).any():
        raise ValueError(f"{label} contains duplicate trade_date/symbol keys")


def build_microcap_decomposition_panel(
    characteristics: pd.DataFrame,
    turnover: pd.DataFrame,
    quality: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Join the frozen characteristic set and report formation-date completeness."""
    _require_unique(characteristics, label="characteristics")
    _require_unique(turnover, label="turnover")
    _require_unique(quality, label="quality")
    required_characteristics = {
        "log_market_cap",
        "illiquidity_60d",
        "max_return_21d",
        "ivol_60d",
    }
    missing = sorted(required_characteristics - set(characteristics.columns))
    if missing:
        raise ValueError("characteristics is missing required columns: " + ", ".join(missing))
    if "turnover_lagged_mean_60d" not in turnover.columns:
        raise ValueError("turnover is missing turnover_lagged_mean_60d")
    if "factor_quality" not in quality.columns:
        raise ValueError("quality is missing factor_quality")

    panel = characteristics.merge(
        turnover[["trade_date", "symbol", "turnover_lagged_mean_60d"]],
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    panel = panel.merge(
        quality[["trade_date", "symbol", "factor_quality"]],
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    panel = panel.sort_values(["trade_date", "symbol"]).reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for date, group in panel.groupby("trade_date", sort=True):
        row: dict[str, object] = {
            "formation_date": pd.Timestamp(date),
            "rows": len(group),
        }
        complete = pd.Series(True, index=group.index)
        for column in REGRESSORS:
            valid = pd.to_numeric(group[column], errors="coerce").notna()
            row[f"missing_{column}"] = int((~valid).sum())
            complete &= valid
        row["complete_case_rows"] = int(complete.sum())
        rows.append(row)
    return panel, pd.DataFrame(rows)


def build_microcap_double_sorts(
    panel: pd.DataFrame,
    daily_returns: pd.DataFrame,
    *,
    formation_dates: pd.DatetimeIndex,
    bucket_count: int = 5,
) -> pd.DataFrame:
    """Run the five frozen size × characteristic double sorts."""
    rows: list[pd.DataFrame] = []
    for characteristic in DOUBLE_SORT_CHARACTERISTICS:
        result = build_double_sort(
            panel,
            daily_returns,
            formation_dates=formation_dates,
            first_column="log_market_cap",
            second_column=characteristic,
            bucket_count=bucket_count,
        )
        result.insert(1, "second_characteristic", characteristic)
        rows.append(result)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _forward_returns(
    daily_returns: pd.DataFrame,
    formation_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    returns = daily_returns.copy()
    returns.index = pd.to_datetime(returns.index).normalize()
    dates = pd.DatetimeIndex(formation_dates).normalize().sort_values().unique()
    rows: list[pd.DataFrame] = []
    for index, formation_date in enumerate(dates):
        next_date = dates[index + 1] if index + 1 < len(dates) else returns.index.max()
        window = returns.loc[(returns.index > formation_date) & (returns.index <= next_date)]
        forward = (1.0 + window).prod(axis=0, min_count=1) - 1.0
        rows.append(
            pd.DataFrame(
                {
                    "trade_date": formation_date,
                    "symbol": forward.index.astype(str),
                    "forward_return": forward.to_numpy(dtype=float),
                }
            )
        )
    if not rows:
        return pd.DataFrame(columns=["trade_date", "symbol", "forward_return"])
    return pd.concat(rows, ignore_index=True)


def _winsorized_zscore(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    lower = numeric.quantile(0.01)
    upper = numeric.quantile(0.99)
    clipped = numeric.clip(lower=lower, upper=upper)
    std = clipped.std()
    if not np.isfinite(std) or std <= 0:
        return pd.Series(np.nan, index=values.index, dtype=float)
    return (clipped - clipped.mean()) / std


def run_microcap_cross_sectional_regressions(
    panel: pd.DataFrame,
    daily_returns: pd.DataFrame,
    *,
    formation_dates: pd.DatetimeIndex,
    regressors: Sequence[str] = REGRESSORS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run one OLS cross-section per formation date with frozen preprocessing."""
    missing = sorted(set(regressors) - set(panel.columns))
    if missing:
        raise ValueError("panel is missing regressors: " + ", ".join(missing))
    forward = _forward_returns(daily_returns, formation_dates)
    work = panel.merge(
        forward,
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )

    coefficient_rows: list[dict[str, object]] = []
    diagnostic_rows: list[dict[str, object]] = []
    for date, group in work.groupby("trade_date", sort=True):
        cross = group.copy()
        z_columns: list[str] = []
        for column in regressors:
            zcol = f"z_{column}"
            cross[zcol] = _winsorized_zscore(cross[column])
            z_columns.append(zcol)
        required = ["forward_return", *z_columns]
        complete = cross.dropna(subset=required)
        diagnostic = {
            "formation_date": pd.Timestamp(date),
            "input_rows": len(cross),
            "complete_case_rows": len(complete),
            "dropped_rows": len(cross) - len(complete),
        }
        if len(complete) <= len(z_columns) + 1:
            diagnostic["status"] = "insufficient_cross_section"
            diagnostic_rows.append(diagnostic)
            continue

        design = sm.add_constant(complete[z_columns], has_constant="add")
        fit = sm.OLS(complete["forward_return"], design).fit()
        diagnostic["status"] = "ok"
        diagnostic["r_squared"] = float(fit.rsquared)
        diagnostic_rows.append(diagnostic)
        for coefficient, value in fit.params.items():
            coefficient_rows.append(
                {
                    "formation_date": pd.Timestamp(date),
                    "coefficient": str(coefficient),
                    "value": float(value),
                    "nobs": int(fit.nobs),
                    "r_squared": float(fit.rsquared),
                }
            )
    return pd.DataFrame(coefficient_rows), pd.DataFrame(diagnostic_rows)


def summarize_cross_sectional_coefficients(
    coefficients: pd.DataFrame,
    *,
    hac_maxlags: int = 3,
) -> pd.DataFrame:
    """Summarize date-level coefficients with an intercept-only HAC regression."""
    required = {"formation_date", "coefficient", "value", "r_squared"}
    missing = sorted(required - set(coefficients.columns))
    if missing:
        raise ValueError("coefficients is missing required columns: " + ", ".join(missing))
    if hac_maxlags < 0:
        raise ValueError("hac_maxlags must be non-negative")

    rows: list[dict[str, object]] = []
    for coefficient, group in coefficients.groupby("coefficient", sort=True):
        ordered = group.sort_values("formation_date")
        values = pd.to_numeric(ordered["value"], errors="coerce").dropna().to_numpy()
        if len(values) < 2:
            continue
        fit = sm.OLS(values, np.ones((len(values), 1))).fit(
            cov_type="HAC",
            cov_kwds={"maxlags": hac_maxlags},
        )
        standard_error = float(fit.bse[0])
        mean = float(fit.params[0])
        rows.append(
            {
                "coefficient": coefficient,
                "coefficient_mean": mean,
                "hac_standard_error": standard_error,
                "t_stat": mean / standard_error if standard_error > 0 else np.nan,
                "formation_count": len(values),
                "positive_share": float((values > 0).mean()),
                "coefficient_std": float(values.std(ddof=1)),
                "median_r_squared": float(pd.to_numeric(ordered["r_squared"]).median()),
                "hac_maxlags": hac_maxlags,
            }
        )
    return pd.DataFrame(rows)


__all__ = [
    "DOUBLE_SORT_CHARACTERISTICS",
    "REGRESSORS",
    "build_microcap_decomposition_panel",
    "build_microcap_double_sorts",
    "run_microcap_cross_sectional_regressions",
    "summarize_cross_sectional_coefficients",
]
