"""Factor computation from daily, valuation, and optional fundamental data."""

from __future__ import annotations

import numpy as np
import pandas as pd

FACTOR_COLS = [
    "factor_size",
    "factor_value",
    "factor_momentum",
    "factor_quality",
    "factor_lowvol",
    "factor_growth",
    "factor_leverage",
    "factor_beta",
    "factor_liquidity",
]

FUNDAMENTAL_COLS = ["roe", "roa", "netprofit_yoy", "or_yoy", "debt_to_assets"]


def _base_frame(daily: pd.DataFrame, basics: pd.DataFrame) -> pd.DataFrame:
    daily_cols = ["trade_date", "symbol", "close", "pct_chg", "amount"]
    basic_cols = ["trade_date", "symbol", "total_mv", "pb", "pe_ttm", "turnover_rate"]
    df = daily[daily_cols].merge(
        basics[basic_cols],
        on=["trade_date", "symbol"],
        how="left",
    )
    df = df[(df["total_mv"] > 0) & (df["amount"] > 0)].copy()
    return df.sort_values(["symbol", "trade_date"]).reset_index(drop=True)


def _fundamental_columns(fina: pd.DataFrame) -> list[str]:
    return [column for column in FUNDAMENTAL_COLS if column in fina.columns]


def _prepare_fundamentals(fina: pd.DataFrame) -> pd.DataFrame:
    aligned = fina.rename(columns={"ann_date": "align_date", "symbol": "_sym"}).copy()
    aligned["align_date"] = pd.to_datetime(aligned["align_date"])
    aligned = aligned.dropna(subset=["align_date"])
    aligned = aligned.sort_values(["_sym", "align_date"])
    aligned = aligned.drop_duplicates(["_sym", "align_date"], keep="last")
    return aligned.set_index("align_date")


def _assign_symbol_fundamentals(
    group: pd.DataFrame,
    symbol_fundamentals: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    if symbol_fundamentals.empty:
        return group

    group = group.copy()
    symbol_fundamentals = symbol_fundamentals.sort_index()
    report_dates = symbol_fundamentals.index.to_numpy()
    trade_dates = group["trade_date"].to_numpy()
    positions = np.searchsorted(report_dates, trade_dates, side="right") - 1
    valid = positions >= 0
    for column in columns:
        values = np.full(len(group), np.nan)
        source_values = symbol_fundamentals[column].to_numpy()
        values[valid] = source_values[positions[valid]]
        group[column] = values
    return group


def _merge_fundamentals(
    df: pd.DataFrame,
    fina: pd.DataFrame | None,
) -> tuple[pd.DataFrame, bool]:
    if fina is None or fina.empty:
        return df, False

    columns = _fundamental_columns(fina)
    if not columns or "ann_date" not in fina.columns or "symbol" not in fina.columns:
        return df, False

    df = df.copy()
    df["_sym"] = df["symbol"].str.replace(r"\.(SZ|SH|BJ)$", "", regex=True)
    df["_idx"] = np.arange(len(df))
    aligned = _prepare_fundamentals(fina)

    grouped = [
        _assign_symbol_fundamentals(group, aligned[aligned["_sym"] == symbol], columns)
        for symbol, group in df.groupby("_sym", sort=False)
    ]
    merged = pd.concat(grouped, ignore_index=True)
    merged = merged.sort_values("_idx").drop(columns=["_idx", "_sym"])
    return merged, True


def _add_core_factors(df: pd.DataFrame) -> pd.DataFrame:
    df["factor_size"] = np.log(df["total_mv"] + 1)

    df["pb_clean"] = df["pb"].clip(lower=0.01, upper=100)
    df["factor_value"] = 1.0 / df["pb_clean"]

    df["pe_clean"] = df["pe_ttm"].clip(lower=1, upper=500)
    df["factor_quality"] = 1.0 / df["pe_clean"]

    df["ret_1d"] = df.groupby("symbol")["close"].pct_change()
    df["factor_momentum"] = df.groupby("symbol")["close"].transform(
        lambda series: series.pct_change(periods=21).shift(1)
    )

    df["vol20"] = df.groupby("symbol")["ret_1d"].transform(
        lambda series: series.rolling(21, min_periods=10).std().shift(1)
    )
    df["factor_lowvol"] = -df["vol20"]
    return df


def _add_fundamental_factors(df: pd.DataFrame, *, has_fina: bool) -> pd.DataFrame:
    if not has_fina:
        return df
    if {"netprofit_yoy", "or_yoy"} <= set(df.columns):
        df["g_np"] = df["netprofit_yoy"].clip(lower=-300, upper=500)
        df["g_or"] = df["or_yoy"].clip(lower=-200, upper=500)
        df["factor_growth"] = df[["g_np", "g_or"]].mean(axis=1)
    if "debt_to_assets" in df.columns:
        df["factor_leverage"] = -df["debt_to_assets"].clip(lower=0, upper=500)
    return df


def _add_beta_factor(df: pd.DataFrame) -> pd.DataFrame:
    df["ret"] = df["pct_chg"] / 100.0
    df["mkt_ret"] = df.groupby("trade_date")["ret"].transform("mean")
    df["cov_252"] = (
        df.groupby("symbol")[["ret", "mkt_ret"]]
        .apply(
            lambda group: group["ret"].rolling(252, min_periods=126).cov(group["mkt_ret"]),
            include_groups=False,
        )
        .reset_index(level=0, drop=True)
    )
    df["var_252"] = df.groupby("symbol")["mkt_ret"].transform(
        lambda series: series.rolling(252, min_periods=126).var()
    )
    raw_beta = df["cov_252"] / df["var_252"].replace(0, np.nan)
    df["factor_beta"] = -raw_beta
    return df


def _add_liquidity_factor(df: pd.DataFrame) -> pd.DataFrame:
    df["turn_clean"] = df["turnover_rate"].clip(lower=0.01, upper=100)
    df["factor_liquidity"] = -df["turn_clean"]
    return df


def _standardize_factors(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=FACTOR_COLS[:5]).copy()
    active = [column for column in FACTOR_COLS if column in df.columns]
    for column in active:
        df[column] = df.groupby("trade_date")[column].transform(
            lambda series: series.clip(
                lower=series.quantile(0.01),
                upper=series.quantile(0.99),
            )
        )
    for column in active:
        mean = df.groupby("trade_date")[column].transform("mean")
        std = df.groupby("trade_date")[column].transform("std")
        df[f"{column}_z"] = (df[column] - mean) / std.replace(0, np.nan)
    return df


def compute_factors(
    daily: pd.DataFrame,
    basics: pd.DataFrame,
    fina: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Compute style factors per stock per date.

    If fina_indicator data is provided, Growth and Leverage are aligned by
    announcement date so the factor frame does not look ahead.
    """
    df = _base_frame(daily, basics)
    df, has_fina = _merge_fundamentals(df, fina)
    df = _add_core_factors(df)
    df = _add_fundamental_factors(df, has_fina=has_fina)
    df = _add_beta_factor(df)
    df = _add_liquidity_factor(df)
    df = _standardize_factors(df)
    active = [column for column in FACTOR_COLS if column in df.columns]
    n_factors = len(active)
    print(
        f"[factors] {df['trade_date'].min().date()} ~ {df['trade_date'].max().date()}, "
        f"{len(df)} rows, {df['symbol'].nunique()} stocks, {n_factors} factors"
    )
    return df
