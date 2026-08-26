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

from style_factors.data import load_sw_industry_membership
from style_factors.liquidity_signals import build_liquidity_control_panel
from style_factors.robustness_data import load_robustness_market_data
from style_factors.small_cap_low_turnover import (
    SIGNAL_COLUMNS,
    build_candidate_signal_panel,
    build_lagged_turnover_panel,
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


def _correlations(daily: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in daily if column.endswith("_net")]
    if not columns:
        return pd.DataFrame()
    return daily[columns].corr().rename(
        columns=lambda column: column.removesuffix("_net"),
        index=lambda index: index.removesuffix("_net"),
    )


def _signal_correlations(panel: pd.DataFrame) -> pd.DataFrame:
    def group_correlation(group: pd.DataFrame, left: str, right: str) -> float:
        return float(group[left].corr(group[right]))

    columns = [column for column in SIGNAL_COLUMNS.values() if column in panel]
    groups = panel.groupby("trade_date", sort=False)
    rows: list[dict[str, Any]] = []
    for left_index, left in enumerate(columns):
        for right in columns[left_index + 1 :]:
            values = groups[[left, right]].apply(
                group_correlation,
                left,
                right,
                include_groups=False,
            ).dropna()
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
        "- Equal-weight target portfolio with a 40-name target and 60-name buffer.",
        "- Formation eligibility excludes immature listings, ST names, suspended names, "
        "and names outside the point-in-time universe.",
        "- Daily simulation uses the shared suspension, price-limit, delisting, and "
        "transaction-cost engine.",
        "- Target changes are submitted on the next trading session, so the "
        "formation-day return is not captured by the new holdings.",
        "- Weights are continuous research weights; integer-lot rounding is a "
        "remaining implementation limitation.",
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
    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- A positive composite is not evidence that low turnover is causal; compare "
            "it with small-cap-only, low-turnover-only, residualized low-turnover, and controls.",
            "- Net results remain exploratory until costs, liquidity, integer lots, and "
            "live execution assumptions are independently reviewed.",
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
    end_date: str | None = None,
    transaction_cost_bps: float = 10.0,
    minimum_listed_days: int = 180,
    target_count: int = 40,
    buffer_count: int = 60,
) -> Path:
    """Run the candidate comparison and write reproducible research outputs."""
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps must be non-negative")
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
    controls = build_liquidity_control_panel(
        controls_daily,
        basics,
        formation_dates,
        sw_membership=sw_membership if not sw_membership.empty else None,
    )
    turnover = build_lagged_turnover_panel(daily_clean, formation_dates)
    signal_panel = build_candidate_signal_panel(controls, turnover)
    candidates = dict(SIGNAL_COLUMNS)
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
        "target_count": target_count,
        "buffer_count": buffer_count,
        "minimum_listed_days": minimum_listed_days,
        "transaction_cost_bps": transaction_cost_bps,
        "execution_rules": [
            "next trading session target execution",
            "suspension and price-limit blocking",
            "known delisting terminal return",
            "continuous weight accounting; integer lots not modeled",
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
        metadata=metadata,
    )
    return outdir


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore small-cap and low-turnover candidates")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--start-date", default="2015-01-01")
    parser.add_argument("--end-date")
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--minimum-listed-days", type=int, default=180)
    parser.add_argument("--target-count", type=int, default=40)
    parser.add_argument("--buffer-count", type=int, default=60)
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
    )
    print(f"[OK] exploration artifacts -> {output}")


if __name__ == "__main__":
    main()
