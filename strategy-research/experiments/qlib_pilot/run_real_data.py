"""qlib 真实数据验证：用真实 A 股日线数据跑通 XGBModel。

验证目标：
1. 真实数据接入成本（5796 只股票，dump_bin 耗时）
2. 真实数据上 XGBModel 训练/评估是否可行
3. 结果可信度（与合成数据的差异）

数据源：~/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/

运行：
    uv run python run_real_data.py
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("qlib_real_pilot")

ROOT = Path(__file__).resolve().parent
DATA_SOURCE = Path(
    os.environ.get(
        "A_SHARE_DAILY_DIR",
        "/home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data",
    )
)
CSV_DIR = ROOT / "data" / "real_csv"
QLIB_DIR = ROOT / "qlib_real_bucket"
MLRUNS_DIR = ROOT / "mlruns"

# 时间窗
START_DATE = "2023-01-01"
END_DATE = "2024-12-31"
# 训练/验证划分
TRAIN_END = "2024-06-30"

# 真实因子（daily_clean_latest 里的可用列）
FEATURES = ["pct_chg", "turnover_rate", "pe_ttm", "pb", "vol", "amount"]
# 标签：未来 5 日收益
LABEL_HORIZON = 5

# 抽样上限，控制验证规模（None = 全量）
LIMIT_SYMBOLS: int | None = 200


def load_real_panel() -> pd.DataFrame:
    """读取真实日线面板，计算未来收益标签，过滤出时间窗。"""
    files = sorted(DATA_SOURCE.glob("*.parquet"))
    LOGGER.info("data source: %s, %d files", DATA_SOURCE, len(files))
    if LIMIT_SYMBOLS is not None:
        files = files[:LIMIT_SYMBOLS]
        LOGGER.info("sampling %d symbols", LIMIT_SYMBOLS)

    frames = []
    t0 = time.time()
    for f in files:
        df = pd.read_parquet(f)
        if "trade_date" not in df.columns or "adj_close" not in df.columns:
            continue
        df = df.copy()
        df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
        df = df.sort_values("trade_date")
        df = df.set_index("trade_date")
        # 未来 LABEL_HORIZON 期收益
        df["LABEL"] = df["adj_close"].shift(-LABEL_HORIZON) / df["adj_close"] - 1
        df = df.reset_index()
        df = df[(df["trade_date"] >= pd.Timestamp(START_DATE)) & (df["trade_date"] <= pd.Timestamp(END_DATE))]
        if df.empty:
            continue
        keep = ["trade_date", "ts_code"] + FEATURES + ["LABEL"]
        df = df[keep]
        frames.append(df)
    panel = pd.concat(frames, ignore_index=True)
    LOGGER.info("real panel loaded: %d rows, %.1fs", len(panel), time.time() - t0)
    return panel


def prepare_csv(panel: pd.DataFrame) -> None:
    """拆成 dump_bin 需要的"每股票一个 csv"。"""
    if CSV_DIR.exists():
        shutil.rmtree(CSV_DIR)
    CSV_DIR.mkdir(parents=True)
    for ts_code, sub in panel.groupby("ts_code"):
        sub = sub.sort_values("trade_date").rename(columns={"ts_code": "symbol", "trade_date": "date"})
        sub["date"] = sub["date"].dt.strftime("%Y-%m-%d")
        sub.to_csv(CSV_DIR / f"{ts_code}.csv", index=False)


def dump_to_qlib() -> None:
    """官方 dump_bin 工具把 csv 转 qlib bucket。"""
    if QLIB_DIR.exists():
        shutil.rmtree(QLIB_DIR)
    fields = ",".join(FEATURES + ["LABEL"])
    cmd = [
        sys.executable,
        str(ROOT / "tools_dump_bin.py"),
        "dump_all",
        "--data_path",
        str(CSV_DIR),
        "--qlib_dir",
        str(QLIB_DIR),
        "--include_fields",
        fields,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        LOGGER.error("dump_bin failed: %s", result.stderr[-2000:])
        raise RuntimeError("dump_bin failed")


def run_experiment() -> None:
    import qlib
    from qlib.config import REG_CN
    from qlib.data import D
    from qlib.data.dataset import DatasetH
    from qlib.data.dataset.handler import DataHandlerLP
    from qlib.data.dataset.loader import QlibDataLoader
    from qlib.utils import init_instance_by_config
    from qlib.workflow import R
    from qlib.workflow.record_temp import SigAnaRecord

    qlib.init(provider_uri=str(QLIB_DIR), region=REG_CN, mlflow_dir=str(MLRUNS_DIR))
    LOGGER.info("qlib initialized")

    instruments = D.instruments(market="all")
    df = D.features(instruments, ["$pct_chg"], start_time=START_DATE, end_time=END_DATE, freq="day")
    LOGGER.info("qlib features read: %s", df.shape)
    assert len(df) > 0, "features empty"

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
        "kwargs": {
            "n_estimators": 200,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "silent": True,
        },
    }
    model = init_instance_by_config(model_conf)
    model.fit(dataset)
    LOGGER.info("XGBModel trained")

    # 用验证集算 IC 和 Rank IC，验证结果可信度
    from scipy.stats import spearmanr

    pred = model.predict(dataset, segment="valid")
    label_df = dataset.prepare("valid", col_set="__all", data_key=DataHandlerLP.DK_L)
    label = label_df["LABEL"] if "LABEL" in label_df.columns else None

    if label is not None:
        merged = pd.concat([pred.rename("PRED"), label], axis=1, join="inner").dropna()
        if len(merged) > 0:
            ic = merged["PRED"].corr(merged["LABEL"])
            ric, _ = spearmanr(merged["PRED"], merged["LABEL"])
            LOGGER.info("== IC metrics (valid) ==")
            LOGGER.info("IC = %.4f, Rank IC = %.4f, n = %d", ic, ric, len(merged))
        else:
            LOGGER.warning("no overlapping valid samples for IC")
    else:
        LOGGER.warning("LABEL column not found in valid data; skipping IC")

    with R.start(experiment_name="qlib_real_pilot"):
        recorder = R.get_recorder()
        SigAnaRecord(recorder, dataset, label_col=1).generate()
        LOGGER.info("Signal analysis done")


def main() -> None:
    t0 = time.time()
    panel = load_real_panel()
    t1 = time.time()
    prepare_csv(panel)
    dump_to_qlib()
    t2 = time.time()
    run_experiment()
    t3 = time.time()
    LOGGER.info("== timing ==")
    LOGGER.info("real panel load: %.1fs", t1 - t0)
    LOGGER.info("panel -> csv -> qlib bucket (dump_bin): %.1fs", t2 - t1)
    LOGGER.info("qlib train+eval: %.1fs", t3 - t2)
    LOGGER.info("total: %.1fs", t3 - t0)


if __name__ == "__main__":
    main()
