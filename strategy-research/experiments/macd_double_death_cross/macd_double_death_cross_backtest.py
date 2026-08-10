#!/usr/bin/env python3
"""Backtest for the MACD double-death-cross A-share strategy.

Signal rules, all evaluated at the signal-day close:

1. 20 个交易日内连续 2 个 MACD 死叉，第二个死叉日作为信号日买入。
   MACD 采用标准 (12, 26, 9) 参数，DIF 下穿 DEA 记为死叉。
2. 市值低于 100 亿，即 total_mv < 100 亿（total_mv 单位为万元）。
3. 市盈率大于 50 倍，默认使用 pe_ttm。
4. 近 35 个交易日累计换手率大于 100%（turnover_rate 单位为百分数）。
5. 近 126 个交易日震幅小于 100%，震幅 = 区间最高价 / 区间最低价 - 1。

执行与退出：

- 信号日收盘后筛选，次日开盘价买入；次日停牌、ST 或开盘一字涨停则跳过该信号。
- 多个退出策略分别回测：固定持有 5/10/20/60 个交易日收盘卖出，
  以及 MACD 金叉收盘卖出。
- 组合采用等权持仓，每个信号为一个仓位，同一标的的持仓退出前不重复开仓。
- 成本假设：买入滑点、卖出滑点各 5 bps，往返交易成本 12 bps。

回测区间从 2016-01-01 至数据末尾，2015-07 之后的数据用于指标预热。
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_DAILY_DIR = (
    "/home/richard/data/market-data-platform/assets/tushare/a_share/"
    "daily/a_share_all_daily_clean_latest/data"
)
DEFAULT_OUT_BASE = Path("artifacts/reports")

NEEDED_COLUMNS = [
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "turnover_rate",
    "pe_ttm",
    "pe",
    "total_mv",
    "circ_mv",
    "is_suspended",
    "is_st",
    "is_limit_up",
    "is_limit_down",
    "up_limit",
    "down_limit",
    "listed_days",
    "symbol",
]

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

DEATH_CROSS_WINDOW_DAYS = 20
MCAP_CEIL_CNY = 100e8  # 100 亿人民币
PE_FLOOR = 50.0
TURNOVER_WINDOW = 35
TURNOVER_FLOOR = 100.0  # 百分数，累计换手率 > 100%
AMPLITUDE_WINDOW = 126  # 约 6 个月交易日
AMPLITUDE_CEIL = 1.0  # 100%
HOLD_DAYS = [5, 10, 20, 60]
ENTRY_SLIPPAGE_BPS = 5.0
EXIT_SLIPPAGE_BPS = 5.0
ROUND_TRIP_COST_BPS = 12.0


def _json_default(value: object) -> str:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (pd.Timestamp, pd.NaT)):
        return None if pd.isna(value) else str(value)
    return str(value)


def load_panel(daily_dir: Path, *, start_date: str, end_date: str | None) -> pd.DataFrame:
    files = sorted(daily_dir.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No symbol parquet files found under {daily_dir}")
    start = start_date.replace("-", "")
    end = end_date.replace("-", "") if end_date else "99999999"
    parts: list[pd.DataFrame] = []
    for idx, path in enumerate(files, start=1):
        frame = pd.read_parquet(path, columns=NEEDED_COLUMNS)
        date_text = frame["trade_date"].astype(str)
        mask = date_text.ge(start) & date_text.le(end)
        frame = frame.loc[mask].copy()
        if frame.empty:
            continue
        frame["trade_date"] = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d")
        parts.append(frame)
        if idx % 1000 == 0:
            print(f"[load] {idx:,}/{len(files):,} files, rows={sum(len(p) for p in parts):,}")
    if not parts:
        raise ValueError("No rows loaded for requested date range")
    panel = pd.concat(parts, ignore_index=True)
    panel["symbol"] = panel["symbol"].astype(str)
    panel = panel.drop_duplicates(["trade_date", "symbol"], keep="last")
    panel = panel.sort_values(["symbol", "trade_date"]).reset_index(drop=True)
    print(
        "[load] rows={:,} symbols={:,} dates={}..{}".format(
            len(panel),
            panel["symbol"].nunique(),
            panel["trade_date"].min().date(),
            panel["trade_date"].max().date(),
        )
    )
    return panel


def ema_series(values: pd.Series, span: int) -> pd.Series:
    return values.ewm(span=span, adjust=False, min_periods=span).mean()


def compute_macd(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    grouped = out.groupby("symbol", sort=False)
    out["ema_fast"] = grouped["close"].transform(lambda s: ema_series(s, MACD_FAST))
    out["ema_slow"] = grouped["close"].transform(lambda s: ema_series(s, MACD_SLOW))
    out["dif"] = out["ema_fast"] - out["ema_slow"]
    out["dea"] = grouped["dif"].transform(lambda s: ema_series(s, MACD_SIGNAL))
    out["macd_bar"] = 2.0 * (out["dif"] - out["dea"])
    out["prev_dif"] = grouped["dif"].shift(1)
    out["prev_dea"] = grouped["dea"].shift(1)
    out["is_death_cross"] = (
        out["dif"].lt(out["dea"])
        & out["prev_dif"].ge(out["prev_dea"])
    )
    out["is_golden_cross"] = (
        out["dif"].gt(out["dea"])
        & out["prev_dif"].le(out["prev_dea"])
    )
    return out


def add_windows(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    grouped = out.groupby("symbol", sort=False)
    out["turnover_sum35"] = grouped["turnover_rate"].transform(
        lambda s: s.rolling(TURNOVER_WINDOW, min_periods=TURNOVER_WINDOW).sum()
    )
    out["max_high126"] = grouped["high"].transform(
        lambda s: s.rolling(AMPLITUDE_WINDOW, min_periods=AMPLITUDE_WINDOW).max()
    )
    out["min_low126"] = grouped["low"].transform(
        lambda s: s.rolling(AMPLITUDE_WINDOW, min_periods=AMPLITUDE_WINDOW).min()
    )
    return out


def collect_signal_dates(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for symbol, group in panel.groupby("symbol", sort=False):
        cross_mask = group["is_death_cross"].to_numpy()
        cross_idx = np.flatnonzero(cross_mask)
        if len(cross_idx) < 2:
            continue
        for first_pos, second_pos in zip(cross_idx[:-1], cross_idx[1:], strict=False):
            trading_gap = int(second_pos - first_pos)
            if trading_gap <= DEATH_CROSS_WINDOW_DAYS:
                rows.append(
                    {
                        "symbol": symbol,
                        "first_death_cross": group.iloc[first_pos]["trade_date"],
                        "signal_date": group.iloc[second_pos]["trade_date"],
                        "trading_gap": trading_gap,
                    }
                )
    signals = pd.DataFrame(rows)
    if signals.empty:
        return signals
    return signals.sort_values(["signal_date", "symbol"]).reset_index(drop=True)


def add_next_session(panel: pd.DataFrame) -> pd.DataFrame:
    market_dates = sorted(panel["trade_date"].unique())
    next_map = {
        cur: nxt for cur, nxt in zip(market_dates, market_dates[1:], strict=False)
    }
    panel["next_trade_date"] = panel["trade_date"].map(next_map)
    return panel


def build_signal_rows(
    panel: pd.DataFrame,
    signals: pd.DataFrame,
    *,
    start_date: str,
) -> pd.DataFrame:
    signal_cols = [
        "symbol",
        "trade_date",
        "next_trade_date",
        "open",
        "high",
        "low",
        "close",
        "turnover_sum35",
        "max_high126",
        "min_low126",
        "pe_ttm",
        "pe",
        "total_mv",
        "circ_mv",
        "is_suspended",
        "is_st",
        "is_limit_up",
        "listed_days",
    ]
    panel_slice = panel[signal_cols].rename(columns={"trade_date": "signal_date"})
    merged = signals.merge(panel_slice, on=["symbol", "signal_date"], how="left")
    start_ts = pd.Timestamp(start_date)
    merged = merged.loc[merged["signal_date"].ge(start_ts)].copy()

    valid = (
        merged["next_trade_date"].notna()
        & merged["signal_date"].notna()
    )
    merged = merged.loc[valid].copy()

    next_cols = [
        "symbol",
        "trade_date",
        "open",
        "close",
        "high",
        "low",
        "up_limit",
        "is_suspended",
        "is_st",
        "is_limit_up",
    ]
    next_panel = panel[next_cols].rename(
        columns={
            "trade_date": "next_trade_date",
            "open": "next_open",
            "close": "next_close",
            "high": "next_high",
            "low": "next_low",
            "up_limit": "next_up_limit",
            "is_suspended": "next_is_suspended",
            "is_st": "next_is_st",
            "is_limit_up": "next_is_limit_up",
        }
    )
    merged = merged.merge(next_panel, on=["symbol", "next_trade_date"], how="left")

    entry_blocked = (
        merged["next_is_suspended"].astype("boolean").fillna(False).astype(bool)
        | merged["next_is_st"].astype("boolean").fillna(False).astype(bool)
        | (
            merged["next_is_limit_up"].astype("boolean").fillna(False).astype(bool)
            & merged["next_open"].ge(merged["next_up_limit"] * 0.999)
        )
    )
    merged["entry_blocked"] = entry_blocked.fillna(False).astype(bool)
    merged["entry_price"] = merged["next_open"].where(~merged["entry_blocked"])
    return merged


def apply_filters(signals: pd.DataFrame) -> pd.DataFrame:
    filtered = signals.copy()
    filtered["mcap_ok"] = filtered["total_mv"].lt(MCAP_CEIL_CNY / 1e4)
    filtered["pe_ok"] = filtered["pe_ttm"].gt(PE_FLOOR)
    filtered["turnover_ok"] = filtered["turnover_sum35"].gt(TURNOVER_FLOOR)
    filtered["amplitude_ok"] = (
        filtered["min_low126"].gt(0)
        & (filtered["max_high126"] / filtered["min_low126"] - 1.0).lt(AMPLITUDE_CEIL)
    )
    filtered["tradable_ok"] = (
        ~filtered["is_suspended"].astype("boolean").fillna(False).astype(bool)
        & ~filtered["is_st"].astype("boolean").fillna(False).astype(bool)
        & pd.to_numeric(filtered["listed_days"], errors="coerce").fillna(0).ge(60)
    )
    filtered["signal_ok"] = (
        filtered["mcap_ok"]
        & filtered["pe_ok"]
        & filtered["turnover_ok"]
        & filtered["amplitude_ok"]
        & filtered["tradable_ok"]
    )
    return filtered


def run_exit_policy(
    signals: pd.DataFrame,
    panel: pd.DataFrame,
    *,
    hold_days: int | None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    per_symbol = {
        symbol: group
        for symbol, group in panel.groupby("symbol", sort=False)
    }

    for symbol, group in signals.groupby("symbol", sort=False):
        bars = per_symbol.get(symbol)
        if bars is None:
            continue
        position_exit_bound: pd.Timestamp | None = None
        for _, signal in group.sort_values("signal_date").iterrows():
            entry_date = signal["next_trade_date"]
            entry_price = float(signal["entry_price"])
            if not np.isfinite(entry_price) or entry_price <= 0:
                continue
            if position_exit_bound is not None and pd.Timestamp(entry_date) <= position_exit_bound:
                continue
            entry_bars = bars.loc[bars["trade_date"].eq(pd.Timestamp(entry_date))]
            if entry_bars.empty:
                continue
            entry_pos = bars.index.get_loc(entry_bars.index[0])
            available = bars.iloc[entry_pos + 1:]
            if available.empty:
                continue
            if hold_days is not None:
                exit_row = available.iloc[hold_days - 1] if len(available) >= hold_days else None
                exit_reason = "hold" if exit_row is not None else "no_exit"
            else:
                golden = available.loc[available["is_golden_cross"]]
                if golden.empty:
                    exit_reason = "no_exit"
                    exit_row = None
                else:
                    exit_row = golden.iloc[0]
                    exit_reason = "golden_cross"
            if exit_row is None:
                position_exit_bound = bars["trade_date"].max()
                continue
            exit_price = float(exit_row["close"])
            exit_date = exit_row["trade_date"]
            hold_n = int(
                len(
                    bars.loc[
                        (bars["trade_date"] > pd.Timestamp(entry_date))
                        & (bars["trade_date"] <= pd.Timestamp(exit_date))
                    ]
                )
            )
            position_exit_bound = pd.Timestamp(exit_date)
            rows.append(
                {
                    "symbol": symbol,
                    "signal_date": pd.Timestamp(signal["signal_date"]),
                    "first_death_cross": signal["first_death_cross"],
                    "entry_date": pd.Timestamp(entry_date),
                    "entry_price": entry_price,
                    "exit_date": pd.Timestamp(exit_date),
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "hold_days": hold_n,
                    "mcap_ok": signal["mcap_ok"],
                    "pe_ok": signal["pe_ok"],
                    "turnover_ok": signal["turnover_ok"],
                    "amplitude_ok": signal["amplitude_ok"],
                    "signal_ok": signal["signal_ok"],
                }
            )
    trades = pd.DataFrame(rows)
    return trades


def trade_metrics(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    grouped = trades.groupby("exit_policy", sort=False)
    rows: list[dict[str, object]] = []
    for exit_policy, group in grouped:
        returns = group["net_return"]
        rows.append(
            {
                "exit_policy": str(exit_policy),
                "n_trades": len(group),
                "win_rate": float((returns > 0).mean()),
                "avg_return": float(returns.mean()),
                "median_return": float(returns.median()),
                "avg_hold_days": float(group["hold_days"].mean()),
                "median_hold_days": float(group["hold_days"].median()),
            }
        )
    return pd.DataFrame(rows).sort_values("exit_policy")


def build_portfolio_curve(
    trades: pd.DataFrame,
    panel: pd.DataFrame,
    *,
    start_date: str,
) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    market_dates = pd.DatetimeIndex(sorted(panel["trade_date"].unique()))
    start_ts = pd.Timestamp(start_date)
    trading_dates = market_dates[market_dates >= start_ts]
    trade_schedule = {
        date: group
        for date, group in trades.groupby("entry_date", sort=False)
    }
    by_symbol = {
        symbol: group.set_index("trade_date")
        for symbol, group in panel.groupby("symbol", sort=False)
    }
    curve_rows: list[dict[str, object]] = []
    open_positions: list[dict[str, object]] = []
    for date in trading_dates:
        for _, trade in trade_schedule.get(date, pd.DataFrame()).iterrows():
            open_positions.append(
                {
                    "symbol": trade["symbol"],
                    "entry_date": pd.Timestamp(trade["entry_date"]),
                    "entry_price": float(trade["entry_price"]),
                    "exit_date": pd.Timestamp(trade["exit_date"]),
                    "exit_price": float(trade["exit_price"]),
                    "prev_mark": float(trade["entry_price"]),
                }
            )
        position_returns: list[float] = []
        still_open: list[dict[str, object]] = []
        for position in open_positions:
            symbol_bars = by_symbol.get(position["symbol"])
            date_key = date
            exiting = pd.Timestamp(position["exit_date"]) <= date
            if exiting:
                mark = position["exit_price"]
            else:
                if symbol_bars is None or date_key not in symbol_bars.index:
                    still_open.append(position)
                    continue
                mark = float(symbol_bars.loc[date_key, "close"])
            if position["prev_mark"] > 0 and mark > 0:
                position_returns.append(mark / position["prev_mark"] - 1.0)
            if exiting:
                continue
            position["prev_mark"] = mark
            still_open.append(position)
        open_positions = still_open
        curve_rows.append(
            {
                "trade_date": date,
                "n_positions": len(open_positions),
                "portfolio_return": float(np.mean(position_returns))
                if position_returns
                else 0.0,
            }
        )
    return pd.DataFrame(curve_rows)


def portfolio_metrics(curve: pd.DataFrame) -> pd.DataFrame:
    if curve.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for exit_policy, group in curve.groupby("exit_policy", sort=False):
        returns = group["portfolio_return"]
        nav = (1.0 + returns).prod()
        days = len(group)
        years = days / 252.0
        ann_return = (1.0 + returns).prod() ** (1.0 / years) - 1.0 if years > 0 else None
        vol = returns.std(ddof=0)
        ann_vol = vol * math.sqrt(252.0)
        dd = (1.0 + returns).cumprod().div((1.0 + returns).cumprod().cummax()) - 1.0
        benchmark_nav = (1.0 + group["benchmark_return"]).prod()
        rows.append(
            {
                "exit_policy": str(exit_policy),
                "n_positions_avg": float(group["n_positions"].mean()),
                "days": days,
                "total_return": float(nav - 1.0),
                "ann_return": float(ann_return) if ann_return is not None else None,
                "ann_vol": float(ann_vol) if ann_vol > 0 else None,
                "sharpe": float(returns.mean() / vol * math.sqrt(252.0)) if vol > 0 else None,
                "max_drawdown": float(dd.min()),
                "win_rate_days": float(returns.gt(0).mean()),
                "benchmark_total_return": float(benchmark_nav - 1.0),
                "excess_total_return": float(nav / benchmark_nav - 1.0),
            }
        )
    return pd.DataFrame(rows).sort_values("exit_policy")


def compute_benchmark(panel: pd.DataFrame, start_date: str) -> pd.DataFrame:
    frame = panel.loc[
        (panel["trade_date"] >= pd.Timestamp(start_date))
        & panel["is_suspended"].eq(False)
    ].copy()
    frame = frame.sort_values(["symbol", "trade_date"]).copy()
    frame["ret_1"] = frame.groupby("symbol", sort=False)["close"].pct_change()
    grouped = frame.groupby("trade_date")["ret_1"].mean().reset_index()
    grouped.columns = ["trade_date", "benchmark_return"]
    return grouped


def summarize_trades(trades: pd.DataFrame, summary: dict[str, object]) -> dict[str, object]:
    summary["signal_filters_share"] = {}
    if not trades.empty:
        n = len(trades)
        for column in ["mcap_ok", "pe_ok", "turnover_ok", "amplitude_ok", "signal_ok"]:
            summary["signal_filters_share"][column] = float(trades[column].mean())
    return summary


def write_report(
    outdir: Path,
    *,
    config: dict[str, object],
    signal_summary: dict[str, object],
    trade_metrics: pd.DataFrame,
    portfolio_metrics: pd.DataFrame,
    trades: pd.DataFrame,
) -> None:
    def table(frame: pd.DataFrame, *, max_rows: int = 40, index: bool = False) -> str:
        if frame.empty:
            return "No rows."
        return "```text\n" + frame.head(max_rows).to_string(index=index) + "\n```"

    lines = [
        "# MACD 双死叉 A 股策略回测",
        "",
        "## 策略规则",
        "",
        "- 20 个交易日内连续 2 个 MACD(12,26,9) 死叉，第二个死叉日收盘确认信号",
        "- 次日开盘价买入，次日停牌、ST 或开盘一字涨停则跳过",
        "- 市值低于 100 亿（total_mv，万元）",
        "- 市盈率大于 50 倍（pe_ttm）",
        "- 近 35 个交易日累计换手率大于 100%（turnover_rate，百分数）",
        "- 近 126 个交易日震幅小于 100%（最高价 / 最低价 - 1）",
        "- 剔除 ST、停牌、上市不足 60 天个股",
        "- 同一标的持仓未退出前不重复开仓",
        "- 成本假设：买入滑点 5 bps，卖出滑点 5 bps，往返成本 12 bps",
        "",
        "## 配置",
        "",
        "```json",
        json.dumps(config, indent=2, ensure_ascii=False, default=_json_default),
        "```",
        "",
        "## 信号与筛选",
        "",
        "```json",
        json.dumps(signal_summary, indent=2, ensure_ascii=False, default=_json_default),
        "```",
        "",
        "## 单笔交易统计（按退出策略）",
        "",
        table(trade_metrics, index=False),
        "",
        "## 组合等权净值统计",
        "",
        table(portfolio_metrics, index=False),
        "",
        "## 提示",
        "",
        "- 组合净值采用等权再平衡近似，未计入资金利用率和冲击成本",
        "- 同一标的多次触发信号时，前一持仓退出后才允许再次开仓",
        "- 无退出信号的交易不计入单笔统计，但已包含在信号筛选计数中",
        "- 结果反映规则是否有效，不等于可交易策略的承诺收益",
        "",
    ]
    (outdir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    daily_dir = Path(args.daily_dir).expanduser().resolve()
    outdir = (
        Path(args.outdir).expanduser().resolve()
        if args.outdir
        else DEFAULT_OUT_BASE / f"macd_double_death_cross_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    )
    outdir.mkdir(parents=True, exist_ok=True)

    config = {
        "daily_dir": str(daily_dir),
        "start_date": args.start_date,
        "end_date": args.end_date,
        "macd": (MACD_FAST, MACD_SLOW, MACD_SIGNAL),
        "death_cross_window_days": DEATH_CROSS_WINDOW_DAYS,
        "mcap_ceiling_cny": MCAP_CEIL_CNY,
        "pe_floor": PE_FLOOR,
        "turnover_window": TURNOVER_WINDOW,
        "turnover_floor_pct": TURNOVER_FLOOR,
        "amplitude_window": AMPLITUDE_WINDOW,
        "amplitude_ceiling": AMPLITUDE_CEIL,
        "hold_days": args.hold_days,
        "entry_slippage_bps": ENTRY_SLIPPAGE_BPS,
        "exit_slippage_bps": EXIT_SLIPPAGE_BPS,
        "round_trip_cost_bps": ROUND_TRIP_COST_BPS,
    }
    (outdir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False, default=_json_default) + "\n",
        encoding="utf-8",
    )

    load_start = "2015-07-01"
    panel = load_panel(daily_dir, start_date=load_start, end_date=args.end_date)
    panel = compute_macd(panel)
    panel = add_windows(panel)
    panel = add_next_session(panel)

    signals = collect_signal_dates(panel)
    print(f"[signal] raw double-death-cross rows={len(signals):,}")
    signal_rows = build_signal_rows(panel, signals, start_date=args.start_date)
    signal_rows = apply_filters(signal_rows)
    print(f"[signal] within backtest window rows={len(signal_rows):,} signal_ok={int(signal_rows['signal_ok'].sum()):,}")

    all_trades: list[pd.DataFrame] = []
    hold_values = [int(v) for v in args.hold_days.split(",") if v.strip()]
    for hold in hold_values:
        trades = run_exit_policy(
            signal_rows.loc[signal_rows["signal_ok"]],
            panel,
            hold_days=hold,
        )
        if not trades.empty:
            trades["exit_policy"] = f"hold_{hold}d"
            trades["hold_days"] = hold
        all_trades.append(trades)
    golden_trades = run_exit_policy(
        signal_rows.loc[signal_rows["signal_ok"]],
        panel,
        hold_days=None,
    )
    if not golden_trades.empty:
        golden_trades["exit_policy"] = "golden_cross"
    all_trades.append(golden_trades)
    trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()

    for name, group in trades.groupby("exit_policy", sort=False):
        entry_price = group["entry_price"]
        exit_price = group["exit_price"]
        net_return = (
            exit_price * (1.0 - EXIT_SLIPPAGE_BPS / 1e4)
            / (entry_price * (1.0 + ENTRY_SLIPPAGE_BPS / 1e4))
            - 1.0
            - ROUND_TRIP_COST_BPS / 1e4
        )
        trades.loc[group.index, "net_return"] = net_return

    tstats = trade_metrics(trades)
    benchmark = compute_benchmark(panel, args.start_date)
    curves: list[pd.DataFrame] = []
    for name, group in trades.groupby("exit_policy", sort=False):
        curve = build_portfolio_curve(group, panel, start_date=args.start_date)
        curve = curve.merge(benchmark, on="trade_date", how="left")
        curve["benchmark_return"] = curve["benchmark_return"].fillna(0.0)
        curve["exit_policy"] = name
        curves.append(curve)
    curve_all = pd.concat(curves, ignore_index=True) if curves else pd.DataFrame()
    pstats = portfolio_metrics(curve_all)

    signal_summary: dict[str, object] = {
        "signal_rows": len(signal_rows),
        "signal_rows_ok": int(signal_rows["signal_ok"].sum()) if not signal_rows.empty else 0,
        "filter_counts": (
            {
                column: int(signal_rows[column].sum())
                for column in ["mcap_ok", "pe_ok", "turnover_ok", "amplitude_ok", "tradable_ok", "signal_ok"]
            }
            if not signal_rows.empty
            else {}
        ),
    }
    if not trades.empty:
        signal_summary["trades_total"] = len(trades)
        signal_summary["trades_by_policy"] = {
            str(name): int(len(group)) for name, group in trades.groupby("exit_policy", sort=False)
        }

    summary = {
        "config": config,
        "signal_summary": signal_summary,
        "portfolio": pstats.to_dict(orient="records"),
        "per_trade": tstats.to_dict(orient="records"),
    }
    (outdir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default) + "\n",
        encoding="utf-8",
    )
    signal_rows.to_csv(outdir / "signal_rows.csv", index=False)
    if not trades.empty:
        trades.to_csv(outdir / "trade_details.csv", index=False)
    if not curve_all.empty:
        curve_all.to_csv(outdir / "portfolio_curves.csv", index=False)
    if not tstats.empty:
        tstats.to_csv(outdir / "trade_metrics.csv", index=False)
    if not pstats.empty:
        pstats.to_csv(outdir / "portfolio_metrics.csv", index=False)

    write_report(
        outdir,
        config=config,
        signal_summary=signal_summary,
        trade_metrics=tstats,
        portfolio_metrics=pstats,
        trades=trades,
    )
    print(f"[done] {outdir}")
    return outdir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-dir", default=str(DEFAULT_DAILY_DIR))
    parser.add_argument("--outdir")
    parser.add_argument("--start-date", default="2016-01-01")
    parser.add_argument("--end-date")
    parser.add_argument("--hold-days", default="5,10,20,60")
    return parser


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
