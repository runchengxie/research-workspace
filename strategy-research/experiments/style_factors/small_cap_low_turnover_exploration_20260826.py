"""Compare small-cap and low-turnover long-only candidates.

This is an evidence-producing research experiment only.  It does not register
a strategy, write production artifacts, or trigger an E2 review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from portfolio_backtester.execution import ParticipationSlippageModel
from portfolio_backtester.execution_sim import (
    ExecutionSimConfig,
    PreparedExecutionTables,
    prepare_execution_tables,
    simulate_execution_adjusted_nav,
    simulate_ideal_daily_nav,
)
from portfolio_backtester.position_backtest import PositionBacktestConfig
from style_factors.data import load_sw_industry_membership
from style_factors.liquidity_signals import build_liquidity_control_panel
from style_factors.portfolio_backtester_adapter import (
    attribute_delayed_fills,
    periods_from_positions,
    run_native_position_replay,
)
from style_factors.robustness_data import load_robustness_market_data
from style_factors.robustness_execution import daily_return_matrix, execution_matrices
from style_factors.size_turnover_double_sort import build_size_turnover_double_sort
from style_factors.small_cap_low_turnover import (
    SIGNAL_COLUMNS,
    build_buffered_targets,
    build_candidate_signal_panel,
    build_lagged_turnover_panel,
    build_rebalance_formation_dates,
    filter_candidate_eligibility,
    map_targets_to_execution_dates,
    simulate_long_only_candidates,
    summarize_long_only_simulations,
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(pd.Timestamp(value))
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    return value


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _yearly_returns(daily: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for column in sorted(column for column in daily if column.endswith("_net")):
        candidate = column.removesuffix("_net")
        for year, values in daily[column].dropna().groupby(daily.index.year):
            rows.append(
                {
                    "candidate": candidate,
                    "year": int(year),
                    "net_return": float((1.0 + values).prod() - 1.0),
                }
            )
    return pd.DataFrame(rows)


def _period_return_metrics(
    values: pd.Series,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, float | int]:
    clean = values.loc[start:end].dropna()
    if clean.empty:
        return {
            "days": 0,
            "cumulative_return": float("nan"),
            "annualized_return": float("nan"),
        }
    cumulative = float((1.0 + clean).prod() - 1.0)
    return {
        "days": len(clean),
        "cumulative_return": cumulative,
        "annualized_return": float((1.0 + cumulative) ** (252 / len(clean)) - 1.0),
    }


def _correlations(daily: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in daily if column.endswith("_net")]
    if not columns:
        return pd.DataFrame()
    return (
        daily[columns]
        .corr()
        .rename(
            columns=lambda column: column.removesuffix("_net"),
            index=lambda index: index.removesuffix("_net"),
        )
    )


def _signal_correlations(panel: pd.DataFrame) -> pd.DataFrame:
    def group_correlation(group: pd.DataFrame, left: str, right: str) -> float:
        return float(group[left].corr(group[right]))

    columns = [column for column in SIGNAL_COLUMNS.values() if column in panel]
    groups = panel.groupby("trade_date", sort=False)
    rows: list[dict[str, Any]] = []
    for left_index, left in enumerate(columns):
        for right in columns[left_index + 1 :]:
            values = (
                groups[[left, right]]
                .apply(
                    group_correlation,
                    left,
                    right,
                    include_groups=False,
                )
                .dropna()
            )
            rows.append(
                {
                    "left_signal": left.removeprefix("signal_"),
                    "right_signal": right.removeprefix("signal_"),
                    "mean_cross_sectional_correlation": float(values.mean()),
                    "median_cross_sectional_correlation": float(values.median()),
                    "formation_dates": len(values),
                }
            )
    return pd.DataFrame(rows)


def _run_robustness_matrix(
    *,
    controls: pd.DataFrame,
    daily_clean: pd.DataFrame,
    formation_dates: pd.DatetimeIndex,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    instruments: pd.DataFrame,
    transaction_cost_bps: float,
    target_count: int,
    buffer_count: int,
    minimum_listed_days: int,
    initial_capital: float,
    returns: pd.DataFrame,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> pd.DataFrame:
    definitions = (
        ("mean_20", 20, "mean"),
        ("mean_60", 60, "mean"),
        ("median_60", 60, "median"),
        ("mean_120", 120, "mean"),
    )
    participation_cases: tuple[tuple[str, float | None], ...] = (
        ("unconstrained", None),
        ("prior_amount_5pct", 0.05),
        ("prior_amount_10pct", 0.10),
        ("prior_amount_20pct", 0.20),
    )
    rows: list[dict[str, Any]] = []
    for definition, window, statistic in definitions:
        turnover = build_lagged_turnover_panel(
            daily_clean,
            formation_dates,
            window=window,
            minimum_observations=int(np.ceil(window * 0.75)),
            statistic=statistic,
        )
        panel = build_candidate_signal_panel(
            controls,
            turnover,
            turnover_column=f"turnover_lagged_{statistic}_{window}d",
        )
        for participation_case, participation_rate in participation_cases:
            candidate_name = f"composite_{definition}_{participation_case}"
            simulations = simulate_long_only_candidates(
                panel,
                daily_clean,
                universe,
                st_history,
                instruments,
                {candidate_name: "signal_composite"},
                target_count=target_count,
                buffer_count=buffer_count,
                minimum_listed_days=minimum_listed_days,
                initial_capital=initial_capital,
                lot_size=100,
                participation_rate=participation_rate,
                returns=returns,
                matrices=matrices,
            )
            summary, daily = summarize_long_only_simulations(
                simulations,
                transaction_cost_bps=transaction_cost_bps,
            )
            if summary.empty:
                continue
            row = summary.iloc[0].to_dict()
            net = daily[f"{candidate_name}_net"]
            development = _period_return_metrics(
                net,
                start=pd.Timestamp("2015-01-01"),
                end=pd.Timestamp("2023-12-31"),
            )
            holdout = _period_return_metrics(
                net,
                start=pd.Timestamp("2024-01-01"),
                end=pd.Timestamp("2026-12-31"),
            )
            rows.append(
                {
                    **row,
                    "turnover_definition": definition,
                    "participation_case": participation_case,
                    "participation_rate": participation_rate,
                    "lot_size": 100,
                    "development_period": "2015-01-01 to 2023-12-31",
                    "holdout_period": "2024-01-01 to 2026-12-31",
                    "development_cumulative_return": development["cumulative_return"],
                    "development_annualized_return": development["annualized_return"] * 100,
                    "development_days": development["days"],
                    "holdout_cumulative_return": holdout["cumulative_return"],
                    "holdout_annualized_return": holdout["annualized_return"] * 100,
                    "holdout_days": holdout["days"],
                }
            )
    return pd.DataFrame(rows)


def _run_rebalance_matrix(
    *,
    daily_clean: pd.DataFrame,
    sw_membership: pd.DataFrame | None,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    instruments: pd.DataFrame,
    transaction_cost_bps: float,
    target_count: int,
    buffer_count: int,
    minimum_listed_days: int,
    initial_capital: float,
    returns: pd.DataFrame,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> pd.DataFrame:
    trading_dates = pd.DatetimeIndex(daily_clean["trade_date"].unique()).normalize()
    basics = daily_clean[["trade_date", "symbol", "total_mv"]]
    controls_daily = daily_clean[["trade_date", "symbol", "tr_close", "amount"]].rename(
        columns={"tr_close": "close"}
    )
    frequencies = ("weekly", "biweekly", "monthly", "quarterly")
    rows: list[dict[str, Any]] = []
    for frequency in frequencies:
        formation_dates = build_rebalance_formation_dates(
            trading_dates,
            frequency=frequency,
        )
        controls = build_liquidity_control_panel(
            controls_daily,
            basics,
            formation_dates,
            sw_membership=sw_membership,
        )
        turnover = build_lagged_turnover_panel(daily_clean, formation_dates)
        panel = build_candidate_signal_panel(controls, turnover)
        candidate_name = f"composite_{frequency}"
        simulations = simulate_long_only_candidates(
            panel,
            daily_clean,
            universe,
            st_history,
            instruments,
            {candidate_name: "signal_composite"},
            target_count=target_count,
            buffer_count=buffer_count,
            minimum_listed_days=minimum_listed_days,
            initial_capital=initial_capital,
            returns=returns,
            matrices=matrices,
        )
        summary, daily = summarize_long_only_simulations(
            simulations,
            transaction_cost_bps=transaction_cost_bps,
        )
        if summary.empty:
            continue
        row = summary.iloc[0].to_dict()
        net = daily[f"{candidate_name}_net"]
        development = _period_return_metrics(
            net,
            start=pd.Timestamp("2015-01-01"),
            end=pd.Timestamp("2023-12-31"),
        )
        holdout = _period_return_metrics(
            net,
            start=pd.Timestamp("2024-01-01"),
            end=pd.Timestamp("2026-12-31"),
        )
        rows.append(
            {
                **row,
                "rebalance_frequency": frequency,
                "formation_dates": len(formation_dates),
                "development_period": "2015-01-01 to 2023-12-31",
                "holdout_period": "2024-01-01 to 2026-12-31",
                "development_cumulative_return": development["cumulative_return"],
                "development_annualized_return": development["annualized_return"] * 100,
                "development_days": development["days"],
                "holdout_cumulative_return": holdout["cumulative_return"],
                "holdout_annualized_return": holdout["annualized_return"] * 100,
                "holdout_days": holdout["days"],
            }
        )
    return pd.DataFrame(rows)


def _build_share_ledger_positions(
    formation_targets: dict[pd.Timestamp, dict[str, float]],
    trading_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Expand formation targets into execution-sim position rows.

    Each formation target is paired with its next trading session as the
    ``entry_date``.  The ``rebalance_date`` is the formation session, matching
    the simulator's period semantics.
    """
    rows: list[dict[str, Any]] = []
    for formation_date, weights in formation_targets.items():
        position = int(trading_dates.searchsorted(formation_date, side="right"))
        if position >= len(trading_dates):
            continue
        entry_date = pd.Timestamp(trading_dates[position]).normalize()  # ty: ignore[unresolved-attribute]
        for symbol, weight in weights.items():
            rows.append(
                {
                    "rebalance_date": pd.Timestamp(formation_date).normalize(),  # ty: ignore[unresolved-attribute]
                    "entry_date": entry_date,
                    "symbol": symbol,
                    "weight": float(weight),
                    "side": "long",
                }
            )
    return pd.DataFrame(rows)


