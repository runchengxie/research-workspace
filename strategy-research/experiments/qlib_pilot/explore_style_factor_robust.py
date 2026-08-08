"""风格因子报告结论落地验证：扩展特征集 + robust 标准化。

背景：风格因子报告指出低换手、价值、短期反转是长期有效的风格，且这些因子
（换手率、估值）含极端值/缺失，是 robust 标准化的主场。

验证假设：
- 在 a_share 纯技术面特征集上，robust 相对 zscore 提升温和（+0.0043）
- 扩展特征集（加入换手率 turnover_rate + 估值 pe_ttm/pb + pct_chg）后，
  robust 的收益应兑现，明显拉开与 zscore 的差距

方法：两个特征集 x 两种标准化（zscore/robust），8 个滚动窗口对比 OOS IC。

运行：
    uv run python explore_style_factor_robust.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("style_robust")

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
TRAIN_MONTHS = 12
VALID_MONTHS = 3
STEP_MONTHS = 3
LABEL_HORIZON = 5
LIMIT_SYMBOLS: int | None = 200

# 特征集 A：a_share 纯技术面（现状）
FEATURES_TECH = [
    "ret_5", "ret_20", "ret_60",
    "rv_20", "rv_60",
    "log_vol", "vol",
    "volume_sma5_ratio", "volume_sma20_ratio", "volume_sma60_ratio",
    "amount_log",
]
# 特征集 B：A + 低换手/价值/反转因子（报告指出的长期有效风格）
FEATURES_EXTENDED = FEATURES_TECH + [
    "turnover_rate", "pe_ttm", "pb", "pct_chg",
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
    if LIMIT_SYMBOLS is not None:
        files = files[:LIMIT_SYMBOLS]
    frames = []
    for f in files:
        df = pd.read_parquet(f)
        if "trade_date" not in df.columns or "adj_close" not in df.columns:
            continue
        df = df.copy()
        df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
        df = compute_features(df)
        df = df.set_index("trade_date")
        df["LABEL"] = df["adj_close"].shift(-LABEL_HORIZON) / df["adj_close"] - 1
        df = df.reset_index()
        df = df[(df["trade_date"] >= pd.Timestamp(DATA_START)) & (df["trade_date"] <= pd.Timestamp(DATA_END))]
        if df.empty:
            continue
        frames.append(df[["trade_date", "ts_code"] + FEATURES_EXTENDED + ["LABEL"]])
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


def run_window(panel, features, train_start, train_end, valid_start, *, method: str | None) -> float:
    from xgboost import XGBRegressor

    train = panel[(panel["trade_date"] >= train_start) & (panel["trade_date"] < valid_start)].copy()
    valid = panel[(panel["trade_date"] >= valid_start)].copy()
    valid = valid[valid["trade_date"] < valid_start + pd.DateOffset(months=VALID_MONTHS)]

    if method in {"zscore", "robust", "rank"}:
        from alpha_research.transform import apply_cross_sectional_transform

        train = apply_cross_sectional_transform(train, features, method=method, winsorize_pct=0.01)
        valid = apply_cross_sectional_transform(valid, features, method=method, winsorize_pct=0.01)
        train = train.dropna(subset=["LABEL"])
        valid = valid.dropna(subset=["LABEL"])

    train = train.dropna(subset=features + ["LABEL"])
    valid = valid.dropna(subset=features)
    if len(train) < 1000 or len(valid) < 100:
        return np.nan

    model = XGBRegressor(**XGB_PARAMS)
    model.fit(train[features], train["LABEL"])
    valid = valid.copy()
    valid["PRED"] = model.predict(valid[features])
    return daily_ic_mean(valid, "PRED")


def main() -> None:
    sys.path.insert(0, str(WORKSPACE_ROOT / "alpha-research" / "src"))
    panel = load_panel()
    windows = build_windows(panel)
    LOGGER.info("%d rolling windows", len(windows))

    configs = {
        "tech_zscore": (FEATURES_TECH, "zscore"),
        "tech_robust": (FEATURES_TECH, "robust"),
        "extended_zscore": (FEATURES_EXTENDED, "zscore"),
        "extended_robust": (FEATURES_EXTENDED, "robust"),
        "extended_rank": (FEATURES_EXTENDED, "rank"),
    }
    results = {k: [] for k in configs}
    for i, (t_start, t_end, v_start) in enumerate(windows):
        row = {}
        for k, (feats, method) in configs.items():
            ic = run_window(panel, feats, t_start, t_end, v_start, method=method)
            row[k] = ic
            results[k].append(ic)
        LOGGER.info("w%d valid=%s tech_z=%.4f tech_r=%.4f ext_z=%.4f ext_r=%.4f ext_rank=%.4f",
                    i + 1, v_start.date(), row["tech_zscore"], row["tech_robust"],
                    row["extended_zscore"], row["extended_robust"], row["extended_rank"])

    LOGGER.info("== summary ==")
    summary = {}
    for k in configs:
        vals = [v for v in results[k] if not np.isnan(v)]
        summary[k] = (np.mean(vals), np.std(vals)) if vals else (np.nan, np.nan)
        LOGGER.info("%-16s mean_ic=%.4f std=%.4f", k, summary[k][0], summary[k][1])

    LOGGER.info("== key deltas ==")
    LOGGER.info("tech robust-vs-zscore: %+.4f", summary["tech_robust"][0] - summary["tech_zscore"][0])
    LOGGER.info("extended robust-vs-zscore: %+.4f", summary["extended_robust"][0] - summary["extended_zscore"][0])
    LOGGER.info("extended-vs-tech (robust): %+.4f", summary["extended_robust"][0] - summary["tech_robust"][0])
    LOGGER.info("extended-vs-tech (zscore): %+.4f", summary["extended_zscore"][0] - summary["tech_zscore"][0])

    # 命中率：extended_robust vs extended_zscore
    er = [v for v in results["extended_robust"] if not np.isnan(v)]
    ez = [v for v in results["extended_zscore"] if not np.isnan(v)]
    if er and ez and len(er) == len(ez):
        hit = sum(1 for r, z in zip(er, ez) if r > z) / len(er)
        LOGGER.info("extended robust-vs-zscore hit rate: %.1f%%", hit * 100)


if __name__ == "__main__":
    main()
