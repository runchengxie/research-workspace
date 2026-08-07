"""alpha-research NativeTrainerBackend vs QlibTrainerBackend 差分报告。

在**同一真实 A 股面板**、**同一 TrainerFitRequest**（同模型参数、同特征、同目标）、
**同一 IC 口径**下，对比原生训练后端与 Qlib 训练后端的训练预测、特征重要性、耗时。

这是 ADR-0005 验收标准中"与原生基线形成可复验差异报告"的一部分。

运行：
    uv run python diff_native_vs_qlib.py
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("qlib_diff")

ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT.parents[1]
DATA_SOURCE = Path(
    os.environ.get(
        "A_SHARE_DAILY_DIR",
        "/home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data",
    )
)

START_DATE = "2023-01-01"
TRAIN_END = "2024-06-30"
END_DATE = "2024-12-31"
LABEL_HORIZON = 5
FEATURES = ["pct_chg", "turnover_rate", "pe_ttm", "pb", "vol", "amount"]
LIMIT_SYMBOLS: int | None = 200

# 与 alpha-research xgb_regressor 默认参数一致
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
        df = df[(df["trade_date"] >= pd.Timestamp(START_DATE)) & (df["trade_date"] <= pd.Timestamp(END_DATE))]
        if df.empty:
            continue
        frames.append(df[["trade_date", "ts_code"] + FEATURES + ["LABEL"]])
    return pd.concat(frames, ignore_index=True)


def daily_ic_mean(df: pd.DataFrame, pred_col: str, target_col: str = "LABEL") -> dict[str, float]:
    from scipy.stats import spearmanr

    ics: list[float] = []
    for _, group in df.groupby("trade_date"):
        sub = group[[pred_col, target_col]].dropna()
        if len(sub) < 2 or sub[target_col].nunique() < 2:
            continue
        ic, _ = spearmanr(sub[pred_col], sub[target_col])
        if not np.isnan(ic):
            ics.append(ic)
    if not ics:
        return {"n": 0, "mean_ic": np.nan}
    return {"n": len(ics), "mean_ic": float(np.mean(ics))}


def run_backend(backend, panel: pd.DataFrame, label: str) -> dict[str, float]:
    """用给定 backend 训练（train 段）并对 valid 段预测，返回 IC。"""
    from alpha_research.backends import TrainerFitRequest

    train_df = panel[panel["trade_date"] <= pd.Timestamp(TRAIN_END)].dropna(subset=FEATURES + ["LABEL"])
    valid_df = panel[panel["trade_date"] > pd.Timestamp(TRAIN_END)].copy()
    valid_df = valid_df.dropna(subset=FEATURES)

    request = TrainerFitRequest(
        frame=train_df,
        model_type="xgb_regressor",
        model_params=dict(XGB_PARAMS),
        features=tuple(FEATURES),
        target_col="LABEL",
        date_col="trade_date",
    )

    t0 = time.time()
    handle = backend.fit(request)
    fit_time = time.time() - t0

    t1 = time.time()
    pred = backend.predict(handle, valid_df, features=tuple(FEATURES))
    pred_time = time.time() - t1

    valid = valid_df.copy()
    valid["PRED"] = pred.to_numpy()
    ic = daily_ic_mean(valid, "PRED")
    ic["fit_s"] = round(fit_time, 2)
    ic["predict_s"] = round(pred_time, 2)

    try:
        importance = backend.feature_importance(handle, features=tuple(FEATURES))
        top_features = importance.frame.head(3)["feature"].tolist()
        ic["top_features"] = top_features
    except Exception as exc:  # noqa: BLE001
        ic["top_features"] = f"unavailable: {type(exc).__name__}"

    LOGGER.info("%s: %s", label, ic)
    return ic


def main() -> None:
    sys.path.insert(0, str(WORKSPACE_ROOT / "alpha-research" / "src"))
    sys.path.insert(0, str(WORKSPACE_ROOT / "market-data-platform" / "src"))

    from alpha_research.backends import NativeTrainerBackend, QlibTrainerBackend

    panel = load_panel()
    LOGGER.info("panel: %d rows, %d symbols", len(panel), panel["ts_code"].nunique())

    native = run_backend(NativeTrainerBackend(), panel, "native")
    qlib_backend = run_backend(QlibTrainerBackend(), panel, "qlib")

    LOGGER.info("== differential summary ==")
    ic_diff = qlib_backend["mean_ic"] - native["mean_ic"]
    LOGGER.info(
        "IC: native=%.4f qlib=%.4f delta=%.4f",
        native["mean_ic"],
        qlib_backend["mean_ic"],
        ic_diff,
    )
    LOGGER.info("fit: native=%.1fs qlib=%.1fs", native["fit_s"], qlib_backend["fit_s"])
    LOGGER.info("predict: native=%.1fs qlib=%.1fs", native["predict_s"], qlib_backend["predict_s"])


if __name__ == "__main__":
    main()
