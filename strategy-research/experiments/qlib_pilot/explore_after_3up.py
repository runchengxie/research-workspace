"""市场理解探索：连续大涨 3 天后，第 4 天更容易涨还是跌。

用全市场等权日收益序列，找连续 3 天上涨（或大涨）的时段，
统计第 4 天收益，对比基线。

运行：
    uv run python explore_after_3up.py
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("after3")

ROOT = Path(__file__).resolve().parent
DATA_SOURCE = Path(
    os.environ.get(
        "A_SHARE_DAILY_DIR",
        "/home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data",
    )
)
START = "2008-01-01"
END = "2026-08-07"
SAMPLE = 500


def load_market_returns() -> pd.Series:
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
    daily = panel.groupby("trade_date")["pct_chg"].mean()
    LOGGER.info("market proxy: %d days", len(daily))
    return daily


def main() -> None:
    daily = load_market_returns()
    df = daily.reset_index()
    df.columns = ["date", "ret"]
    df = df.sort_values("date").reset_index(drop=True)

    # 连续上涨 3 天（ret > 0），取第 4 天收益
    df["up"] = df["ret"] > 0
    df["up3"] = df["up"] & df["up"].shift(1) & df["up"].shift(2)
    # 第 4 天收益 = up3 为 True 的下一行
    df["next_ret"] = df["ret"].shift(-1)
    after = df.loc[df["up3"], "next_ret"].dropna()
    baseline = df["ret"]
    # 连续大涨 3 天（ret > 1%）
    df["big_up"] = df["ret"] > 1.0
    df["big3"] = df["big_up"] & df["big_up"].shift(1) & df["big_up"].shift(2)
    after_big = df.loc[df["big3"], "next_ret"].dropna()

    LOGGER.info("基线：平均日收益 = %.3f%%, 胜率 = %.1f%%", baseline.mean(), (baseline > 0).mean() * 100)
    LOGGER.info("连续涨3天后：n=%d, 第4天平均 = %.3f%%, 胜率 = %.1f%%",
                len(after), after.mean(), (after > 0).mean() * 100)
    LOGGER.info("连续大涨3天后：n=%d, 第4天平均 = %.3f%%, 胜率 = %.1f%%",
                len(after_big), after_big.mean(), (after_big > 0).mean() * 100)


if __name__ == "__main__":
    main()