def _participation_slippage_model(
    impact_bps: float,
    *,
    portfolio_value: float,
) -> ParticipationSlippageModel | None:
    if impact_bps <= 0:
        return None
    return ParticipationSlippageModel(
        impact_bps=float(impact_bps),
        amount_col="amount",
        amount_multiplier=1_000.0,
        portfolio_value=float(portfolio_value),
    )


def _prepare_frequency_cache(
    *,
    daily_clean: pd.DataFrame,
    sw_membership: pd.DataFrame | None,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    minimum_listed_days: int,
    frequencies: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    """Build expensive frequency-specific research inputs exactly once."""
    trading_dates = pd.DatetimeIndex(daily_clean["trade_date"].unique()).normalize()
    basics = daily_clean[["trade_date", "symbol", "total_mv"]]
    controls_daily = daily_clean[["trade_date", "symbol", "tr_close", "amount"]].rename(
        columns={"tr_close": "close"}
    )
    cache: dict[str, dict[str, Any]] = {}
    for frequency in dict.fromkeys(frequencies):
        formation_dates = build_rebalance_formation_dates(
            trading_dates,
            frequency=frequency,
        )
        controls = build_liquidity_control_panel(
            controls_daily,
            basics,
            formation_dates,
            sw_membership=sw_membership,
        )
        turnover = build_lagged_turnover_panel(daily_clean, formation_dates)
        panel = build_candidate_signal_panel(controls, turnover)
        eligible = filter_candidate_eligibility(
            panel,
            universe,
            daily_clean,
            st_history,
            minimum_listed_days=minimum_listed_days,
        )
        cache[frequency] = {
            "formation_dates": formation_dates,
            "controls": controls,
            "panel": panel,
            "eligible": eligible,
        }
    return cache


def _write_csv_checkpoint(frame: pd.DataFrame, outdir: Path, filename: str) -> None:
    """Persist one completed matrix immediately for interruption-safe runs."""
    frame.to_csv(outdir / filename, index=False)


def _run_share_ledger_matrix(
    *,
    daily_clean: pd.DataFrame,
    sw_membership: pd.DataFrame | None,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    instruments: pd.DataFrame,
    transaction_cost_bps: float,
    target_count: int,
    buffer_count: int,
    minimum_listed_days: int,
    initial_capital: float,
    impact_bps: float = 0.0,
    attribution_rows: list[pd.DataFrame] | None = None,
    owner_ledger: bool = False,
    frequencies: tuple[str, ...] = ("monthly", "biweekly"),
    frequency_cache: dict[str, dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Run the raw composite under a cash-ledger execution model.

    Targets are built with the same signal panel and buffer as the weight-level
    simulator, then executed by ``portfolio_backtester.execution_sim`` with lot
    rounding, T+1 inventory, participation caps, and daily NAV accounting.  The
    owner-package period replay is recorded alongside it for migration comparison.
    """
    trading_dates = pd.DatetimeIndex(daily_clean["trade_date"].unique()).normalize()
    pricing = daily_clean[
        ["trade_date", "symbol", "tr_close", "amount", "pct_chg", "is_limit_up", "is_limit_down"]
    ].rename(columns={"tr_close": "close"})
    rows: list[dict[str, Any]] = []
    for frequency in frequencies:
        prepared = (frequency_cache or {}).get(frequency)
        if prepared is None:
            prepared = _prepare_frequency_cache(
                daily_clean=daily_clean,
                sw_membership=sw_membership,
                universe=universe,
                st_history=st_history,
                minimum_listed_days=minimum_listed_days,
                frequencies=(frequency,),
            )[frequency]
        formation_dates = prepared["formation_dates"]
        eligible = prepared["eligible"]
        formation_targets = build_buffered_targets(
            eligible,
            formation_dates,
            signal_column="signal_composite",
            target_count=target_count,
            buffer_count=buffer_count,
        )
        execution_targets = map_targets_to_execution_dates(formation_targets, trading_dates)
        positions = _build_share_ledger_positions(formation_targets, trading_dates)
        if positions.empty:
            continue
        owner_periods = periods_from_positions(positions, pricing)
        config = ExecutionSimConfig(
            enabled=True,
            portfolio_value=initial_capital,
            participation_rate=0.05,
            liquidity_cols=("amount",),
            liquidity_notional_multiplier=1_000.0,
            buy_max_days=3,
            sell_max_days=5,
            round_lot=100,
            enforce_t1=True,
        )
        slippage_model = _participation_slippage_model(
            impact_bps,
            portfolio_value=initial_capital,
        )
        owner_result = run_native_position_replay(
            positions,
            pricing,
            owner_periods,
            config=PositionBacktestConfig(
                price_col="close",
                transaction_cost_bps=transaction_cost_bps,
                tradable_col="amount",
            ),
            ledger=owner_ledger,
            ledger_config=config,
            slippage_model=slippage_model if owner_ledger else None,
        )
        owner_returns = owner_result.performance["net_return"].dropna()
        result = simulate_execution_adjusted_nav(
            positions,
            pricing,
            config,
            price_col="close",
            tradable_col="amount",
            transaction_cost_bps=transaction_cost_bps,
            slippage_model=slippage_model,
        )
        attribution = attribute_delayed_fills(result.orders, result.fills, pricing)
        if attribution_rows is not None:
            detail = attribution.copy()
            detail.insert(0, "rebalance_frequency", frequency)
            attribution_rows.append(detail)
        summary = result.summary
        stats = summary.get("stats", {})
        rows.append(
            {
                "rebalance_frequency": frequency,
                "formation_dates": len(formation_dates),
                "status": summary.get("status"),
                "share_ledger_net_annual_return": stats.get("ann_return") * 100
                if stats.get("ann_return") is not None
                else None,
                "share_ledger_net_sharpe": stats.get("sharpe"),
                "share_ledger_max_drawdown": stats.get("max_drawdown") * 100
                if stats.get("max_drawdown") is not None
                else None,
                "share_ledger_fill_ratio": summary.get("fill_ratio"),
                "share_ledger_avg_cash_weight": summary.get("avg_cash_weight"),
                "share_ledger_cumulative_turnover": (
                    float(summary.get("filled_notional", 0.0)) / initial_capital
                ),
                "share_ledger_temporary_impact": float(result.daily["cost_temporary_impact"].sum()),
                "share_ledger_delay_opportunity_cost": float(
                    attribution["delay_opportunity_cost"].sum()
                ),
                "share_ledger_delayed_orders": int(attribution["delay_days"].gt(0).sum()),
                "weight_level_targets": len(execution_targets),
                "owner_period_replay_status": "ok",
                "owner_period_replay_periods": len(owner_returns),
                "owner_period_replay_cumulative_return": float((1.0 + owner_returns).prod() - 1.0),
                "owner_ledger_temporary_impact": float(
                    owner_result.fills.get("cost_temporary_impact", pd.Series(dtype=float)).sum()
                ),
                "owner_canonical_status": (
                    "comparison_only_ledger" if owner_ledger else "comparison_only_period_replay"
                ),
            }
        )
    return pd.DataFrame(rows)


def _ledger_arm_row(
    result: Any,
    *,
    frequency: str,
    candidate: str,
    engine_arm: str,
    initial_capital: float,
) -> dict[str, Any]:
    stats = result.summary.get("stats", {})
    ann_return = stats.get("ann_return")
    max_drawdown = stats.get("max_drawdown")
    return {
        "rebalance_frequency": frequency,
        "candidate": candidate,
        "engine_arm": engine_arm,
        "net_annual_return": ann_return * 100 if ann_return is not None else None,
        "net_sharpe": stats.get("sharpe"),
        "max_drawdown": max_drawdown * 100 if max_drawdown is not None else None,
        "fill_ratio": result.summary.get("fill_ratio"),
        "avg_cash_weight": result.summary.get("avg_cash_weight"),
        "cumulative_turnover": (
            float(result.summary.get("filled_notional", 0.0)) / initial_capital
        ),
        "temporary_impact": float(
            result.fills.get("cost_temporary_impact", pd.Series(dtype=float)).sum()
        ),
    }


def _weight_level_arm_row(
    summary: pd.DataFrame,
    name: str,
    *,
    frequency: str,
    candidate: str,
) -> dict[str, Any]:
    row = summary.iloc[0].to_dict()
    return {
        "rebalance_frequency": frequency,
        "candidate": candidate,
        "engine_arm": "weight_level",
        "net_annual_return": row.get("net_annual_return"),
        "net_sharpe": row.get("net_sharpe"),
        "max_drawdown": row.get("net_max_drawdown"),
        "fill_ratio": None,
        "avg_cash_weight": None,
        "cumulative_turnover": float(row.get("average_daily_turnover", 0.0) or 0.0)
        * float(row.get("days", 0)),
    }


def _run_reconciliation_arm(
    *,
    engine_arm: str,
    positions: pd.DataFrame,
    pricing: pd.DataFrame,
    panel: pd.DataFrame,
    daily_clean: pd.DataFrame,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    instruments: pd.DataFrame,
    returns: pd.DataFrame,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray],
    signal_column: str,
    reference_name: str,
    frequency: str,
    candidate: str,
    target_count: int,
    buffer_count: int,
    minimum_listed_days: int,
    initial_capital: float,
    transaction_cost_bps: float,
    impact_bps: float,
    prepared_tables: PreparedExecutionTables,
) -> dict[str, Any]:
    """Run exactly one reconciliation arm for an already-built position plan."""
    if engine_arm == "weight_level":
        simulations = simulate_long_only_candidates(
            panel,
            daily_clean,
            universe,
            st_history,
            instruments,
            {reference_name: signal_column},
            target_count=target_count,
            buffer_count=buffer_count,
            minimum_listed_days=minimum_listed_days,
            initial_capital=initial_capital,
            returns=returns,
            matrices=matrices,
        )
        summary, _daily = summarize_long_only_simulations(
            simulations,
            transaction_cost_bps=transaction_cost_bps,
        )
        return _weight_level_arm_row(
            summary, reference_name, frequency=frequency, candidate=candidate
        )

    if engine_arm == "ideal_nav":
        result = simulate_ideal_daily_nav(
            positions,
            pricing,
            price_col="close",
            transaction_cost_bps=transaction_cost_bps,
            portfolio_value=initial_capital,
        )
    else:
        participation_rate = 1.0 if engine_arm == "ledger_no_participation" else 0.05
        round_lot = None if engine_arm == "ledger_no_lot" else 100
        enforce_t1 = engine_arm != "ledger_no_t1"
        config = ExecutionSimConfig(
            enabled=True,
            portfolio_value=initial_capital,
            participation_rate=participation_rate,
            liquidity_cols=("amount",),
            liquidity_notional_multiplier=1_000.0,
            buy_max_days=3,
            sell_max_days=5,
            round_lot=round_lot,
            enforce_t1=enforce_t1,
        )
        result = simulate_execution_adjusted_nav(
            positions,
            pricing,
            config,
            price_col="close",
            tradable_col="amount",
            transaction_cost_bps=(
                0.0 if engine_arm == "ledger_zero_cost" else transaction_cost_bps
            ),
            slippage_model=_participation_slippage_model(
                impact_bps,
                portfolio_value=initial_capital,
            ),
            prepared_tables=prepared_tables,
        )
    return _ledger_arm_row(
        result,
        frequency=frequency,
        candidate=candidate,
        engine_arm=engine_arm,
        initial_capital=initial_capital,
    )


def _run_reconciliation_matrix(  # noqa: C901
    *,
    daily_clean: pd.DataFrame,
    sw_membership: pd.DataFrame | None,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    instruments: pd.DataFrame,
    transaction_cost_bps: float,
    target_count: int,
    buffer_count: int,
    minimum_listed_days: int,
    initial_capital: float,
    returns: pd.DataFrame,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray],
    impact_bps: float = 0.0,
    frequencies: tuple[str, ...] = ("monthly", "biweekly"),
    frequency_cache: dict[str, dict[str, Any]] | None = None,
    checkpoint_path: Path | None = None,
    resume: bool = False,
) -> pd.DataFrame:
    """Decompose the weight-level versus cash-ledger result gap.

    For identical formation targets the runner reports a weight-level
    reference, a frictionless ideal NAV with share semantics, and the fully
    constrained ledger, then relaxes one constraint at a time on the monthly
    composite so the gap can be attributed to accounting semantics versus
    execution frictions.
    """
    trading_dates = pd.DatetimeIndex(daily_clean["trade_date"].unique()).normalize()
    pricing = daily_clean[
        ["trade_date", "symbol", "tr_close", "amount", "pct_chg", "is_limit_up", "is_limit_down"]
    ].rename(columns={"tr_close": "close"})
    candidates = (
        ("composite", "signal_composite"),
        ("small_cap", "signal_small_cap"),
        ("large_cap_control", "signal_large_cap_control"),
    )

    table_config = ExecutionSimConfig(
        enabled=True,
        portfolio_value=initial_capital,
        participation_rate=0.05,
        liquidity_cols=("amount",),
        liquidity_notional_multiplier=1_000.0,
        buy_max_days=3,
        sell_max_days=5,
        round_lot=100,
        enforce_t1=True,
    )
    prepared_tables = prepare_execution_tables(
        pricing,
        table_config,
        price_col="close",
        tradable_col="amount",
    )

    rows: list[dict[str, Any]] = []
    position_cache: dict[tuple[str, str], pd.DataFrame] = {}
    if checkpoint_path is not None and resume and checkpoint_path.exists():
        existing = pd.read_csv(checkpoint_path)
        completed = set(
            zip(
                existing.get("rebalance_frequency", pd.Series(dtype=str)),
                existing.get("candidate", pd.Series(dtype=str)),
                existing.get("engine_arm", pd.Series(dtype=str)),
                strict=True,
            )
        )
    else:
        existing = pd.DataFrame()
        completed = set()

    def checkpoint() -> None:
        if checkpoint_path is None:
            return
        output = pd.DataFrame(rows)
        if not existing.empty:
            output = pd.concat([existing, output], ignore_index=True)
        output.to_csv(checkpoint_path, index=False)

    for frequency in frequencies:
        prepared = (frequency_cache or {}).get(frequency)
        if prepared is None:
            prepared = _prepare_frequency_cache(
                daily_clean=daily_clean,
                sw_membership=sw_membership,
                universe=universe,
                st_history=st_history,
                minimum_listed_days=minimum_listed_days,
                frequencies=(frequency,),
            )[frequency]
        formation_dates = prepared["formation_dates"]
        panel = prepared["panel"]
        eligible = prepared["eligible"]
        for candidate, signal_column in candidates:
            cache_key = (frequency, candidate)
            positions = position_cache.get(cache_key)
            if positions is None:
                formation_targets = build_buffered_targets(
                    eligible,
                    formation_dates,
                    signal_column=signal_column,
                    target_count=target_count,
                    buffer_count=buffer_count,
                )
                positions = _build_share_ledger_positions(formation_targets, trading_dates)
                position_cache[cache_key] = positions
            if positions.empty:
                continue
            reference_name = f"recon_{candidate}"
            for engine_arm in ("weight_level", "ideal_nav", "ledger_full"):
                key = (frequency, candidate, engine_arm)
                if key in completed:
                    continue
                rows.append(
                    _run_reconciliation_arm(
                        engine_arm=engine_arm,
                        positions=positions,
                        pricing=pricing,
                        panel=panel,
                        daily_clean=daily_clean,
                        universe=universe,
                        st_history=st_history,
                        instruments=instruments,
                        returns=returns,
                        matrices=matrices,
                        signal_column=signal_column,
                        reference_name=reference_name,
                        frequency=frequency,
                        candidate=candidate,
                        target_count=target_count,
                        buffer_count=buffer_count,
                        minimum_listed_days=minimum_listed_days,
                        initial_capital=initial_capital,
                        transaction_cost_bps=transaction_cost_bps,
                        impact_bps=impact_bps,
                        prepared_tables=prepared_tables,
                    )
                )
                checkpoint()
            if frequency != "monthly" or candidate != "composite":
                continue
            for engine_arm in (
                "ledger_no_participation",
                "ledger_no_t1",
                "ledger_no_lot",
                "ledger_zero_cost",
            ):
                key = (frequency, candidate, engine_arm)
                if key in completed:
                    continue
                rows.append(
                    _run_reconciliation_arm(
                        engine_arm=engine_arm,
                        positions=positions,
                        pricing=pricing,
                        panel=panel,
                        daily_clean=daily_clean,
                        universe=universe,
                        st_history=st_history,
                        instruments=instruments,
                        returns=returns,
                        matrices=matrices,
                        signal_column=signal_column,
                        reference_name=reference_name,
                        frequency=frequency,
                        candidate=candidate,
                        target_count=target_count,
                        buffer_count=buffer_count,
                        minimum_listed_days=minimum_listed_days,
                        initial_capital=initial_capital,
                            transaction_cost_bps=transaction_cost_bps,
                            impact_bps=impact_bps,
                            prepared_tables=prepared_tables,
                        )
                )
                checkpoint()
    out = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True)
    if out.empty:
        return out
    comparison_keys = ["rebalance_frequency", "engine_arm"]
    small = out.loc[
        out["candidate"].eq("small_cap"), [*comparison_keys, "net_annual_return"]
    ].rename(columns={"net_annual_return": "small_cap_return"})
    large = out.loc[
        out["candidate"].eq("large_cap_control"), [*comparison_keys, "net_annual_return"]
    ].rename(columns={"net_annual_return": "large_cap_return"})
    out = out.merge(small, on=comparison_keys, how="left")
    out = out.merge(large, on=comparison_keys, how="left")
    out["incremental_vs_small_cap"] = out["net_annual_return"] - out["small_cap_return"]
    out["incremental_vs_large_cap"] = out["net_annual_return"] - out["large_cap_return"]
    return out.drop(columns=["small_cap_return", "large_cap_return"])


def _run_capacity_ladder(
    *,
    daily_clean: pd.DataFrame,
    sw_membership: pd.DataFrame | None,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    instruments: pd.DataFrame,
    transaction_cost_bps: float,
    target_count: int,
    buffer_count: int,
    minimum_listed_days: int,
    impact_bps: float = 0.0,
    capitals: tuple[float, ...] = (10_000_000.0, 100_000_000.0, 500_000_000.0),
    frequency_cache: dict[str, dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Run the monthly raw composite through the constrained ledger at capital sizes.

    Participation caps tighten as capital grows because each name's capacity is
    a fixed fraction of its prior traded amount, so the ladder locates where
    fills, cash drag, and net results start to collapse.
    """
    trading_dates = pd.DatetimeIndex(daily_clean["trade_date"].unique()).normalize()
    pricing = daily_clean[
        ["trade_date", "symbol", "tr_close", "amount", "pct_chg", "is_limit_up", "is_limit_down"]
    ].rename(columns={"tr_close": "close"})
    prepared = (frequency_cache or {}).get("monthly")
    if prepared is None:
        prepared = _prepare_frequency_cache(
            daily_clean=daily_clean,
            sw_membership=sw_membership,
            universe=universe,
            st_history=st_history,
            minimum_listed_days=minimum_listed_days,
            frequencies=("monthly",),
        )["monthly"]
    formation_dates = prepared["formation_dates"]
    eligible = prepared["eligible"]
    formation_targets = build_buffered_targets(
        eligible,
        formation_dates,
        signal_column="signal_composite",
        target_count=target_count,
        buffer_count=buffer_count,
    )
    positions = _build_share_ledger_positions(formation_targets, trading_dates)
    rows: list[dict[str, Any]] = []
    if positions.empty:
        return pd.DataFrame(rows)
    for capital in capitals:
        config = ExecutionSimConfig(
            enabled=True,
            portfolio_value=capital,
            participation_rate=0.05,
            liquidity_cols=("amount",),
            liquidity_notional_multiplier=1_000.0,
            buy_max_days=3,
            sell_max_days=5,
            round_lot=100,
            enforce_t1=True,
        )
        result = simulate_execution_adjusted_nav(
            positions,
            pricing,
            config,
            price_col="close",
            tradable_col="amount",
            transaction_cost_bps=transaction_cost_bps,
            slippage_model=_participation_slippage_model(
                impact_bps,
                portfolio_value=capital,
            ),
        )
        attribution = attribute_delayed_fills(result.orders, result.fills, pricing)
        summary = result.summary
        stats = summary.get("stats", {})
        ann_return = stats.get("ann_return")
        max_drawdown = stats.get("max_drawdown")
        rows.append(
            {
                "capital": capital,
                "status": summary.get("status"),
                "net_annual_return": ann_return * 100 if ann_return is not None else None,
                "net_sharpe": stats.get("sharpe"),
                "max_drawdown": max_drawdown * 100 if max_drawdown is not None else None,
                "fill_ratio": summary.get("fill_ratio"),
                "avg_cash_weight": summary.get("avg_cash_weight"),
                "cumulative_turnover": (float(summary.get("filled_notional", 0.0)) / capital),
                "temporary_impact": float(
                    result.fills.get("cost_temporary_impact", pd.Series(dtype=float)).sum()
                ),
                "delay_opportunity_cost": float(attribution["delay_opportunity_cost"].sum()),
                "delayed_orders": int(attribution["delay_days"].gt(0).sum()),
            }
        )
    return pd.DataFrame(rows)


def _run_joint_matrix(
    *,
    daily_clean: pd.DataFrame,
    sw_membership: pd.DataFrame | None,
    universe: pd.DataFrame,
    st_history: pd.DataFrame,
    instruments: pd.DataFrame,
    transaction_cost_bps: float,
    target_count: int,
    buffer_count: int,
    minimum_listed_days: int,
    initial_capital: float,
    returns: pd.DataFrame,
    matrices: tuple[np.ndarray, np.ndarray, np.ndarray],
    definitions: tuple[tuple[str, int, str], ...] = (
        ("mean_20", 20, "mean"),
        ("mean_60", 60, "mean"),
        ("median_60", 60, "median"),
        ("mean_120", 120, "mean"),
    ),
    frequencies: tuple[str, ...] = ("weekly", "biweekly", "monthly", "quarterly"),
    frequency_cache: dict[str, dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Cross turnover lookback definitions with formation cadences.

    The robustness matrix varies definitions at the monthly cadence and the
    rebalance matrix varies cadences at the mean-60 definition; this matrix
    covers the joint grid on the raw composite with the weight-level engine.
    """
    rows: list[dict[str, Any]] = []
    for frequency in frequencies:
        prepared = (frequency_cache or {}).get(frequency)
        if prepared is None:
            prepared = _prepare_frequency_cache(
                daily_clean=daily_clean,
                sw_membership=sw_membership,
                universe=universe,
                st_history=st_history,
                minimum_listed_days=minimum_listed_days,
                frequencies=(frequency,),
            )[frequency]
        formation_dates = prepared["formation_dates"]
        controls = prepared["controls"]
        for definition, window, statistic in definitions:
            turnover = build_lagged_turnover_panel(
                daily_clean,
                formation_dates,
                window=window,
                minimum_observations=int(np.ceil(window * 0.75)),
                statistic=statistic,
            )
            panel = build_candidate_signal_panel(
                controls,
                turnover,
                turnover_column=f"turnover_lagged_{statistic}_{window}d",
            )
            candidate_name = f"joint_{definition}_{frequency}"
            simulations = simulate_long_only_candidates(
                panel,
                daily_clean,
                universe,
                st_history,
                instruments,
                {candidate_name: "signal_composite"},
                target_count=target_count,
                buffer_count=buffer_count,
                minimum_listed_days=minimum_listed_days,
                initial_capital=initial_capital,
                returns=returns,
                matrices=matrices,
            )
            summary, daily = summarize_long_only_simulations(
                simulations,
                transaction_cost_bps=transaction_cost_bps,
            )
            if summary.empty:
                continue
            row = summary.iloc[0].to_dict()
            net = daily[f"{candidate_name}_net"]
            development = _period_return_metrics(
                net,
                start=pd.Timestamp("2015-01-01"),
                end=pd.Timestamp("2023-12-31"),
            )
            holdout = _period_return_metrics(
                net,
                start=pd.Timestamp("2024-01-01"),
                end=pd.Timestamp("2026-12-31"),
            )
            rows.append(
                {
                    **row,
                    "turnover_definition": definition,
                    "rebalance_frequency": frequency,
                    "formation_dates": len(formation_dates),
                    "development_annualized_return": development["annualized_return"] * 100,
                    "holdout_annualized_return": holdout["annualized_return"] * 100,
                }
            )
    return pd.DataFrame(rows)


def _period_returns(daily: pd.DataFrame) -> pd.DataFrame:
    periods = {
        "2015-2019": (pd.Timestamp("2015-01-01"), pd.Timestamp("2019-12-31")),
        "2020-2023": (pd.Timestamp("2020-01-01"), pd.Timestamp("2023-12-31")),
        "2024-2026": (pd.Timestamp("2024-01-01"), pd.Timestamp("2026-12-31")),
    }
    rows: list[dict[str, Any]] = []
    for column in sorted(column for column in daily if column.endswith("_net")):
        candidate = column.removesuffix("_net")
        for period, (start, end) in periods.items():
            values = daily.loc[start:end, column].dropna()
            if values.empty:
                continue
            rows.append(
                {
                    "candidate": candidate,
                    "period": period,
                    "net_return": float((1.0 + values).prod() - 1.0),
                    "days": len(values),
                }
            )
    return pd.DataFrame(rows)


def _write_report(
    outdir: Path,
    *,
    summary: pd.DataFrame,
    yearly: pd.DataFrame,
    periods: pd.DataFrame,
    signal_correlations: pd.DataFrame,
    robustness: pd.DataFrame,
    rebalance_matrix: pd.DataFrame,
    share_ledger_matrix: pd.DataFrame,
    reconciliation_matrix: pd.DataFrame,
    capacity_ladder: pd.DataFrame,
    joint_matrix: pd.DataFrame,
    metadata: dict[str, Any],
) -> None:
    lines = [
        "# Small-cap × low-turnover exploration",
        "",
        "This is a research-screening artifact. It is not a production strategy "
        "and does not trigger E2.",
        "",
        "## Scope",
        "",
        "- Monthly formation; next-trading-session target execution.",
        "- Sector-neutral small-cap and lagged 60-trading-day turnover signals.",
        "- Low-turnover residualized against size and low volatility.",
        "- Low-turnover residualized against size, low volatility, and one-hot "
        "industry dummies to deconfound industry exposure.",
        "- Equal-weight target portfolio with a 40-name target and 60-name buffer.",
        "- Formation eligibility excludes immature listings, ST names, suspended names, "
        "and names outside the point-in-time universe.",
        "- Daily simulation uses the shared suspension, price-limit, delisting, and "
        "transaction-cost engine.",
        "- Target changes are submitted on the next trading session, so the "
        "formation-day return is not captured by the new holdings.",
        "- Weights are continuous research weights; integer-lot rounding is a "
        "remaining limitation for the baseline arm; sensitivity cases round "
        "target entries using the prior close.",
        "- Sensitivity cases use configurable research capital; the current run uses "
        "100m CNY and 100-share lot rounding.",
        "- Sensitivity caps use the prior observed session's traded amount; "
        "they remain static-capacity research approximations.",
        "",
        "## Candidate comparison",
        "",
    ]
    if summary.empty:
        lines.append("No candidate produced a valid simulation.")
    else:
        columns = [
            "candidate",
            "net_annual_return",
            "net_sharpe",
            "net_max_drawdown",
            "annualized_turnover",
            "blocked_entry_days",
            "blocked_exit_days",
        ]
        lines.append(summary[columns].to_markdown(index=False, floatfmt=".4f"))
    lines.extend(["", "## Yearly net returns", ""])
    lines.append(
        yearly.to_markdown(index=False, floatfmt=".4f")
        if not yearly.empty
        else "No yearly observations."
    )
    lines.extend(["", "## Regime net returns", ""])
    lines.append(
        periods.to_markdown(index=False, floatfmt=".4f")
        if not periods.empty
        else "No regime observations."
    )
    lines.extend(["", "## Signal exposure check", ""])
    lines.append(
        signal_correlations.to_markdown(index=False, floatfmt=".4f")
        if not signal_correlations.empty
        else "No signal-correlation observations."
    )
    lines.extend(["", "## Capacity and turnover-definition sensitivity", ""])
    if robustness.empty:
        lines.append("No robustness observations.")
    else:
        columns = [
            "turnover_definition",
            "participation_case",
            "net_annual_return",
            "net_max_drawdown",
            "annualized_turnover",
            "development_annualized_return",
            "holdout_annualized_return",
        ]
        lines.append(robustness[columns].to_markdown(index=False, floatfmt=".4f"))
    lines.extend(["", "## Rebalance-frequency sensitivity", ""])
    if rebalance_matrix.empty:
        lines.append("No rebalance-frequency observations.")
    else:
        columns = [
            "rebalance_frequency",
            "formation_dates",
            "net_annual_return",
            "net_max_drawdown",
            "annualized_turnover",
            "development_annualized_return",
            "holdout_annualized_return",
        ]
        lines.append(rebalance_matrix[columns].to_markdown(index=False, floatfmt=".4f"))
    lines.extend(["", "## Share-ledger execution", ""])
    if share_ledger_matrix.empty:
        lines.append("No share-ledger observations.")
    else:
        columns = [
            "rebalance_frequency",
            "formation_dates",
            "status",
            "share_ledger_net_annual_return",
            "share_ledger_net_sharpe",
            "share_ledger_max_drawdown",
            "share_ledger_fill_ratio",
            "share_ledger_avg_cash_weight",
            "share_ledger_cumulative_turnover",
            "owner_period_replay_status",
            "owner_period_replay_periods",
            "owner_period_replay_cumulative_return",
            "share_ledger_temporary_impact",
            "share_ledger_delay_opportunity_cost",
            "share_ledger_delayed_orders",
            "owner_ledger_temporary_impact",
            "owner_canonical_status",
        ]
        lines.append(share_ledger_matrix[columns].to_markdown(index=False, floatfmt=".4f"))
    lines.extend(["", "## Ledger reconciliation", ""])
    if reconciliation_matrix.empty:
        lines.append("No reconciliation observations.")
    else:
        columns = [
            "rebalance_frequency",
            "candidate",
            "engine_arm",
            "net_annual_return",
            "net_sharpe",
            "max_drawdown",
            "fill_ratio",
            "avg_cash_weight",
            "cumulative_turnover",
            "temporary_impact",
            "incremental_vs_small_cap",
            "incremental_vs_large_cap",
        ]
        lines.append(reconciliation_matrix[columns].to_markdown(index=False, floatfmt=".4f"))
    lines.extend(["", "## Capital ladder (ledger)", ""])
    if capacity_ladder.empty:
        lines.append("No capital-ladder observations.")
    else:
        columns = [
            "capital",
            "status",
            "net_annual_return",
            "net_sharpe",
            "max_drawdown",
            "fill_ratio",
            "avg_cash_weight",
            "cumulative_turnover",
            "temporary_impact",
            "delay_opportunity_cost",
            "delayed_orders",
        ]
        lines.append(capacity_ladder[columns].to_markdown(index=False, floatfmt=".4f"))
    lines.extend(["", "## Turnover-definition × cadence matrix", ""])
    if joint_matrix.empty:
        lines.append("No joint-matrix observations.")
    else:
        columns = [
            "turnover_definition",
            "rebalance_frequency",
            "formation_dates",
            "net_annual_return",
            "net_sharpe",
            "annualized_turnover",
            "development_annualized_return",
            "holdout_annualized_return",
        ]
        lines.append(joint_matrix[columns].to_markdown(index=False, floatfmt=".4f"))
    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- A positive composite is not evidence that low turnover is causal; compare "
            "it with small-cap-only, low-turnover-only, residualized low-turnover, and controls.",
            "- Net results remain exploratory until costs, liquidity, integer lots, and "
            "live execution assumptions are independently reviewed.",
            "- Prior-session traded-amount caps alter the fill path and can improve "
            "simulated returns by delaying "
            "trades; this is not evidence of investable alpha.",
            "- The share-ledger section uses the portfolio-backtester cash-ledger "
            "execution model with lot rounding, T+1 inventory, and participation caps; "
            "it is not a broker-fill model.",
            "- The capital ladder holds the strategy fixed and scales research capital; "
            "fill ratios tighten mechanically with size, which is a capacity statement, "
            "not an alpha change.",
            "- The joint matrix multiplies looks across definitions and cadences on the "
            "same history; isolated best cells are expected by chance, it runs on the "
            "weight-level screening engine, and cell rankings must be confirmed on the "
            "ledger engine before any selection.",
            "- The reconciliation table attributes the engine gap to accounting "
            "semantics (weight-level versus ideal NAV) and to execution frictions "
            "(ideal NAV versus constrained ledger); it is an attribution, not a proof "
            "of investable alpha.",
            "- Rebalance-frequency variants change only the formation cadence; costs and "
            "participation mechanics are otherwise shared.",
            "- No parameter was selected from final out-of-sample results by this runner.",
            "",
            f"Metadata: `{metadata['metadata_file']}`.",
        ]
    )
    (outdir / "small_cap_low_turnover_exploration.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def run_exploration(
    *,
    data_root: Path,
    outdir: Path,
    start_date: str = "2015-01-01",
    end_date: str | None = "2026-07-31",
    transaction_cost_bps: float = 10.0,
    minimum_listed_days: int = 180,
    target_count: int = 40,
    buffer_count: int = 60,
    initial_capital: float = 100_000_000.0,
    impact_bps: float = 0.0,
    stage: str = "all",
    resume: bool = False,
) -> Path:
    """Run the candidate comparison and write reproducible research outputs."""
    if stage not in {"all", "ledger", "capacity"}:
        raise ValueError("stage must be one of: all, ledger, capacity")
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps must be non-negative")
    if not np.isfinite(initial_capital) or initial_capital <= 0:
        raise ValueError("initial_capital must be positive")
    if not np.isfinite(impact_bps) or impact_bps < 0:
        raise ValueError("impact_bps must be non-negative")
    outdir.mkdir(parents=True, exist_ok=True)
    market_data = load_robustness_market_data(
        data_root,
        start_date=start_date,
        end_date=end_date,
    )
    formation_dates = pd.DatetimeIndex(
        sorted(market_data.universe["trade_date"].unique())
    ).normalize()
    daily_clean = market_data.daily_clean
    controls_daily = daily_clean[["trade_date", "symbol", "tr_close", "amount"]].rename(
        columns={"tr_close": "close"}
    )
    basics = daily_clean[["trade_date", "symbol", "total_mv"]]
    sw_membership = load_sw_industry_membership(data_root)
    cache_frequencies = {
        "all": ("weekly", "biweekly", "monthly", "quarterly"),
        "ledger": ("monthly", "biweekly"),
        "capacity": ("monthly",),
    }[stage]
    frequency_cache = _prepare_frequency_cache(
        daily_clean=daily_clean,
        sw_membership=sw_membership if not sw_membership.empty else None,
        universe=market_data.universe,
        st_history=market_data.st_history,
        minimum_listed_days=minimum_listed_days,
        frequencies=cache_frequencies,
    )
    controls = build_liquidity_control_panel(
        controls_daily,
        basics,
        formation_dates,
        sw_membership=sw_membership if not sw_membership.empty else None,
    )
    turnover = build_lagged_turnover_panel(daily_clean, formation_dates)
    signal_panel = build_candidate_signal_panel(controls, turnover)
    candidates = dict(SIGNAL_COLUMNS)
    return_matrix = daily_return_matrix(daily_clean)
    execution_context = execution_matrices(daily_clean, return_matrix)
    simulations = simulate_long_only_candidates(
        signal_panel,
        daily_clean,
        market_data.universe,
        market_data.st_history,
        market_data.instruments,
        candidates,
        target_count=target_count,
        buffer_count=buffer_count,
        minimum_listed_days=minimum_listed_days,
        initial_capital=initial_capital,
        returns=return_matrix,
        matrices=execution_context,
    )
    summary, daily = summarize_long_only_simulations(
        simulations,
        transaction_cost_bps=transaction_cost_bps,
    )
    yearly = _yearly_returns(daily)
    periods = _period_returns(daily)
    correlations = _correlations(daily)
    signal_correlations = _signal_correlations(signal_panel)
    signal_panel.to_parquet(outdir / "candidate_signal_panel.parquet", index=False)
    summary.to_csv(outdir / "candidate_summary.csv", index=False)
    daily.to_csv(outdir / "candidate_daily.csv", index=True)
    yearly.to_csv(outdir / "candidate_yearly_returns.csv", index=False)
    periods.to_csv(outdir / "candidate_regime_returns.csv", index=False)
    correlations.to_csv(outdir / "candidate_net_correlations.csv", index=True)
    signal_correlations.to_csv(outdir / "candidate_signal_correlations.csv", index=False)
    size_turnover_double_sort = build_size_turnover_double_sort(
        signal_panel,
        return_matrix,
        formation_dates=formation_dates,
    )
    robustness = pd.DataFrame()
    rebalance_matrix = pd.DataFrame()
    if stage == "all":
        robustness = _run_robustness_matrix(
            controls=controls,
            daily_clean=daily_clean,
            formation_dates=formation_dates,
            universe=market_data.universe,
            st_history=market_data.st_history,
            instruments=market_data.instruments,
            transaction_cost_bps=transaction_cost_bps,
            target_count=target_count,
            buffer_count=buffer_count,
            minimum_listed_days=minimum_listed_days,
            initial_capital=initial_capital,
            returns=return_matrix,
            matrices=execution_context,
        )
        _write_csv_checkpoint(robustness, outdir, "candidate_robustness_matrix.csv")
        rebalance_matrix = _run_rebalance_matrix(
            daily_clean=daily_clean,
            sw_membership=sw_membership if not sw_membership.empty else None,
            universe=market_data.universe,
            st_history=market_data.st_history,
            instruments=market_data.instruments,
            transaction_cost_bps=transaction_cost_bps,
            target_count=target_count,
            buffer_count=buffer_count,
            minimum_listed_days=minimum_listed_days,
            initial_capital=initial_capital,
            returns=return_matrix,
            matrices=execution_context,
        )
        _write_csv_checkpoint(rebalance_matrix, outdir, "candidate_rebalance_matrix.csv")
    attribution_rows: list[pd.DataFrame] = []
    share_ledger_matrix = pd.DataFrame()
    reconciliation_matrix = pd.DataFrame()
    if stage in {"all", "ledger"}:
        share_ledger_matrix = _run_share_ledger_matrix(
            daily_clean=daily_clean,
            sw_membership=sw_membership if not sw_membership.empty else None,
            universe=market_data.universe,
            st_history=market_data.st_history,
            instruments=market_data.instruments,
            transaction_cost_bps=transaction_cost_bps,
            target_count=target_count,
            buffer_count=buffer_count,
            minimum_listed_days=minimum_listed_days,
            initial_capital=initial_capital,
            impact_bps=impact_bps,
            attribution_rows=attribution_rows,
            frequency_cache=frequency_cache,
        )
        _write_csv_checkpoint(
            share_ledger_matrix, outdir, "candidate_share_ledger_matrix.csv"
        )
        reconciliation_matrix = _run_reconciliation_matrix(
            daily_clean=daily_clean,
            sw_membership=sw_membership if not sw_membership.empty else None,
            universe=market_data.universe,
            st_history=market_data.st_history,
            instruments=market_data.instruments,
            transaction_cost_bps=transaction_cost_bps,
            target_count=target_count,
            buffer_count=buffer_count,
            minimum_listed_days=minimum_listed_days,
            initial_capital=initial_capital,
            impact_bps=impact_bps,
            returns=return_matrix,
            matrices=execution_context,
            frequency_cache=frequency_cache,
            checkpoint_path=outdir / "candidate_reconciliation_matrix.csv",
            resume=resume,
        )
        _write_csv_checkpoint(
            reconciliation_matrix, outdir, "candidate_reconciliation_matrix.csv"
        )
        attribution_frame = (
            pd.concat(attribution_rows, ignore_index=True)
            if attribution_rows
            else pd.DataFrame()
        )
        _write_csv_checkpoint(
            attribution_frame, outdir, "candidate_delayed_fill_attribution.csv"
        )
    capacity_ladder = pd.DataFrame()
    if stage in {"all", "capacity"}:
        capacity_ladder = _run_capacity_ladder(
            daily_clean=daily_clean,
            sw_membership=sw_membership if not sw_membership.empty else None,
            universe=market_data.universe,
            st_history=market_data.st_history,
            instruments=market_data.instruments,
            transaction_cost_bps=transaction_cost_bps,
            target_count=target_count,
            buffer_count=buffer_count,
            minimum_listed_days=minimum_listed_days,
            impact_bps=impact_bps,
            frequency_cache=frequency_cache,
        )
        _write_csv_checkpoint(capacity_ladder, outdir, "candidate_capacity_ladder.csv")
    joint_matrix = pd.DataFrame()
    if stage == "all":
        joint_matrix = _run_joint_matrix(
            daily_clean=daily_clean,
            sw_membership=sw_membership if not sw_membership.empty else None,
            universe=market_data.universe,
            st_history=market_data.st_history,
            instruments=market_data.instruments,
            transaction_cost_bps=transaction_cost_bps,
            target_count=target_count,
            buffer_count=buffer_count,
            minimum_listed_days=minimum_listed_days,
            initial_capital=initial_capital,
            returns=return_matrix,
            matrices=execution_context,
            frequency_cache=frequency_cache,
        )
        _write_csv_checkpoint(joint_matrix, outdir, "candidate_joint_matrix.csv")
    if stage in {"all", "capacity"}:
        size_turnover_double_sort.to_csv(
            outdir / "candidate_size_turnover_double_sort.csv", index=False
        )
    attribution_frame = (
        pd.concat(attribution_rows, ignore_index=True) if attribution_rows else pd.DataFrame()
    )
    if stage not in {"all", "ledger"}:
        attribution_frame.to_csv(outdir / "candidate_delayed_fill_attribution.csv", index=False)
    target_rows = [
        {"candidate": name, "execution_date": date, "holdings": len(target)}
        for name, simulation in simulations.items()
        for date, target in simulation.targets.items()
    ]
    pd.DataFrame(target_rows).to_csv(outdir / "candidate_target_counts.csv", index=False)

    metadata: dict[str, Any] = {
        "experiment": "small_cap_low_turnover_exploration_20260826",
        "research_status": "exploration_only",
        "e2_triggered": False,
        "data_root": str(data_root),
        "start_date": start_date,
        "end_date": end_date,
        "data_metadata": market_data.metadata,
        "formation_dates": len(formation_dates),
        "formation_start": formation_dates.min().date().isoformat(),
        "formation_end": formation_dates.max().date().isoformat(),
        "turnover_definition": (
            "mean turnover_rate over prior 60 trading sessions, excluding formation date"
        ),
        "signals": candidates,
        "double_sort": {
            "artifact": "candidate_size_turnover_double_sort.csv",
            "size_column": "size_score",
            "turnover_column": "turnover_lagged_mean_60d",
            "bucket_count": 5,
            "forward_window": "formation_date exclusive to next formation date inclusive",
        },
        "delayed_fill_attribution": {
            "artifact": "candidate_delayed_fill_attribution.csv",
            "delay_opportunity_cost_definition": (
                "unfilled notional multiplied by side-signed return from entry date "
                "to first fill date; negative means delay helped"
            ),
            "temporary_impact_is_execution_cost": True,
        },
        "target_count": target_count,
        "buffer_count": buffer_count,
        "minimum_listed_days": minimum_listed_days,
        "transaction_cost_bps": transaction_cost_bps,
        "impact_bps": impact_bps,
        "stage": stage,
        "resume": resume,
        "robustness_matrix": {
            "turnover_definitions": ["mean_20", "mean_60", "median_60", "mean_120"],
            "participation_cases": [
                "unconstrained",
                "prior_amount_5pct",
                "prior_amount_10pct",
                "prior_amount_20pct",
            ],
            "initial_capital": initial_capital,
            "lot_size": 100,
            "development_period": "2015-01-01 to 2023-12-31",
            "holdout_period": "2024-01-01 to 2026-12-31",
        },
        "execution_rules": [
            "next trading session target execution",
            "suspension and price-limit blocking",
            "known delisting terminal return",
            "baseline continuous weight accounting",
            "sensitivity target entries rounded to lots using prior close",
            "sensitivity caps use prior observed traded amount",
        ],
        "metadata_file": str(outdir / "exploration_meta.json"),
    }
    _write_json(metadata, outdir / "exploration_meta.json")
    _write_report(
        outdir,
        summary=summary,
        yearly=yearly,
        periods=periods,
        signal_correlations=signal_correlations,
        robustness=robustness,
        rebalance_matrix=rebalance_matrix,
        share_ledger_matrix=share_ledger_matrix,
        reconciliation_matrix=reconciliation_matrix,
        capacity_ladder=capacity_ladder,
        joint_matrix=joint_matrix,
        metadata=metadata,
    )
    return outdir


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore small-cap and low-turnover candidates")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--start-date", default="2015-01-01")
    parser.add_argument("--end-date", default="2026-07-31")
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--minimum-listed-days", type=int, default=180)
    parser.add_argument("--target-count", type=int, default=40)
    parser.add_argument("--buffer-count", type=int, default=60)
    parser.add_argument("--initial-capital", type=float, default=100_000_000.0)
    parser.add_argument("--impact-bps", type=float, default=0.0)
    parser.add_argument("--stage", choices=("all", "ledger", "capacity"), default="all")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    output = run_exploration(
        data_root=Path(args.data_root).expanduser().resolve(),
        outdir=Path(args.outdir).expanduser().resolve(),
        start_date=args.start_date,
        end_date=args.end_date,
        transaction_cost_bps=args.transaction_cost_bps,
        minimum_listed_days=args.minimum_listed_days,
        target_count=args.target_count,
        buffer_count=args.buffer_count,
        initial_capital=args.initial_capital,
        impact_bps=args.impact_bps,
        stage=args.stage,
        resume=args.resume,
    )
    print(f"[OK] exploration artifacts -> {output}")


if __name__ == "__main__":
    main()
