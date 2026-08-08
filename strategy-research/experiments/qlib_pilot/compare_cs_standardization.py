"""自研横截面标准化 vs qlib RobustZScoreNorm 效果对比。

A 方案验证：alpha-research 原生训练链路里加上横截面标准化，能否复现 qlib
预处理管线的 IC 提升。对比三个 arm：

1. native 原始特征（baseline）
2. native + apply_cross_sectional_transform(method=zscore)
3. qlib RobustZScoreNorm 完整管线

同一真实面板、同一模型参数、同一 IC 口径。

运行：
    uv run python compare_cs_standardization.py
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
LOGGER = logging.getLogger("cs_compare")

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


def train_predict(panel: pd.DataFrame, *, standardize: str | None) -> dict[str, float]:
    """原生 XGBRegressor，可选应用自研横截面标准化。"""
    from xgboost import XGBRegressor

    train_df = panel[panel["trade_date"] <= pd.Timestamp(TRAIN_END)].copy()
    valid_df = panel[panel["trade_date"] > pd.Timestamp(TRAIN_END)].copy()

    if standardize in {"zscore", "robust"}:
        from alpha_research.transform import apply_cross_sectional_transform

        train_df = apply_cross_sectional_transform(
            train_df, FEATURES, method=standardize, winsorize_pct=None
        )
        valid_df = apply_cross_sectional_transform(
            valid_df, FEATURES, method=standardize, winsorize_pct=None
        )
        train_df = train_df.dropna(subset=["LABEL"])
        valid_df = valid_df.dropna(subset=["LABEL"])

    train = train_df.dropna(subset=FEATURES + ["LABEL"])
    valid = valid_df.dropna(subset=FEATURES)

    model = XGBRegressor(**XGB_PARAMS)
    t0 = time.time()
    model.fit(train[FEATURES], train["LABEL"])
    fit_s = time.time() - t0

    valid = valid.copy()
    valid["PRED"] = model.predict(valid[FEATURES])
    ic = daily_ic_mean(valid, "PRED")
    ic["fit_s"] = round(fit_s, 2)
    return ic


def run_qlib_pipeline(panel: pd.DataFrame) -> dict[str, float]:
    """qlib RobustZScoreNorm 完整管线（对照）。"""
    import shutil
    import subprocess

    import qlib
    from qlib.config import REG_CN
    from qlib.data import D
    from qlib.data.dataset import DatasetH
    from qlib.data.dataset.handler import DataHandlerLP
    from qlib.data.dataset.loader import QlibDataLoader
    from qlib.utils import init_instance_by_config

    csv_dir = ROOT / "data" / "cs_csv"
    bucket = ROOT / "qlib_cs_bucket"
    for d in (csv_dir, bucket):
        if d.exists():
            shutil.rmtree(d)
    csv_dir.mkdir(parents=True)

    for ts_code, sub in panel.groupby("ts_code"):
        sub = sub.sort_values("trade_date").rename(columns={"ts_code": "symbol", "trade_date": "date"})
        sub["date"] = sub["date"].dt.strftime("%Y-%m-%d")
        sub.to_csv(csv_dir / f"{ts_code}.csv", index=False)

    fields = ",".join(FEATURES + ["LABEL"])
    cmd = [
        sys.executable,
        str(ROOT / "tools_dump_bin.py"),
        "dump_all",
        "--data_path",
        str(csv_dir),
        "--qlib_dir",
        str(bucket),
        "--include_fields",
        fields,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"dump_bin failed: {r.stderr[-2000:]}")

    qlib.init(provider_uri=str(bucket), region=REG_CN, mlflow_dir=str(ROOT / "mlruns"))
    instruments = D.instruments(market="all")
    feature_cols = [f"${f}" for f in FEATURES]
    data_loader = {
        "class": "QlibDataLoader",
        "kwargs": {
            "config": {
                "feature": (feature_cols, feature_cols),
                "label": (["$LABEL"], ["LABEL"]),
            },
            "freq": "day",
        },
    }
    handler_conf = {
        "instruments": instruments,
        "start_time": START_DATE,
        "end_time": END_DATE,
        "data_loader": data_loader,
        "infer_processors": [
            {
                "class": "RobustZScoreNorm",
                "kwargs": {
                    "fields_group": "feature",
                    "clip_outlier": True,
                    "fit_start_time": START_DATE,
                    "fit_end_time": TRAIN_END,
                },
            },
            {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
        ],
        "learn_processors": [
            {"class": "DropnaLabel"},
            {"class": "CSZScoreNorm", "kwargs": {"fields_group": "label"}},
        ],
    }
    handler = DataHandlerLP(**handler_conf)
    dataset = DatasetH(
        handler,
        segments={
            "train": (pd.Timestamp(START_DATE), pd.Timestamp(TRAIN_END)),
            "valid": (pd.Timestamp("2024-07-01"), pd.Timestamp(END_DATE)),
        },
    )
    model_conf = {
        "class": "XGBModel",
        "module_path": "qlib.contrib.model.xgboost",
        "kwargs": {**XGB_PARAMS, "silent": True},
    }
    model = init_instance_by_config(model_conf)
    model.fit(dataset)
    pred = model.predict(dataset, segment="valid")

    label_df = dataset.prepare("valid", col_set="__all", data_key=DataHandlerLP.DK_L)
    label = label_df["LABEL"] if "LABEL" in label_df.columns else None
    merged = pd.concat([pred.rename("PRED"), label], axis=1, join="inner").dropna()
    merged = merged.reset_index()
    if isinstance(merged.index, pd.MultiIndex):
        merged["trade_date"] = pd.to_datetime(merged.index.get_level_values(0))
    elif "datetime" in merged.columns:
        merged["trade_date"] = pd.to_datetime(merged["datetime"])
    else:
        merged["trade_date"] = pd.to_datetime(merged.index)
    return daily_ic_mean(merged, "PRED")


def main() -> None:
    sys.path.insert(0, str(WORKSPACE_ROOT / "alpha-research" / "src"))
    panel = load_panel()
    LOGGER.info("panel: %d rows, %d symbols", len(panel), panel["ts_code"].nunique())

    baseline = train_predict(panel, standardize=None)
    LOGGER.info("native raw: %s", baseline)

    zscore = train_predict(panel, standardize="zscore")
    LOGGER.info("native zscore: %s", zscore)

    robust = train_predict(panel, standardize="robust")
    LOGGER.info("native robust: %s", robust)

    qlib_result = run_qlib_pipeline(panel)
    LOGGER.info("qlib robust: %s", qlib_result)

    LOGGER.info("== summary ==")
    LOGGER.info("IC: native_raw=%.4f native_zscore=%.4f native_robust=%.4f qlib_robust=%.4f",
                baseline["mean_ic"], zscore["mean_ic"], robust["mean_ic"], qlib_result["mean_ic"])
    LOGGER.info("delta zscore-vs-raw: %.4f", zscore["mean_ic"] - baseline["mean_ic"])
    LOGGER.info("delta robust-vs-raw: %.4f", robust["mean_ic"] - baseline["mean_ic"])
    LOGGER.info("delta qlib-vs-raw: %.4f", qlib_result["mean_ic"] - baseline["mean_ic"])
    LOGGER.info("delta robust-vs-qlib: %.4f", robust["mean_ic"] - qlib_result["mean_ic"])


if __name__ == "__main__":
    main()
