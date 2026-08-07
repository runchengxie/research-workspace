"""a_share 生产链路特征集下 zscore vs robust 对比。

用 a_share.yml 预设中能从 daily_clean_latest 计算的特征子集（ret / rv / vol /
volume ratio 等），对比 cross_sectional method zscore 与 robust 的生产效果。
沿用多滚动窗口方法验证提升稳定性。

运行：
    uv run python compare_a_share_cs_methods.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("a_share_cs")

ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parents[1]
DATA_SOURCE = Path(
    os.environ.get(
        "A_SHARE_DAILY_DIR",
        "/home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data",
    )
)

# 贴近 a_share.yml 的滚动设置
DATA_START = "2022-01-01"
DATA_END = "2024-12-31"
TRAIN_MONTHS = 12
VALID_MONTHS = 3
STEP_MONTHS = 3
LABEL_HORIZON = 5
LIMIT_SYMBOLS: int | None = 200

# a_share.yml 中能用 daily_clean_latest 直接算出的特征
FEATURES = [
    "ret_5", "ret_20", "ret_60",
    "rv_20", "rv_60",
    "log_vol", "vol",
    "volume_sma5_ratio", "volume_sma20_ratio", "volume_sma60_ratio",
    "amount_log",
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


def compute_a_share_features(df: pd.DataFrame) -> pd.DataFrame:
    """在单只股票序列上计算 a_share 风格特征。"""
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
    if LIMIT_SYMBOLS is not None:
        files = files[:LIMIT_SYMBOLS]
    frames = []
    for f in files:
        df = pd.read_parquet(f)
        if "trade_date" not in df.columns or "adj_close" not in df.columns:
            continue
        df = df.copy()
        df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
        df = compute_a_share_features(df)
        df = df.set_index("trade_date")
        df["LABEL"] = df["adj_close"].shift(-LABEL_HORIZON) / df["adj_close"] - 1
        df = df.reset_index()
        df = df[(df["trade_date"] >= pd.Timestamp(DATA_START)) & (df["trade_date"] <= pd.Timestamp(DATA_END))]
        if df.empty:
            continue
        frames.append(df[["trade_date", "ts_code"] + FEATURES + ["LABEL"]])
    panel = pd.concat(frames, ignore_index=True)
    LOGGER.info("panel: %d rows, %d symbols", len(panel), panel["ts_code"].nunique())
    return panel


def build_windows(panel: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    dates = pd.to_datetime(panel["trade_date"].unique())
    first = dates.min()
    start_cursor = pd.Timestamp(first.year, first.month, 1)
    end_cursor = pd.Timestamp(pd.Timestamp(DATA_END).year, pd.Timestamp(DATA_END).month, 1)
    windows = []
    cursor = start_cursor + pd.DateOffset(months=TRAIN_MONTHS)
    while cursor <= end_cursor:
        train_start = cursor - pd.DateOffset(months=TRAIN_MONTHS)
        valid_start = cursor
        valid_end = valid_start + pd.DateOffset(months=VALID_MONTHS)
        if valid_end > end_cursor + pd.DateOffset(months=1):
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


def run_window(panel, train_start, train_end, valid_start, *, method: str | None) -> float:
    from xgboost import XGBRegressor

    train = panel[(panel["trade_date"] >= train_start) & (panel["trade_date"] < valid_start)].copy()
    valid = panel[(panel["trade_date"] >= valid_start)].copy()
    valid = valid[valid["trade_date"] < valid_start + pd.DateOffset(months=VALID_MONTHS)]

    if method in {"zscore", "robust", "rank"}:
        from alpha_research.transform import apply_cross_sectional_transform

        train = apply_cross_sectional_transform(train, FEATURES, method=method, winsorize_pct=0.01)
        valid = apply_cross_sectional_transform(valid, FEATURES, method=method, winsorize_pct=0.01)
        train = train.dropna(subset=["LABEL"])
        valid = valid.dropna(subset=["LABEL"])

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
    LOGGER.info("%d rolling windows", len(windows))

    results = {m: [] for m in ["none", "zscore", "robust"]}
    for i, (t_start, t_end, v_start) in enumerate(windows):
        row = {}
        for m in results:
            ic = run_window(panel, t_start, t_end, v_start, method=m if m != "none" else None)
            row[m] = ic
            results[m].append(ic)
        LOGGER.info("w%d valid=%s none=%.4f zscore=%.4f robust=%.4f",
                    i + 1, v_start.date(), row["none"], row["zscore"], row["robust"])

    LOGGER.info("== summary (a_share features) ==")
    for m in results:
        vals = [v for v in results[m] if not np.isnan(v)]
        if vals:
            LOGGER.info("%-8s mean_ic=%.4f std=%.4f", m, np.mean(vals), np.std(vals))
    none_v = [v for v in results["none"] if not np.isnan(v)]
    zscore_v = [v for v in results["zscore"] if not np.isnan(v)]
    robust_v = [v for v in results["robust"] if not np.isnan(v)]
    if robust_v and none_v:
        LOGGER.info("robust-vs-none mean delta=%+.4f", np.mean(robust_v) - np.mean(none_v))
    if robust_v and zscore_v:
        hit = sum(1 for r, z in zip(robust_v, zscore_v) if r > z) / len(robust_v)
        LOGGER.info("robust-vs-zscore mean delta=%+.4f hit=%.1f%%",
                    np.mean(robust_v) - np.mean(zscore_v), hit * 100)


if __name__ == "__main__":
    main()
