"""qlib vs 自研 XGB 公平对比。

在**同一份真实 A 股面板**上，用**同一模型参数**、**同一 IC 口径**，
分别用 qlib XGBModel 和自研 XGBRegressor（alpha-research 同族）训练并评估，
量化两套训练管线的结果差异，回答"qlib 替代自研训练/评估层是否可行"。

对比口径：
- 数据：同一批股票、同一时间窗、同一特征、同一 label
- 模型参数：alpha-research xgb_regressor 默认（300/3/0.05/0.8/0.8）
- IC：每日横截面 Spearman IC 均值（daily_ic_series 口径）

运行：
    uv run python compare_qlib_vs_own.py
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
LOGGER = logging.getLogger("qlib_compare")

ROOT = Path(__file__).resolve().parent
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
    """每日横截面 Spearman IC，取均值 + rank IC（与 alpha_research.metrics 同口径）。"""
    from scipy.stats import spearmanr

    ics: list[float] = []
    rics: list[float] = []
    for _, group in df.groupby("trade_date"):
        if group[target_col].nunique() < 2:
            continue
        sub = group[[pred_col, target_col]].dropna()
        if len(sub) < 2 or sub[target_col].nunique() < 2:
            continue
        ic, _ = spearmanr(sub[pred_col], sub[target_col])
        if not np.isnan(ic):
            ics.append(ic)
            rics.append(ic)
    if not ics:
        return {"n": 0, "mean_ic": np.nan, "mean_rank_ic": np.nan}
    return {
        "n": len(ics),
        "mean_ic": float(np.mean(ics)),
        "mean_rank_ic": float(np.mean(rics)),
    }


def run_own_xgb(panel: pd.DataFrame, *, standardize: bool = False) -> dict[str, float]:
    """自研 XGBRegressor 训练 + 自研 daily IC 口径。

    standardize=True 时手动复刻 qlib 的 RobustZScoreNorm + Fillna 预处理，
    用于隔离"训练管线 vs 预处理"对 IC 的贡献。
    """
    from xgboost import XGBRegressor

    train = panel[panel["trade_date"] <= pd.Timestamp(TRAIN_END)].copy()
    valid = panel[panel["trade_date"] > pd.Timestamp(TRAIN_END)].copy()

    if standardize:
        # 复刻 qlib RobustZScoreNorm：按日对特征做中位数中心化 + MAD 缩放的近似
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

        train = _cs_norm(train)
        valid = _cs_norm(valid)
        # 特征标准化不影响 label；训练仍需丢弃 label 缺失的行
        train = train.dropna(subset=["LABEL"])
        valid = valid.dropna(subset=["LABEL"])
    else:
        train = train.dropna(subset=FEATURES + ["LABEL"])
        valid = valid.dropna(subset=FEATURES + ["LABEL"])

    model = XGBRegressor(**XGB_PARAMS)
    model.fit(train[FEATURES], train["LABEL"])
    valid = valid.copy()
    valid["PRED"] = model.predict(valid[FEATURES])
    return daily_ic_mean(valid, "PRED")


def run_qlib_xgb(panel: pd.DataFrame) -> dict[str, float]:
    """qlib XGBModel 训练，然后用同一面板算 daily IC（统一口径）。"""
    import qlib
    from qlib.config import REG_CN
    from qlib.data.dataset import DatasetH
    from qlib.data.dataset.handler import DataHandlerLP
    from qlib.data.dataset.loader import QlibDataLoader
    from qlib.utils import init_instance_by_config

    import shutil
    import subprocess

    csv_dir = ROOT / "data" / "compare_csv"
    bucket = ROOT / "qlib_compare_bucket"
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
    instruments = qlib.data.D.instruments(market="all")

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

    # 统一口径：把 qlib 预测和原始 label 对齐后，用同一 daily IC 函数
    label_df = dataset.prepare("valid", col_set="__all", data_key=DataHandlerLP.DK_L)
    label = label_df["LABEL"] if "LABEL" in label_df.columns else None
    if label is None:
        # 从原始面板对齐
        valid_panel = panel[panel["trade_date"] > pd.Timestamp(TRAIN_END)].copy()
        valid_panel["PRED"] = np.nan
        return daily_ic_mean(valid_panel, "PRED")

    merged = pd.concat([pred.rename("PRED"), label], axis=1, join="inner").dropna()
    merged = merged.reset_index()
    # 合并日期列（label_df 的 index 第一层是 datetime）
    if "datetime" in merged.columns:
        merged["trade_date"] = pd.to_datetime(merged["datetime"])
    elif isinstance(merged.index, pd.MultiIndex):
        merged["trade_date"] = pd.to_datetime(merged.index.get_level_values(0))
    else:
        merged["trade_date"] = pd.to_datetime(merged.index)
    return daily_ic_mean(merged, "PRED")


def main() -> None:
    t0 = time.time()
    panel = load_panel()
    LOGGER.info("panel: %d rows, %d symbols", len(panel), panel["ts_code"].nunique())

    t1 = time.time()
    own = run_own_xgb(panel, standardize=False)
    t2 = time.time()
    LOGGER.info("own XGB (raw): %s (%.1fs)", own, t2 - t1)

    own_std = run_own_xgb(panel, standardize=True)
    t2b = time.time()
    LOGGER.info("own XGB (standardized): %s (%.1fs)", own_std, t2b - t2)

    qlib_result = run_qlib_xgb(panel)
    t3 = time.time()
    LOGGER.info("qlib XGB: %s (%.1fs)", qlib_result, t3 - t2b)

    LOGGER.info("== comparison ==")
    LOGGER.info(
        "IC diff: own_raw=%.4f own_std=%.4f qlib=%.4f",
        own["mean_ic"],
        own_std["mean_ic"],
        qlib_result["mean_ic"],
    )
    LOGGER.info(
        "RankIC diff: own_raw=%.4f own_std=%.4f qlib=%.4f",
        own["mean_rank_ic"],
        own_std["mean_rank_ic"],
        qlib_result["mean_rank_ic"],
    )
    LOGGER.info("total: %.1fs", time.time() - t0)


if __name__ == "__main__":
    main()
