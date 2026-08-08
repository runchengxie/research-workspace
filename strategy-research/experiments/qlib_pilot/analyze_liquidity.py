"""流动性阈值分析：不同 universe 规模（top N）的可行性与成交率。

全市场 top_k=30 回测成交率仅 51%，因为包含大量低流动性小盘股。本脚本分析
按每日成交额取 top N（800/1200/1500/2000/全市场）时：
- 每天能覆盖多少股票（universe 规模）
- top N 里流动性中位数/最小值（判断是否可执行）
- 模拟 top_k=30 组合需要成交的量 vs 该股票的日成交额（冲击成本）

运行：
    uv run python analyze_liquidity.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("liq_analyze")

DATA_SOURCE = Path(
    os.environ.get(
        "A_SHARE_DAILY_DIR",
        "/home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data",
    )
)

START = "2024-01-01"
END = "2024-12-31"
TOP_NS = [800, 1200, 1500, 2000]
TOP_K = 30
PORTFOLIO_NOTIONAL = 10_000_000.0  # 1千万组合


def load_amount_panel() -> pd.DataFrame:
    files = sorted(DATA_SOURCE.glob("*.parquet"))
    frames = []
    for f in files:
        df = pd.read_parquet(f, columns=["trade_date", "amount"])
        if df.empty:
            continue
        df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
        df = df[(df["trade_date"] >= pd.Timestamp(START)) & (df["trade_date"] <= pd.Timestamp(END))]
        if df.empty:
            continue
        df["symbol"] = f.stem
        frames.append(df[["trade_date", "symbol", "amount"]])
    panel = pd.concat(frames, ignore_index=True)
    LOGGER.info("panel: %d rows, %d symbols", len(panel), panel["symbol"].nunique())
    return panel


def analyze(panel: pd.DataFrame) -> None:
    # 每天的成交额
    daily = panel.pivot_table(index="trade_date", columns="symbol", values="amount", aggfunc="sum")
    daily = daily.sort_index()
    n_days = len(daily)
    LOGGER.info("trading days: %d", n_days)

    for n in TOP_NS:
        # 每天取成交额 top n
        top_n_daily = daily.apply(lambda row: row.nlargest(n).dropna(), axis=1)
        # 第 TOP_K 名（组合会买入的最差流动性标的）每天的成交额
        kth_liq = top_n_daily.apply(lambda row: row.iloc[min(TOP_K, len(row)) - 1], axis=1)
        # top n 全部标的的中位成交额
        med_liq = top_n_daily.apply(lambda row: row.median(), axis=1)
        per_name = PORTFOLIO_NOTIONAL / TOP_K
        impact_30th = (per_name / kth_liq).median()
        # 也看第 TOP_K 名成交额本身
        LOGGER.info(
            "top%-4d 第%d名中位成交额: %.1f万元, 全组中位成交额: %.1f万元, "
            "买入第%d名冲击: %.1f%%",
            n,
            TOP_K,
            kth_liq.median() / 1e4,
            med_liq.median() / 1e4,
            TOP_K,
            impact_30th * 100,
        )


def main() -> None:
    panel = load_amount_panel()
    analyze(panel)


if __name__ == "__main__":
    main()
