"""市场理解探索：过去 20 年 A 股最差的 10 个交易日有什么共同点。

找等权市场收益最差的 10 天，看：
- 日期分布（哪年/哪月/星期几）
- 次日表现（大跌后反弹还是继续跌）
- 是否集中在某些年份/时期

运行：
    uv run python explore_worst_days.py
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("worst")

ROOT = Path(__file__).resolve().parent
DATA_SOURCE = Path(
    os.environ.get(
        "A_SHARE_DAILY_DIR",
        "/home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data",
    )
)
START = "2005-01-01"
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
    df["next_ret"] = df["ret"].shift(-1)
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["weekday"] = df["date"].dt.day_name()

    worst10 = df.nsmallest(10, "ret")
    LOGGER.info("== 最差 10 个交易日 ==")
    for _, row in worst10.iterrows():
        LOGGER.info(
            "%s (%s %s): %.2f%% 次日: %+.2f%%",
            row["date"].date(), row["weekday"][:3], row["year"],
            row["ret"], row["next_ret"] if not pd.isna(row["next_ret"]) else 0,
        )

    LOGGER.info("== 年份分布 ==")
    year_counts = worst10.groupby("year").size()
    LOGGER.info(year_counts.to_dict())
    LOGGER.info("== 星期分布 ==")
    LOGGER.info(worst10.groupby("weekday").size().to_dict())
    LOGGER.info("次日平均: %+.2f%%, 次日胜率: %.0f%%",
                worst10["next_ret"].mean(), (worst10["next_ret"] > 0).mean() * 100)


if __name__ == "__main__":
    main()
