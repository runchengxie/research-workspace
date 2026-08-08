"""qlib 极速验证：用自己的数据跑通 XGBModel 训练与评估。

验证目标：数据接入成本（面板 -> qlib bucket）和首次跑通 XGBModel 耗时。
数据接入走官方 dump_bin 工具，即真实使用路径。

运行：
    uv run python run_pilot.py

输出：打印各阶段耗时，并将结果写入 RESULTS.md。
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

# qlib 用 MLflow 文件存储后端记录实验，新版本 mlflow 需要显式允许
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("qlib_pilot")

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
CSV_DIR = DATA_DIR / "csv"
QLIB_DIR = ROOT / "qlib_bucket"
N_INSTRUMENTS = 20
N_DAYS = 400
FEATURES = 6
START_DATE = "2021-01-01"
END_DATE = "2022-06-30"


def build_sample_data() -> None:
    """构造一份小样例数据，模拟横截面日频面板。"""
    DATA_DIR.mkdir(exist_ok=True)
    dates = pd.bdate_range(START_DATE, periods=N_DAYS)
    instruments = [f"SH{i:06d}" for i in range(N_INSTRUMENTS)]

    rows = []
    rng = np.random.default_rng(42)
    for inst in instruments:
        factor1 = rng.standard_normal(N_DAYS)
        factor2 = rng.standard_normal(N_DAYS)
        factor3 = rng.standard_normal(N_DAYS)
        factor4 = rng.standard_normal(N_DAYS)
        factor5 = rng.standard_normal(N_DAYS)
        factor6 = rng.standard_normal(N_DAYS)
        # 未来 1 期收益作为标签
        future_ret = 0.1 * factor1 + 0.05 * factor2 + rng.standard_normal(N_DAYS) * 0.01
        rows.append(
            pd.DataFrame(
                {
                    "date": dates,
                    "instrument": inst,
                    "F000001": factor1,
                    "F000002": factor2,
                    "F000003": factor3,
                    "F000004": factor4,
                    "F000005": factor5,
                    "F000006": factor6,
                    "LABEL": future_ret,
                }
            )
        )
    df = pd.concat(rows, ignore_index=True)
    df = df.sort_values(["date", "instrument"]).reset_index(drop=True)
    df.to_parquet(DATA_DIR / "sample_panel.parquet")
    LOGGER.info("sample panel written: %d rows, %d instruments, %d days", len(df), N_INSTRUMENTS, N_DAYS)


def prepare_csv() -> None:
    """把面板拆成 dump_bin 需要的"每股票一个 csv"。"""
    if CSV_DIR.exists():
        shutil.rmtree(CSV_DIR)
    CSV_DIR.mkdir(parents=True)
    df = pd.read_parquet(DATA_DIR / "sample_panel.parquet")
    for inst, sub in df.groupby("instrument"):
        sub = sub.sort_values("date").rename(columns={"instrument": "symbol"})
        sub["date"] = pd.to_datetime(sub["date"])
        sub.to_csv(CSV_DIR / f"{inst}.csv", index=False)


def dump_to_qlib() -> None:
    """用官方 dump_bin 工具把 csv 转成 qlib bucket。"""
    if QLIB_DIR.exists():
        shutil.rmtree(QLIB_DIR)
    fields = ",".join([f"F00000{i}" for i in range(1, FEATURES + 1)] + ["LABEL"])
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
    from qlib.utils import init_instance_by_config
    from qlib.workflow import R

    provider_uri = str(QLIB_DIR)
    qlib.init(provider_uri=provider_uri, region=REG_CN)
    LOGGER.info("qlib initialized with provider_uri=%s", provider_uri)

    instruments = D.instruments(market="all")
    df = D.features(
        instruments,
        ["$F000001"],
        start_time=START_DATE,
        end_time=END_DATE,
        freq="day",
    )
    LOGGER.info("qlib features read: %s", df.shape)
    assert len(df) > 0, "features empty"

    from qlib.data.dataset.loader import QlibDataLoader

    feature_cols = [f"$F00000{i}" for i in range(1, FEATURES + 1)]
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
                    "fit_end_time": END_DATE,
                },
            },
            {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
        ],
        "learn_processors": [
            {"class": "DropnaLabel"},
            {
                "class": "CSZScoreNorm",
                "kwargs": {"fields_group": "label"},
            },
        ],
    }
    handler = DataHandlerLP(**handler_conf)
    dataset = DatasetH(
        handler,
        segments={
            "train": (pd.Timestamp(START_DATE), pd.Timestamp("2021-12-31")),
            "valid": (pd.Timestamp("2022-01-01"), pd.Timestamp(END_DATE)),
        },
    )

    model_conf = {
        "class": "XGBModel",
        "module_path": "qlib.contrib.model.xgboost",
        "kwargs": {
            "n_estimators": 100,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "silent": True,
        },
    }
    model = init_instance_by_config(model_conf)
    model.fit(dataset)
    LOGGER.info("XGBModel trained")

    from qlib.workflow.record_temp import SigAnaRecord

    with R.start(experiment_name="qlib_pilot"):
        recorder = R.get_recorder()
        SigAnaRecord(recorder, dataset, label_col=1).generate()
        LOGGER.info("Signal analysis done")


def main() -> None:
    t0 = time.time()
    build_sample_data()
    t1 = time.time()
    prepare_csv()
    dump_to_qlib()
    t2 = time.time()
    run_experiment()
    t3 = time.time()
    LOGGER.info("== timing ==")
    LOGGER.info("sample data build: %.1fs", t1 - t0)
    LOGGER.info("panel -> csv -> qlib bucket: %.1fs", t2 - t1)
    LOGGER.info("qlib train+eval: %.1fs", t3 - t2)
    LOGGER.info("total: %.1fs", t3 - t0)


if __name__ == "__main__":
    main()
