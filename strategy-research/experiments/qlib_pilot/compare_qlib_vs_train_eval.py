"""qlib 完整管线 vs 自研 train_eval 生产训练路径对打。

在**同一份真实 A 股面板**、**同一模型参数**、**同一 IC 口径**下，
对比：
- arm 1 自研：alpha_research.fit_model_and_score_train（xgb_regressor + 样本权重 + 后处理）
- arm 2 qlib：qlib XGBModel 完整管线（RobustZScoreNorm + Fillna + CSZScoreNorm）

两者都在同一 train 段训练、同一 valid 段评估，用 daily_ic_mean 算 IC。

运行：
    uv run python compare_qlib_vs_train_eval.py
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("qlib_vs_traineval")

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


def run_train_eval_arm(panel: pd.DataFrame, *, standardize: bool = False) -> dict[str, float]:
    """自研生产训练路径：fit_model_and_score_train + 对 valid 预测。

    standardize=True 时先对特征做横截面标准化（复刻 qlib RobustZScoreNorm 近似），
    用于隔离"训练路径 vs 预处理"的贡献。
    """
    # alpha_research 依赖 market_data_platform 的 canonicalize_symbol_columns
    for sub in ("alpha-research", "market-data-platform"):
        sys.path.insert(0, str(WORKSPACE_ROOT / sub / "src"))
    from alpha_research.backends import NativeTrainerBackend
    from alpha_research.train_eval_contracts import (
        TrainEvalFeatureTarget,
        TrainEvalModelSettings,
        TrainEvalSignalSettings,
    )
    from alpha_research.train_eval_fit import fit_model_and_score_train

    train_df = panel[panel["trade_date"] <= pd.Timestamp(TRAIN_END)].copy()
    valid_df = panel[panel["trade_date"] > pd.Timestamp(TRAIN_END)].copy()

    if standardize:
        def _cs_norm(df: pd.DataFrame) -> pd.DataFrame:
            out = df.copy()
            for feat in FEATURES:
                g = df.groupby("trade_date")[feat]
                med = g.transform("median")
                mad = g.transform(lambda s: (s - s.median()).abs().median())
                mad = mad.replace(0, np.nan)
                out[feat] = (df[feat] - med) / mad
            out[FEATURES] = out[FEATURES].fillna(0)
            return out

        train_df = _cs_norm(train_df)
        valid_df = _cs_norm(valid_df)

    # xgboost 不接受 label 含 NaN；特征 NaN 由 xgboost 自行处理
    train_df = train_df.dropna(subset=["LABEL"])
    valid_df = valid_df.dropna(subset=["LABEL"])

    # 用 train_df 里的真实目标列构造特征目标
    feature_target = TrainEvalFeatureTarget(
        features=FEATURES,
        target="LABEL",
        train_target="LABEL",
        price_col="adj_close",
        fundamentals_mcap_col="circ_mv",
    )
    model_settings = TrainEvalModelSettings(
        model_type="xgb_regressor",
        model_params=dict(XGB_PARAMS),
        model_cfg={"type": "xgb_regressor", "params": dict(XGB_PARAMS)},
        sample_weight_mode="date_equal",
        sample_weight_params={},
        n_splits=3,
        embargo_steps=0,
        purge_steps=0,
        cv_purge_mode="none",
        train_window_mode="all",
        train_window_size=None,
        train_window_unit=None,
    )
    signal_settings = TrainEvalSignalSettings(
        signal_direction_mode="auto",
        signal_direction=1.0,
        min_abs_ic_to_flip=0.0,
        score_postprocess_method="none",
        score_postprocess_columns=None,
        score_postprocess_strength=1.0,
        score_postprocess_min_obs=None,
        report_train_ic=True,
    )

    result = fit_model_and_score_train(
        train_df,
        feature_target=feature_target,
        model_settings=model_settings,
        signal_settings=signal_settings,
        cv_scores_raw=[],
        trainer_backend=NativeTrainerBackend(),
    )
    model = result.model

    # 对 valid 段预测，统一 IC 口径
    valid = valid_df.copy()
    valid = valid.dropna(subset=FEATURES)
    valid["PRED"] = model.predict(valid[FEATURES])
    return daily_ic_mean(valid, "PRED")


def run_qlib_arm(panel: pd.DataFrame) -> dict[str, float]:
    """qlib 完整管线。"""
    import shutil
    import subprocess

    import qlib
    from qlib.config import REG_CN
    from qlib.data import D
    from qlib.data.dataset import DatasetH
    from qlib.data.dataset.handler import DataHandlerLP
    from qlib.data.dataset.loader import QlibDataLoader
    from qlib.utils import init_instance_by_config

    csv_dir = ROOT / "data" / "traineval_csv"
    bucket = ROOT / "qlib_traineval_bucket"
    if csv_dir.exists():
        shutil.rmtree(csv_dir)
    if bucket.exists():
        shutil.rmtree(bucket)
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
    t0 = time.time()
    panel = load_panel()
    LOGGER.info("panel: %d rows, %d symbols", len(panel), panel["ts_code"].nunique())

    t1 = time.time()
    own = run_train_eval_arm(panel, standardize=False)
    t2 = time.time()
    LOGGER.info("train_eval arm (raw): %s (%.1fs)", own, t2 - t1)

    own_std = run_train_eval_arm(panel, standardize=True)
    t2b = time.time()
    LOGGER.info("train_eval arm (standardized): %s (%.1fs)", own_std, t2b - t2)

    qlib_result = run_qlib_arm(panel)
    t3 = time.time()
    LOGGER.info("qlib arm: %s (%.1fs)", qlib_result, t3 - t2b)

    LOGGER.info("== comparison ==")
    LOGGER.info(
        "IC: train_eval_raw=%.4f train_eval_std=%.4f qlib=%.4f",
        own["mean_ic"],
        own_std["mean_ic"],
        qlib_result["mean_ic"],
    )
    LOGGER.info("total: %.1fs", time.time() - t0)


if __name__ == "__main__":
    main()
