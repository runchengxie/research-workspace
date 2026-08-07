"""robust 标准化的多滚动窗口 OOS 稳健性验证。

验证 A 方案结论是否稳定：用多个滚动（训练->验证）窗口，在每窗口对比
原生 raw 与 robust 标准化的 OOS IC。统计提升的均值、波动和命中率，
判断 +0.0226 是稳定收益还是单窗口巧合。

方法：
- 时间范围 2022-01 至 2024-12，训练窗 12 个月，验证窗 3 个月，步进 3 个月
- 每窗口：训练 XGB（raw 或 robust 特征），对验证窗算每日横截面 IC 均值
- 汇总：每窗口的 raw/robust IC、差值、命中率、均值/标准差

运行：
    uv run python robustness_multi_window.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("robust_robustness")

ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parents[1]
DATA_SOURCE = Path(
    os.environ.get(
        "A_SHARE_DAILY_DIR",
        "/home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data",
    )
)

# 时间范围与滚动窗口
DATA_START = "2022-01-01"
DATA_END = "2024-12-31"
TRAIN_MONTHS = 12
VALID_MONTHS = 3
STEP_MONTHS = 3
LABEL_HORIZON = 5
FEATURES = ["pct_chg", "turnover_rate", "pe_ttm", "pb", "vol", "amount"]
LIMIT_SYMBOLS: int | None = 200

XGB_PARAMS = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "max_depth": 3,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "reg:squarederror",
    "random_state": 42,
}


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
        df = df.sort_values("trade_date").set_index("trade_date")
        df["LABEL"] = df["adj_close"].shift(-LABEL_HORIZON) / df["adj_close"] - 1
        df = df.reset_index()
        df = df[(df["trade_date"] >= pd.Timestamp(DATA_START)) & (df["trade_date"] <= pd.Timestamp(DATA_END))]
        if df.empty:
            continue
        frames.append(df[["trade_date", "ts_code"] + FEATURES + ["LABEL"]])
    return pd.concat(frames, ignore_index=True)


def build_windows(panel: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    """返回 [(train_start, train_end, valid_start), ...] 滚动窗口。"""
    dates = pd.to_datetime(panel["trade_date"].unique())
    first = dates.min()
    # 校准到月初
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


def run_window(panel: pd.DataFrame, train_start, train_end, valid_start, *, standardize: str | None) -> float:
    from xgboost import XGBRegressor

    train = panel[(panel["trade_date"] >= train_start) & (panel["trade_date"] < valid_start)].copy()
    valid = panel[(panel["trade_date"] >= valid_start)].copy()
    # 验证窗为 3 个月
    valid_end = valid_start + pd.DateOffset(months=VALID_MONTHS)
    valid = valid[valid["trade_date"] < valid_end]

    if standardize in {"zscore", "robust"}:
        from alpha_research.transform import apply_cross_sectional_transform

        train = apply_cross_sectional_transform(train, FEATURES, method=standardize, winsorize_pct=None)
        valid = apply_cross_sectional_transform(valid, FEATURES, method=standardize, winsorize_pct=None)
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
    LOGGER.info("panel: %d rows, %d symbols, %s to %s",
                len(panel), panel["ts_code"].nunique(),
                panel["trade_date"].min().date(), panel["trade_date"].max().date())

    windows = build_windows(panel)
    LOGGER.info("%d rolling windows", len(windows))

    rows = []
    for i, (t_start, t_end, v_start) in enumerate(windows):
        raw_ic = run_window(panel, t_start, t_end, v_start, standardize=None)
        robust_ic = run_window(panel, t_start, t_end, v_start, standardize="robust")
        rows.append(
            {
                "window": i + 1,
                "train_end": t_end.date(),
                "valid_start": v_start.date(),
                "raw_ic": raw_ic,
                "robust_ic": robust_ic,
                "delta": robust_ic - raw_ic if (robust_ic is not np.nan and raw_ic is not np.nan) else np.nan,
            }
        )
        LOGGER.info("w%d train_end=%s valid=%s raw=%.4f robust=%.4f delta=%+.4f",
                    i + 1, t_end.date(), v_start.date(), raw_ic, robust_ic,
                    robust_ic - raw_ic if (robust_ic is not np.nan and raw_ic is not np.nan) else np.nan)

    df = pd.DataFrame(rows)
    valid_rows = df.dropna(subset=["raw_ic", "robust_ic"])
    if valid_rows.empty:
        LOGGER.warning("no valid windows")
        return

    LOGGER.info("== robustness summary ==")
    LOGGER.info("valid windows: %d", len(valid_rows))
    LOGGER.info("raw   mean_ic=%.4f std=%.4f", valid_rows["raw_ic"].mean(), valid_rows["raw_ic"].std())
    LOGGER.info("robust mean_ic=%.4f std=%.4f", valid_rows["robust_ic"].mean(), valid_rows["robust_ic"].std())
    LOGGER.info("delta mean=%+.4f std=%.4f", valid_rows["delta"].mean(), valid_rows["delta"].std())
    hit = (valid_rows["delta"] > 0).mean()
    LOGGER.info("hit rate (robust better): %.1f%%", hit * 100)
    LOGGER.info("windows where robust worse: %s",
                valid_rows[valid_rows["delta"] < 0]["valid_start"].astype(str).tolist())
    # 输出到 CSV 供记录
    out_path = ROOT / "data" / "robustness_multi_window.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    LOGGER.info("saved %s", out_path)


if __name__ == "__main__":
    main()
