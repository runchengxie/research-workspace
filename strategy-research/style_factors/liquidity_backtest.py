"""Portfolio diagnostics for alternative low-turnover signal definitions."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from portfolio_backtester.style_factors_backtest import build_quantile_portfolio_returns

from .liquidity_signals import liquidity_signal_columns


def _geometric_annual_return(returns: pd.Series, trading_days: int = 252) -> float:
    clean = returns.dropna()
    if clean.empty:
        return float("nan")
    cumulative = float((1 + clean).prod())
    if cumulative <= 0:
        return float("nan")
    return (cumulative ** (trading_days / len(clean)) - 1) * 100


def _max_drawdown(returns: pd.Series) -> float:
    clean = returns.dropna()
    if clean.empty:
        return float("nan")
    cumulative = (1 + clean).cumprod()
    drawdown = cumulative / cumulative.cummax() - 1
    return float(drawdown.min() * 100)


def _series_metrics(returns: pd.Series) -> dict[str, float | int]:
    clean = returns.dropna()
    if clean.empty:
        return {
            "days": 0,
            "cumulative_return": float("nan"),
            "geometric_annual_return": float("nan"),
            "annual_volatility": float("nan"),
            "sharpe": float("nan"),
            "max_drawdown": float("nan"),
        }
    annual_volatility = float(clean.std() * np.sqrt(252) * 100)
    sharpe = float(clean.mean() / clean.std() * np.sqrt(252)) if clean.std() > 0 else float("nan")
    return {
        "days": len(clean),
        "cumulative_return": float(((1 + clean).prod() - 1) * 100),
        "geometric_annual_return": _geometric_annual_return(clean),
        "annual_volatility": annual_volatility,
        "sharpe": sharpe,
        "max_drawdown": _max_drawdown(clean),
    }


def _positive_year_ratio(returns: pd.Series) -> float:
    clean = returns.dropna()
    if clean.empty:
        return float("nan")
    yearly = clean.resample("YE").apply(lambda values: (1 + values).prod() - 1)
    return float((yearly > 0).mean())


def _monotonicity(quintile_returns: list[float]) -> tuple[float, int]:
    values = np.asarray(quintile_returns, dtype=float)
    if not np.isfinite(values).all():
        return float("nan"), 0
    ranks = pd.Series(values).rank(method="average").to_numpy()
    spearman = float(np.corrcoef(np.arange(1, len(values) + 1), ranks)[0, 1])
    improving_steps = int(np.sum(np.diff(values) > 0))
    return spearman, improving_steps


def build_liquidity_portfolios(
    signal_panel: pd.DataFrame,
    daily: pd.DataFrame,
    formation_dates: pd.DatetimeIndex,
) -> dict[str, dict[str, object]]:
    return build_quantile_portfolio_returns(
        signal_panel,
        daily,
        formation_dates,
        liquidity_signal_columns(),
        n_quantiles=5,
        requested_quantiles=(1, 2, 3, 4, 5),
        include_universe=True,
    )


def summarize_liquidity_portfolios(
    portfolios: dict[str, dict[str, object]],
    signal_diagnostics: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, object]] = []
    quintile_rows: list[dict[str, object]] = []
    baseline = portfolios.get("turnover_1d", {}).get("long_short", pd.Series(dtype=float))

    diagnostics = signal_diagnostics.set_index("variant")
    for variant, result in portfolios.items():
        quantiles = result["quantiles"]
        quantile_annual_returns: list[float] = []
        for quantile in range(1, 6):
            returns = quantiles[quantile]
            metrics = _series_metrics(returns)
            quantile_annual_returns.append(float(metrics["geometric_annual_return"]))
            quintile_rows.append(
                {
                    "variant": variant,
                    "quantile": quantile,
                    **metrics,
                }
            )

        monotonicity, improving_steps = _monotonicity(quantile_annual_returns)
        long_metrics = _series_metrics(result["long"])
        short_metrics = _series_metrics(result["short"])
        spread_metrics = _series_metrics(result["long_short"])
        excess_metrics = _series_metrics(result["long_excess"])
        paired = pd.concat({"variant": result["long_short"], "baseline": baseline}, axis=1).dropna()
        baseline_correlation = (
            float(paired["variant"].corr(paired["baseline"])) if len(paired) > 1 else float("nan")
        )
        signal_row = diagnostics.loc[variant].to_dict()
        summary_rows.append(
            {
                "variant": variant,
                **signal_row,
                "days": spread_metrics["days"],
                "baseline_return_correlation": baseline_correlation,
                "monotonicity_spearman": monotonicity,
                "improving_quintile_steps": improving_steps,
                "q1_annual_return": quantile_annual_returns[0],
                "q2_annual_return": quantile_annual_returns[1],
                "q3_annual_return": quantile_annual_returns[2],
                "q4_annual_return": quantile_annual_returns[3],
                "q5_annual_return": quantile_annual_returns[4],
                "long_annual_return": long_metrics["geometric_annual_return"],
                "long_sharpe": long_metrics["sharpe"],
                "long_max_drawdown": long_metrics["max_drawdown"],
                "high_turnover_annual_return": short_metrics["geometric_annual_return"],
                "long_excess_annual_return": excess_metrics["geometric_annual_return"],
                "long_short_annual_return": spread_metrics["geometric_annual_return"],
                "long_short_sharpe": spread_metrics["sharpe"],
                "long_short_max_drawdown": spread_metrics["max_drawdown"],
                "long_short_positive_year_ratio": _positive_year_ratio(result["long_short"]),
            }
        )
    return pd.DataFrame(summary_rows), pd.DataFrame(quintile_rows)


def daily_liquidity_output(portfolios: dict[str, dict[str, object]]) -> pd.DataFrame:
    series: dict[str, pd.Series] = {}
    for variant, result in portfolios.items():
        for quantile, returns in result["quantiles"].items():
            series[f"{variant}_q{quantile}"] = returns
        series[f"{variant}_long_short"] = result["long_short"]
        series[f"{variant}_universe"] = result["universe"]
        series[f"{variant}_long_excess"] = result["long_excess"]
    output = pd.DataFrame(series).sort_index()
    output.index.name = "trade_date"
    return output


def compare_baseline_returns(
    observed: pd.Series,
    baseline_artifacts: Path | None,
) -> dict[str, object]:
    if baseline_artifacts is None:
        return {"performed": False}
    path = baseline_artifacts / "factor_liquidity_daily.csv"
    if not path.is_file():
        raise FileNotFoundError(f"baseline liquidity return file does not exist: {path}")
    frame = pd.read_csv(path, parse_dates=[0], index_col=0)
    if frame.empty:
        raise ValueError(f"baseline liquidity return file is empty: {path}")
    expected = frame.iloc[:, 0]
    expected.index = pd.DatetimeIndex(expected.index).normalize()
    paired = pd.concat({"observed": observed, "expected": expected}, axis=1).dropna()
    if paired.empty:
        raise ValueError("baseline tie-out has no common observations")
    differences = (paired["observed"] - paired["expected"]).abs()
    maximum_difference = float(differences.max())
    return {
        "performed": True,
        "baseline_file": str(path),
        "common_days": len(paired),
        "maximum_absolute_difference": maximum_difference,
        "passed": maximum_difference <= 1e-12,
    }
