"""Strategy attribution — OLS regression of strategy returns against factor returns."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _factor_return_frame(factor_results: dict) -> pd.DataFrame:
    factor_df = pd.DataFrame(
        {name: res["long_short"].dropna() for name, res in factor_results.items()}
    )
    if not factor_df.empty:
        factor_df.index = factor_df.index.normalize()
    return factor_df


def _merge_strategy_and_factors(
    factor_results: dict,
    strategy_returns: pd.Series | None,
    strategy_name: str,
) -> pd.DataFrame | None:
    if strategy_returns is None or len(strategy_returns) < 20:
        return None

    sr = strategy_returns.dropna().copy()
    if isinstance(sr.index, pd.DatetimeIndex):
        sr.index = sr.index.normalize()

    factor_df = _factor_return_frame(factor_results)
    if factor_df.empty:
        return None
    return factor_df.join(sr.rename(strategy_name), how="inner")


def _ols_attribution(
    merged: pd.DataFrame,
    *,
    factor_columns: list[str],
    strategy_name: str,
) -> dict:
    y = merged[strategy_name]
    X = merged[factor_columns]

    X_aug = np.column_stack([np.ones(len(X)), X.values])
    beta = np.linalg.lstsq(X_aug, y.values, rcond=None)[0]
    intercept, coefs = beta[0], beta[1:]

    y_pred = X_aug @ beta
    residuals = y.values - y_pred
    r2 = 1 - residuals.var() / y.var() if y.var() > 0 else 0

    n_years = (y.index.max() - y.index.min()).days / 365.25
    ann_ret = ((1 + y.mean()) ** 252 - 1) * 100
    period_ret_decimal = (1 + y).prod() - 1
    period_ret = period_ret_decimal * 100
    geometric_ann_ret = (1 + period_ret_decimal) ** (252 / len(y)) - 1
    ann_alpha = ((1 + intercept) ** 252 - 1) * 100

    return {
        "days": int(len(y)),
        "years": round(float(n_years), 1),
        "r_squared": round(float(r2), 4),
        "period_return": round(float(period_ret), 2),
        "annual_return": round(float(ann_ret), 2),
        "geometric_annual_return": round(float(geometric_ann_ret * 100), 2),
        "annual_alpha": round(float(ann_alpha), 2),
        "intercept": round(float(intercept * 252 * 100), 4),
        "betas": {
            str(factor): round(float(coef), 6)
            for factor, coef in zip(factor_columns, coefs, strict=True)
        },
        "residual_mean": float(pd.Series(residuals).mean()),
    }


def _select_complete_factor_sample(
    merged: pd.DataFrame,
    *,
    factor_columns: list[str],
    strategy_name: str,
    min_coverage: float = 0.8,
) -> tuple[pd.DataFrame, list[str], dict[str, float], list[str]]:
    """Select sufficiently covered factors and a complete-case OLS sample."""
    coverage = {column: float(merged[column].notna().mean()) for column in factor_columns}
    selected = [column for column in factor_columns if coverage[column] >= min_coverage]
    excluded = [column for column in factor_columns if column not in selected]
    if not selected:
        return pd.DataFrame(), selected, coverage, excluded
    sample = merged[[*selected, strategy_name]].dropna()
    return sample, selected, coverage, excluded


def run_strategy_attribution(
    factor_results: dict,
    strategy_returns: pd.Series | None = None,
    strategy_name: str = "strategy",
) -> dict:
    """Regress strategy daily returns against factor long-short returns."""
    merged = _merge_strategy_and_factors(factor_results, strategy_returns, strategy_name)
    if merged is None:
        return {"error": "no strategy returns provided"}
    if len(merged) < 20:
        return {"error": "insufficient overlapping dates"}

    factor_columns = [column for column in factor_results if column in merged.columns]
    sample, factor_columns, coverage, excluded = _select_complete_factor_sample(
        merged,
        factor_columns=factor_columns,
        strategy_name=strategy_name,
    )
    if len(sample) < 20:
        return {"error": "insufficient complete-case factor overlap"}
    result = {
        "strategy": strategy_name,
        "factor_coverage": {factor: round(value, 4) for factor, value in coverage.items()},
        "excluded_factors": excluded,
        "overlap_start": sample.index.min().date().isoformat(),
        "overlap_end": sample.index.max().date().isoformat(),
    }
    result.update(
        _ols_attribution(
            sample,
            factor_columns=factor_columns,
            strategy_name=strategy_name,
        )
    )
    result.pop("residual_mean", None)
    return result


def run_yearly_strategy_attribution(
    factor_results: dict,
    strategy_returns: pd.Series | None = None,
    strategy_name: str = "strategy",
    *,
    min_days: int = 50,
) -> pd.DataFrame:
    """Regress strategy returns against factor returns independently by calendar year."""
    merged = _merge_strategy_and_factors(factor_results, strategy_returns, strategy_name)
    if merged is None or len(merged) < min_days:
        return pd.DataFrame()

    rows = []
    for year, group in merged.groupby(merged.index.year):
        if len(group) < min_days:
            continue
        candidate_columns = [column for column in factor_results if column in group.columns]
        sample, factor_columns, _coverage, _excluded = _select_complete_factor_sample(
            group,
            factor_columns=candidate_columns,
            strategy_name=strategy_name,
        )
        if len(sample) < min_days or not factor_columns:
            continue
        attribution = _ols_attribution(
            sample,
            factor_columns=factor_columns,
            strategy_name=strategy_name,
        )
        row = {
            "year": int(year),
            "days": attribution["days"],
            "period_return": attribution["period_return"],
            "annual_return": attribution["annual_return"],
            "geometric_annual_return": attribution["geometric_annual_return"],
            "r_squared": attribution["r_squared"],
            "annual_alpha": attribution["annual_alpha"],
            "intercept": attribution["intercept"],
        }
        for factor, beta in attribution["betas"].items():
            factor_ret = ((1 + sample[factor]).prod() - 1) * 100
            row[f"beta_{factor}"] = beta
            row[f"factor_return_{factor}"] = round(float(factor_ret), 2)
            row[f"contribution_{factor}"] = round(float(beta * factor_ret), 2)
        rows.append(row)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
