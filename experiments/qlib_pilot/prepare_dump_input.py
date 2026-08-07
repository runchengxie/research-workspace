"""把样例面板拆成 dump_bin 需要的"每股票一个 csv"输入。

dump_bin 期望 data_path 目录下每个 csv 文件代表一只股票，
文件内包含 date 列和特征列，文件名即 symbol。

用法：
    uv run python prepare_dump_input.py
输出：data/csv/<symbol>.csv
"""

from __future__ import annotations

import pandas as pd

DATA_DIR = "data"
IN = f"{DATA_DIR}/sample_panel.parquet"
OUT = f"{DATA_DIR}/csv"


def main() -> None:
    import os
    from pathlib import Path

    out_dir = Path(OUT)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(IN)
    for inst, sub in df.groupby("instrument"):
        sub = sub.sort_values("date")
        sub = sub.rename(columns={"instrument": "symbol"})
        sub["date"] = pd.to_datetime(sub["date"])
        sub.to_csv(out_dir / f"{inst}.csv", index=False)
    print(f"wrote {len(df['instrument'].unique())} csv files to {OUT}")


if __name__ == "__main__":
    main()
