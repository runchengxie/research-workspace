"""Shared backtest metrics for daily return series.

Zero-dependency module (numpy only). Can be used from any project:

    from _shared.metrics import compute_metrics, sharpe_ratio, max_drawdown

    rets = np.array([0.001, -0.002, 0.003, ...])
    m = compute_metrics(rets, annual_factor=252)
    print(m["sharpe"], m["max_drawdown"], m["sortino"])
"""

from __future__ import annotations

import numpy as np


def max_drawdown(returns: np.ndarray) -> float:
    """Maximum drawdown from peak.

    Returns a negative number (e.g. -0.15 for 15% drawdown).
    """
    if len(returns) == 0:
        return 0.0
    nav = np.cumprod(1 + returns)
    return float(np.min(nav / np.maximum.accumulate(nav)) - 1)


def sharpe_ratio(returns: np.ndarray, annual_factor: float = 252) -> float:
    """Annualised Sharpe ratio."""
    if len(returns) < 2:
        return 0.0
    mu = float(np.mean(returns))
    sigma = float(np.std(returns, ddof=1))
    if sigma == 0:
        return 0.0
    return mu / sigma * np.sqrt(annual_factor)


def sortino_ratio(returns: np.ndarray, annual_factor: float = 252) -> float:
    """Annualised Sortino ratio (downside deviation only)."""
    if len(returns) < 2:
        return 0.0
    mu = float(np.mean(returns))
    downside = np.minimum(returns, 0.0)
    downside_std = float(np.sqrt(np.mean(downside**2)))
    if downside_std == 0:
        return 0.0
    return mu / downside_std * np.sqrt(annual_factor)


def calmar_ratio(returns: np.ndarray, annual_factor: float = 252) -> float:
    """Annualised return / abs(max drawdown)."""
    dd = max_drawdown(returns)
    if dd >= 0 or len(returns) < 2:
        return 0.0
    total = float(np.prod(1 + returns) - 1)
    n = len(returns)
    ann = (1 + total) ** (annual_factor / n) - 1 if n > 0 else 0.0
    return ann / abs(dd)


def hit_rate(returns: np.ndarray) -> float:
    """Fraction of periods with positive return."""
    if len(returns) == 0:
        return 0.0
    return float(np.mean(returns > 0))


def drawdown_analysis(returns: np.ndarray) -> dict:
    """Maximum drawdown timing: duration (in periods) and recovery (in periods).

    Returns:
        {max_drawdown, trough_index, peak_index, duration, recovery, recovered}
        recovery is NaN if still underwater at end of series.
    """
    if len(returns) == 0:
        return {
            "max_drawdown": 0.0,
            "trough_index": 0,
            "peak_index": 0,
            "duration": 0,
            "recovery": np.nan,
            "recovered": False,
        }

    nav = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(nav)
    dd = nav / running_max - 1
    trough = int(np.argmin(dd))

    peak_value = float(running_max[trough])
    peak_candidates = np.flatnonzero(np.isclose(nav[:trough + 1], peak_value))
    peak = int(peak_candidates[-1]) if len(peak_candidates) > 0 else 0

    duration = trough - peak

    post_nav = nav[trough:]
    recovery_candidates = np.flatnonzero(post_nav >= peak_value)
    if len(recovery_candidates) == 0:
        recovery = np.nan
        recovered = False
    else:
        recovery = int(recovery_candidates[0])
        recovered = True

    return {
        "max_drawdown": float(dd[trough]),
        "trough_index": trough,
        "peak_index": peak,
        "duration": duration,
        "recovery": recovery,
        "recovered": recovered,
    }


def value_at_risk(returns: np.ndarray, pct: float = 5.0) -> float:
    """VaR at given percentile (default 5%)."""
    if len(returns) == 0:
        return 0.0
    return float(np.percentile(returns, pct))


def cvar(returns: np.ndarray, pct: float = 5.0) -> float:
    """Conditional VaR (expected shortfall) at given percentile."""
    if len(returns) == 0:
        return 0.0
    threshold = np.percentile(returns, pct)
    tail = returns[returns <= threshold]
    if len(tail) == 0:
        return 0.0
    return float(tail.mean())


def compute_metrics(returns: np.ndarray, annual_factor: float = 252) -> dict:
    """Compute all common backtest metrics for a daily return series.

    Args:
        returns: 1-d numpy array of period returns (e.g. daily).
        annual_factor: periods per year (252 for daily, 12 for monthly).

    Returns:
        dict with: total_return, ann_return, ann_vol, sharpe, sortino, calmar,
                   max_drawdown, hit_rate, skew, kurtosis, var_95, cvar_95,
                   n_periods.
    """
    rets = np.asarray(returns, dtype=float)
    rets = rets[np.isfinite(rets)]

    n = len(rets)
    if n == 0:
        return {
            "n_periods": 0,
            "total_return": 0.0,
            "ann_return": 0.0,
            "ann_vol": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "calmar": 0.0,
            "max_drawdown": 0.0,
            "hit_rate": 0.0,
            "skew": 0.0,
            "kurtosis": 0.0,
            "var_95": 0.0,
            "cvar_95": 0.0,
        }

    total = float(np.prod(1 + rets) - 1)
    ann = (1 + total) ** (annual_factor / n) - 1 if n > 0 else 0.0
    vol = float(np.std(rets, ddof=1)) * np.sqrt(annual_factor) if n > 1 else 0.0
    sh = sharpe_ratio(rets, annual_factor)
    so = sortino_ratio(rets, annual_factor)
    ca = calmar_ratio(rets, annual_factor)
    dd = max_drawdown(rets)
    hr = hit_rate(rets)

    # Distribution
    skew = float(_safe_skew(rets))
    kurt = float(_safe_kurtosis(rets))
    var95 = value_at_risk(rets, 5.0)
    cvar95 = cvar(rets, 5.0)

    return {
        "n_periods": n,
        "total_return": total,
        "ann_return": ann,
        "ann_vol": vol,
        "sharpe": sh,
        "sortino": so,
        "calmar": ca,
        "max_drawdown": dd,
        "hit_rate": hr,
        "skew": skew,
        "kurtosis": kurt,
        "var_95": var95,
        "cvar_95": cvar95,
    }


def _safe_skew(a: np.ndarray) -> float:
    if len(a) < 3:
        return 0.0
    n = len(a)
    m2 = np.mean((a - a.mean())**2)
    m3 = np.mean((a - a.mean())**3)
    if m2 == 0:
        return 0.0
    # Adjusted sample skewness
    return float((n * (n - 1))**0.5 / (n - 2) * m3 / m2**1.5)


def _safe_kurtosis(a: np.ndarray) -> float:
    if len(a) < 4:
        return 0.0
    n = len(a)
    m2 = np.mean((a - a.mean())**2)
    m4 = np.mean((a - a.mean())**4)
    if m2 == 0:
        return 0.0
    # Excess kurtosis
    return float((n - 1) / ((n - 2) * (n - 3)) * ((n + 1) * m4 / m2**2 - 3 * (n - 1)))
