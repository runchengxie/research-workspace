"""Adapters from style-factor research targets to portfolio-backtester."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from portfolio_backtester.backends import (
    NativePositionReplayBackend,
    NativePositionReplayRequest,
)
from portfolio_backtester.contracts import assert_positions_by_rebalance_frame
from portfolio_backtester.position_backtest import PositionBacktestConfig


def targets_to_positions_by_rebalance(
    targets: Mapping[Any, Mapping[str, float]] | pd.DataFrame,
    *,
    entry_dates: Mapping[Any, Any] | None = None,
    default_side: str = "long",
) -> pd.DataFrame:
    """Convert research targets to the owner package's position contract.

    Mapping inputs use ``rebalance_date -> symbol -> weight``. DataFrame inputs
    must contain ``rebalance_date``, ``symbol`` and ``weight``; ``target_weight``
    is accepted as a compatibility alias. The adapter deliberately does not
    normalize weights, so explicit cash shortfall survives the handoff.
    """
    out = (
        _target_frame_from_mapping(targets, entry_dates=entry_dates, default_side=default_side)
        if not isinstance(targets, pd.DataFrame)
        else _copy_target_frame(targets, entry_dates=entry_dates)
    )

    required = {"rebalance_date", "symbol", "weight"}
    missing = sorted(required - set(out.columns))
    if missing:
        raise ValueError("targets are missing required columns: " + ", ".join(missing))
    if out.empty:
        return pd.DataFrame(
            columns=["rebalance_date", "entry_date", "symbol", "weight", "side"]
        )

    out = out.copy()
    out["rebalance_date"] = pd.to_datetime(out["rebalance_date"], errors="coerce").dt.normalize()
    if out["rebalance_date"].isna().any():
        raise ValueError("rebalance_date must be date-like")
    if "entry_date" in out.columns:
        out["entry_date"] = pd.to_datetime(out["entry_date"], errors="coerce").dt.normalize()
    else:
        out["entry_date"] = pd.NaT
    out["symbol"] = out["symbol"].astype("string").str.strip()
    out["weight"] = pd.to_numeric(out["weight"], errors="coerce")
    if out["symbol"].isna().any() or out["symbol"].eq("").any():
        raise ValueError("symbol must be non-empty")
    if out["weight"].isna().any() or (out["weight"] < 0).any():
        raise ValueError("weight must be numeric and non-negative")
    if out.duplicated(["rebalance_date", "symbol"]).any():
        raise ValueError("targets contain duplicate rebalance_date/symbol rows")
    if "side" not in out.columns:
        out["side"] = default_side
    out["side"] = out["side"].astype(str).str.strip().str.lower()
    if (~out["side"].eq("long")).any():
        raise ValueError("only long targets are supported")

    columns = ["rebalance_date", "entry_date", "symbol", "weight", "side"]
    out = (
        out[columns]
        .sort_values(["rebalance_date", "symbol"], kind="stable")
        .reset_index(drop=True)
    )
    assert_positions_by_rebalance_frame(out)
    return out


def _target_frame_from_mapping(
    targets: Mapping[Any, Mapping[str, float]],
    *,
    entry_dates: Mapping[Any, Any] | None,
    default_side: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for rebalance_date, target in targets.items():
        if not isinstance(target, Mapping):
            raise TypeError("Each target must be a symbol-to-weight mapping.")
        entry_date = entry_dates.get(rebalance_date) if entry_dates is not None else None
        rows.extend(
            {
                "rebalance_date": rebalance_date,
                "entry_date": entry_date,
                "symbol": symbol,
                "weight": weight,
                "side": default_side,
            }
            for symbol, weight in target.items()
        )
    return pd.DataFrame(rows)


def _copy_target_frame(
    targets: pd.DataFrame,
    *,
    entry_dates: Mapping[Any, Any] | None,
) -> pd.DataFrame:
    out = targets.copy()
    if "weight" not in out.columns and "target_weight" in out.columns:
        out = out.rename(columns={"target_weight": "weight"})
    if "entry_date" not in out.columns and entry_dates is not None:
        out["entry_date"] = out["rebalance_date"].map(entry_dates)
    return out


def run_native_position_replay(
    positions: pd.DataFrame,
    pricing: pd.DataFrame,
    periods: pd.DataFrame,
    *,
    config: PositionBacktestConfig,
    ledger: bool = False,
    ledger_config: Any | None = None,
):
    """Run standardized positions through portfolio-backtester's native backend."""
    return NativePositionReplayBackend().run(
        NativePositionReplayRequest(
            positions=positions,
            pricing=pricing,
            periods=periods,
            config=config,
            ledger=ledger,
            ledger_config=ledger_config,
        )
    )


def periods_from_positions(positions: pd.DataFrame, pricing: pd.DataFrame) -> pd.DataFrame:
    """Build replay periods from target entry dates and available pricing dates."""
    required_positions = {"rebalance_date", "entry_date"}
    missing = sorted(required_positions - set(positions.columns))
    if missing:
        raise ValueError("positions are missing required columns: " + ", ".join(missing))
    if "trade_date" not in pricing.columns:
        raise ValueError("pricing is missing required column: trade_date")
    if positions.empty or pricing.empty:
        return pd.DataFrame(columns=["rebalance_date", "entry_date", "exit_date"])

    work = positions[["rebalance_date", "entry_date"]].copy()
    work["rebalance_date"] = pd.to_datetime(work["rebalance_date"], errors="coerce").dt.normalize()
    work["entry_date"] = pd.to_datetime(work["entry_date"], errors="coerce").dt.normalize()
    if work[["rebalance_date", "entry_date"]].isna().any().any():
        raise ValueError("positions rebalance_date and entry_date must be date-like")
    entries = (
        work.groupby("rebalance_date", as_index=False, sort=True)["entry_date"]
        .min()
        .sort_values("rebalance_date")
        .reset_index(drop=True)
    )
    pricing_dates = pd.to_datetime(pricing["trade_date"], errors="coerce").dt.normalize().dropna()
    if pricing_dates.empty:
        raise ValueError("pricing trade_date must contain at least one valid date")
    next_entries = entries["entry_date"].shift(-1)
    entries["exit_date"] = next_entries.fillna(pricing_dates.max())
    if (entries["exit_date"] < entries["entry_date"]).any():
        raise ValueError("pricing does not cover a valid exit date for every position period")
    return entries[["rebalance_date", "entry_date", "exit_date"]]


__all__ = [
    "periods_from_positions",
    "run_native_position_replay",
    "targets_to_positions_by_rebalance",
]
