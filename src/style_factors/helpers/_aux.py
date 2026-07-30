"""Auxiliary stock-day panel merge for style_factors.

Forward-fills an auxiliary (symbol, trade_date) table into the factor panel
within each stock.  Used by the new-factor helpers (moneyflow_ths /
holder_structure / limit_list / daily_basic extras).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _assign_aux_panel(
    group: pd.DataFrame,
    aux_by_symbol: dict[str, pd.DataFrame],
    columns: list[str],
) -> pd.DataFrame:
    """Forward-fill an auxiliary stock-day table into one symbol's panel rows.

    Used for moneyflow_ths / holder_structure / limit_list which are keyed by
    (symbol, trade_date) but may have gaps; we carry the last observed value
    forward within each stock so the factor is defined on more dates.
    """
    if not aux_by_symbol:
        return group
    group = group.copy()
    symbol = group["symbol"].iloc[0]
    aux = aux_by_symbol.get(symbol)
    if aux is None or aux.empty:
        for column in columns:
            group[column] = np.nan
        return group
    aux = aux.sort_values("trade_date")
    td = group["trade_date"].to_numpy()
    aux_dates = aux["trade_date"].to_numpy()
    pos = np.searchsorted(aux_dates, td, side="right") - 1
    valid = pos >= 0
    for column in columns:
        values = np.full(len(group), np.nan)
        if column in aux.columns:
            src = aux[column].to_numpy()
            values[valid] = src[pos[valid]]
        group[column] = values
    return group


def _merge_aux(
    df: pd.DataFrame,
    aux: pd.DataFrame | None,
    columns: list[str],
) -> pd.DataFrame:
    if aux is None or aux.empty:
        for column in columns:
            df[column] = np.nan
        return df
    aux = aux.copy()
    aux["trade_date"] = pd.to_datetime(aux["trade_date"])
    by_symbol = {
        symbol: g.drop(columns=["symbol"]).sort_values("trade_date")
        for symbol, g in aux.groupby("symbol", sort=False)
    }
    grouped = [
        _assign_aux_panel(group, by_symbol, columns)
        for _, group in df.groupby("symbol", sort=False)
    ]
    return pd.concat(grouped, ignore_index=True)
