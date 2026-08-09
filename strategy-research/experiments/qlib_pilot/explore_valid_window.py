"""验证期长度实验：更长验证期是否改善 OOS 信号可靠性。

假设：a_share 回测 OOS IC ~0 是因为验证期太短（5 个月度调仓）。
更长验证期（6/12 个月）应显示真实的 OOS 信号（实验已见 6 个月窗口 IC 0.10）。

方法：同一面板（全市场）、20 日标签，对比不同验证期长度的 OOS IC。

运行：
    uv run python explore_valid_window.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("valid_window")

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
TRAIN_MONTHS = 24
STEP_MONTHS = 12
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
        frames.append(df[["trade_date", "ts_code"] + FEATURES + ["LABEL"]])
    panel = pd.concat(frames, ignore_index=True)
    LOGGER.info("panel: %d rows, %d symbols", len(panel), panel["ts_code"].nunique())
    return panel


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


def run_window(panel, train_start, valid_start, valid_months: int) -> float:
    from xgboost import XGBRegressor

    train = panel[(panel["trade_date"] >= train_start) & (panel["trade_date"] < valid_start)].copy()
    valid = panel[(panel["trade_date"] >= valid_start)].copy()
    valid = valid[valid["trade_date"] < valid_start + pd.DateOffset(months=valid_months)]

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

    # 固定训练窗 24 个月，验证窗从 2024-01 开始，测 3/6/12 个月验证期
    train_start = pd.Timestamp("2022-01-01")
    valid_start = pd.Timestamp("2024-01-01")
    for months in [3, 6, 12]:
        ic = run_window(panel, train_start, valid_start, valid_months=months)
        LOGGER.info("valid=%d months: OOS IC = %.4f", months, ic)


if __name__ == "__main__":
    main()
