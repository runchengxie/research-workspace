"""市场理解探索：星期五效应。

用全市场日收益（等权）验证"星期五更容易跌"的说法。
数据：daily_clean（全市场个股 pct_chg），按星期几分组统计收益。

运行：
    uv run python explore_weekday_effect.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("weekday")

ROOT = Path(__file__).resolve().parent
DATA_SOURCE = Path(
    os.environ.get(
        "A_SHARE_DAILY_DIR",
        "/home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data",
    )
)
START = "2008-01-01"
END = "2026-08-07"
SAMPLE = 500  # 抽样股票数控制速度


def load_market_returns() -> pd.DataFrame:
    files = sorted(DATA_SOURCE.glob("*.parquet"))[:SAMPLE]
    frames = []
    for f in files:
        df = pd.read_parquet(f, columns=["trade_date", "pct_chg"])
        df = df.dropna()
        if df.empty:
            continue
        df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
        df = df[(df["trade_date"] >= pd.Timestamp(START)) & (df["trade_date"] <= pd.Timestamp(END))]
        if df.empty:
            continue
        frames.append(df[["trade_date", "pct_chg"]])
    panel = pd.concat(frames, ignore_index=True)
    # 每日等权平均收益 = 市场代理
    daily = panel.groupby("trade_date")["pct_chg"].mean()
    LOGGER.info("market proxy: %d days, %d stocks", len(daily), panel["trade_date"].nunique())
    return daily


def main() -> None:
    daily = load_market_returns()
    df = daily.reset_index()
    df["weekday"] = df["trade_date"].dt.dayofweek  # 0=Mon, 4=Fri
    df["weekday_name"] = df["trade_date"].dt.day_name()

    stats = df.groupby("weekday_name")["pct_chg"].agg(["mean", "std", "count", lambda s: (s > 0).mean()])
    stats.columns = ["mean", "std", "n_days", "win_rate"]
    stats = stats.reindex(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    )

    LOGGER.info("== 星期效应（每日等权市场收益） ==")
    for name, row in stats.iterrows():
        LOGGER.info(
            "%-9s  mean=%.3f%%  std=%.2f%%  n=%d  win=%.1f%%",
            name, row["mean"], row["std"], row["n_days"], row["win_rate"] * 100,
        )

    friday = stats.loc["Friday", "mean"]
    monday = stats.loc["Monday", "mean"]
    LOGGER.info("Friday vs Monday: %.3f%% vs %.3f%%", friday, monday)


if __name__ == "__main__":
    main()
