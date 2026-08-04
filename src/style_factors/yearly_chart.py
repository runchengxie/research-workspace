"""Re-render the formal yearly style-factor chart from a sealed CSV artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .charts import YearlyChartArtifacts, plot_yearly_barchart


def render_yearly_chart(input_csv: Path, outdir: Path) -> YearlyChartArtifacts:
    if not input_csv.is_file():
        raise FileNotFoundError(f"逐年因子数据文件不存在：{input_csv}")
    yearly = pd.read_csv(input_csv)
    artifacts = plot_yearly_barchart(yearly, outdir)
    if artifacts is None:
        raise ValueError(f"逐年因子数据为空：{input_csv}")
    return artifacts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从 factor_yearly.csv 生成正式年度风格图")
    parser.add_argument("--input", type=Path, required=True, help="factor_yearly.csv 路径")
    parser.add_argument("--outdir", type=Path, required=True, help="图表输出目录")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    artifacts = render_yearly_chart(args.input.expanduser(), args.outdir.expanduser())
    print(f"年度风格图已生成：{artifacts.png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
