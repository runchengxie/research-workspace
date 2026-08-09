"""样本质量过滤实验：按流动性过滤训练样本能否改善 OOS。

假设：全市场 OOS IC ~0 是因为小盘股信号不可靠。qlib DropnaLabel 思路：
训练前按流动性/样本质量过滤，只保留质量足够的股票。

方法：同一面板，滚动窗口，对比：
- baseline：全样本训练
- 流动性过滤：训练时只保留每日成交额 top N 的股票（如 top 800）
- 样本覆盖过滤：训练时要求该股票有足够历史样本（如 >= 100 天）

运行：
    uv run python explore_sample_filter.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("sample_filter")

ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parents[1]
DATA_SOURCE = Path(
    os.environ.get(
        "A_SHARE_DAILY_DIR",
        "/home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data",
    )
)

DATA_START = "2022-01-01"
DATA_END = "2024-12-31"
TRAIN_MONTHS = 18
VALID_MONTHS = 6
STEP_MONTHS = 6
LABEL_HORIZON = 20

FEATURES = [
    "ret_5", "ret_20", "ret_60",
    "rv_20", "rv_60",
    "log_vol", "vol",
    "volume_sma5_ratio", "volume_sma20_ratio", "volume_sma60_ratio",
    "amount_log", "turnover_rate", "pe_ttm", "pb", "pct_chg",
]

XGB_PARAMS = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "max_depth": 3,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "reg:squarederror",
    "random_state": 42,
}


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("trade_date").copy()
    close = df["adj_close"]
    vol = df["vol"]
    amount = df["amount"]
    df["ret_5"] = close.pct_change(5)
    df["ret_20"] = close.pct_change(20)
    df["ret_60"] = close.pct_change(60)
    df["rv_20"] = df["ret_5"].rolling(20).std()
    df["rv_60"] = df["ret_5"].rolling(60).std()
    df["log_vol"] = np.log1p(vol)
    df["vol"] = vol
    df["volume_sma5_ratio"] = vol / vol.rolling(5).mean()
    df["volume_sma20_ratio"] = vol / vol.rolling(20).mean()
    df["volume_sma60_ratio"] = vol / vol.rolling(60).mean()
    df["amount_log"] = np.log1p(amount)
    return df


def load_panel() -> pd.DataFrame:
    files = sorted(DATA_SOURCE.glob("*.parquet"))
    frames = []
    for f in files:
        df = pd.read_parquet(f)
        if "trade_date" not in df.columns or "adj_close" not in df.columns:
            continue
        df = df.copy()
        df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
        df = compute_features(df)
        df = df.sort_values("trade_date").set_index("trade_date")
        df["LABEL"] = df["adj_close"].shift(-LABEL_HORIZON) / df["adj_close"] - 1
        df = df.reset_index()
        df = df[(df["trade_date"] >= pd.Timestamp(DATA_START)) & (df["trade_date"] <= pd.Timestamp(DATA_END))]
        if df.empty:
            continue
        frames.append(df[["trade_date", "ts_code"] + FEATURES + ["LABEL", "amount"]])
    panel = pd.concat(frames, ignore_index=True)
    LOGGER.info("panel: %d rows, %d symbols", len(panel), panel["ts_code"].nunique())
    return panel


def build_windows(panel: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    dates = pd.to_datetime(panel["trade_date"].unique())
    start_cursor = pd.Timestamp(dates.min().year, dates.min().month, 1)
    end_cursor = pd.Timestamp(pd.Timestamp(DATA_END).year, pd.Timestamp(DATA_END).month, 1)
    windows = []
    cursor = start_cursor + pd.DateOffset(months=TRAIN_MONTHS)
    while cursor <= end_cursor:
        train_start = cursor - pd.DateOffset(months=TRAIN_MONTHS)
        valid_start = cursor
        if valid_start + pd.DateOffset(months=VALID_MONTHS) > end_cursor + pd.DateOffset(months=1):
            break
        windows.append((train_start, cursor, valid_start))
        cursor = cursor + pd.DateOffset(months=STEP_MONTHS)
    return windows


def daily_ic_mean(df: pd.DataFrame, pred_col: str, target_col: str = "LABEL") -> float:
    from scipy.stats import spearmanr

    ics: list[float] = []
    for _, group in df.groupby("trade_date"):
        sub = group[[pred_col, target_col]].dropna()
        if len(sub) < 2 or sub[target_col].nunique() < 2:
            continue
        ic, _ = spearmanr(sub[pred_col], sub[target_col])
        if not np.isnan(ic):
            ics.append(ic)
    return float(np.mean(ics)) if ics else np.nan


def run_window(panel, train_start, train_end, valid_start, *, filter_mode: str) -> float:
    from xgboost import XGBRegressor

    train = panel[(panel["trade_date"] >= train_start) & (panel["trade_date"] < valid_start)].copy()
    valid = panel[(panel["trade_date"] >= valid_start)].copy()
    valid = valid[valid["trade_date"] < valid_start + pd.DateOffset(months=VALID_MONTHS)]

    if filter_mode == "liquid800":
        # 训练时每天只保留成交额 top 800 的股票
        top800 = (
            train.groupby("trade_date")["amount"]
            .transform(lambda s: s >= s.nlargest(800).min() if len(s) > 800 else True)
        )
        train = train[top800]
    elif filter_mode == "min_samples":
        # 训练时要求该股票在训练期内有足够样本（>= 100 天）
        sample_counts = train.groupby("ts_code")["trade_date"].transform("count")
        train = train[sample_counts >= 100]

    train = train.dropna(subset=FEATURES + ["LABEL"])
    valid = valid.dropna(subset=FEATURES)
    if len(train) < 1000 or len(valid) < 100:
        return np.nan

    model = XGBRegressor(**XGB_PARAMS)
    model.fit(train[FEATURES], train["LABEL"])
    valid = valid.copy()
    valid["PRED"] = model.predict(valid[FEATURES])
    return daily_ic_mean(valid, "PRED")


def main() -> None:
    sys.path.insert(0, str(WORKSPACE_ROOT / "alpha-research" / "src"))
    panel = load_panel()
    windows = build_windows(panel)
    LOGGER.info("%d windows", len(windows))

    results = {mode: [] for mode in ["all", "liquid800", "min_samples"]}
    for t_start, t_end, v_start in windows:
        for mode in results:
            ic = run_window(panel, t_start, t_end, v_start, filter_mode=mode if mode != "all" else None)
            results[mode].append(ic)
        LOGGER.info(
            "w%d valid=%s all=%.4f liquid800=%.4f min_samples=%.4f",
            len(windows[0:]) + 1 - len([x for x in results["all"] if not np.isnan(x)]),
            v_start.date(),
            results["all"][-1], results["liquid800"][-1], results["min_samples"][-1],
        )

    LOGGER.info("== summary ==")
    for mode in results:
        vals = [v for v in results[mode] if not np.isnan(v)]
        LOGGER.info("%-12s mean=%.4f", mode, np.mean(vals))


if __name__ == "__main__":
    main()
