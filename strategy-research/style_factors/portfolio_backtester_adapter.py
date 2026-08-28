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
from portfolio_backtester.execution import SlippageModel
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
        return pd.DataFrame(columns=["rebalance_date", "entry_date", "symbol", "weight", "side"])

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
        out[columns].sort_values(["rebalance_date", "symbol"], kind="stable").reset_index(drop=True)
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
    slippage_model: SlippageModel | None = None,
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
            slippage_model=slippage_model,
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


def attribute_delayed_fills(
    orders: pd.DataFrame,
    fills: pd.DataFrame,
    pricing: pd.DataFrame,
) -> pd.DataFrame:
    """Attribute fill delay, price movement, and model impact per order.

    ``delay_opportunity_cost`` is positive when the first fill moved against the
    requested side and negative when delayed execution helped. It is an
    execution diagnostic, not alpha attribution.
    """
    required_orders = {
        "rebalance_date",
        "entry_date",
        "symbol",
        "side",
        "requested_notional",
        "filled_notional",
        "unfilled_notional",
    }
    required_pricing = {"trade_date", "symbol", "close"}
    missing_orders = sorted(required_orders - set(orders.columns))
    missing_pricing = sorted(required_pricing - set(pricing.columns))
    if missing_orders:
        raise ValueError("orders are missing required columns: " + ", ".join(missing_orders))
    if missing_pricing:
        raise ValueError("pricing is missing required columns: " + ", ".join(missing_pricing))
    keys = ["rebalance_date", "entry_date", "symbol", "side"]
    out = orders[[*keys, "requested_notional", "filled_notional", "unfilled_notional"]].copy()
    for column in ("rebalance_date", "entry_date"):
        out[column] = pd.to_datetime(out[column], errors="coerce").dt.normalize()
    out["symbol"] = out["symbol"].astype(str)
    out["side"] = out["side"].astype(str).str.lower()
    fill_work = fills.copy()
    if fill_work.empty:
        first = pd.DataFrame(columns=[*keys, "first_fill_date", "temporary_impact"])
    else:
        fill_work["trade_date"] = pd.to_datetime(
            fill_work["trade_date"], errors="coerce"
        ).dt.normalize()
        for column in ("rebalance_date", "entry_date"):
            fill_work[column] = pd.to_datetime(fill_work[column], errors="coerce").dt.normalize()
        fill_work["symbol"] = fill_work["symbol"].astype(str)
        fill_work["side"] = fill_work["side"].astype(str).str.lower()
        first = (
            fill_work.sort_values("trade_date")
            .groupby(keys, as_index=False, sort=False)
            .agg(
                first_fill_date=("trade_date", "first"),
                temporary_impact=("cost_temporary_impact", "sum"),
            )
        )
    out = out.merge(first, on=keys, how="left")
    out["delay_days"] = (out["first_fill_date"] - out["entry_date"]).dt.days.fillna(0).astype(int)
    price_work = pricing[["trade_date", "symbol", "close"]].copy()
    price_work["trade_date"] = pd.to_datetime(
        price_work["trade_date"], errors="coerce"
    ).dt.normalize()
    price_work["close"] = pd.to_numeric(price_work["close"], errors="coerce")
    entry_price = price_work.rename(columns={"trade_date": "entry_date", "close": "entry_price"})
    fill_price = price_work.rename(
        columns={"trade_date": "first_fill_date", "close": "first_fill_price"}
    )
    out = out.merge(entry_price, on=["entry_date", "symbol"], how="left")
    out = out.merge(fill_price, on=["first_fill_date", "symbol"], how="left")
    raw_return = out["first_fill_price"].div(out["entry_price"]) - 1.0
    side_sign = out["side"].astype(str).str.lower().map({"buy": 1.0, "sell": -1.0}).fillna(0.0)
    out["reference_return_to_first_fill"] = (raw_return * side_sign).fillna(0.0)
    out["delay_opportunity_cost"] = (
        out["unfilled_notional"] * out["reference_return_to_first_fill"]
    ).astype(float)
    out["temporary_impact"] = out["temporary_impact"].fillna(0.0)
    return out


def owner_execution_receipt(result: Any) -> dict[str, Any]:
    """Summarize whether an owner result is suitable for canonical execution."""
    capabilities = result.capabilities
    return {
        "backend_name": result.backend_name,
        "daily_ledger": bool(capabilities.daily_ledger and not result.daily_ledger.empty),
        "orders": bool(capabilities.order_lifecycle and not result.orders.empty),
        "fills": bool(capabilities.partial_fills and not result.fills.empty),
        "partial_fills_supported": bool(capabilities.partial_fills),
        "temporary_impact": float(
            result.fills.get("cost_temporary_impact", pd.Series(dtype=float)).sum()
        ),
        "canonical_status": "comparison_only",
    }


__all__ = [
    "attribute_delayed_fills",
    "owner_execution_receipt",
    "periods_from_positions",
    "run_native_position_replay",
    "targets_to_positions_by_rebalance",
]
