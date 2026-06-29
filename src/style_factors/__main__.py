"""Style factor analysis CLI — 9-factor Barra long-short backtest + report.

Usage:
    DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform \\
        python -m style_factors --outdir artifacts/style_analysis

    # Strategy attribution:
    python -m style_factors --strategy-csv returns.csv --strategy-name cstree
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .workflow import run_style_factor_analysis


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--data-root",
        default=os.environ.get("DATA_PLATFORM_ROOT", "/home/richard/data/market-data-platform"),
    )
    ap.add_argument("--outdir", default="artifacts/style_analysis")
    ap.add_argument("--quick", action="store_true", help="Sample mode: only 2020-2026")
    ap.add_argument("--strategy-csv", help="Strategy daily return CSV for attribution")
    ap.add_argument("--strategy-name", default="strategy")
    args = ap.parse_args()

    data_root = Path(args.data_root)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("全市场风格因子分析 (9-factor Barra)")
    print(f"数据根: {data_root}")
    print(f"输出:   {outdir}")
    print("=" * 60)

    artifacts = run_style_factor_analysis(
        data_root=data_root,
        outdir=outdir,
        quick=args.quick,
        strategy_csv=Path(args.strategy_csv) if args.strategy_csv else None,
        strategy_name=args.strategy_name,
    )
    print("\n=== 因子表现 ===")
    print(artifacts.summary.to_string(index=False))

    print("\n=== 因子相关性 ===")
    print(artifacts.correlation.to_string())

    if not artifacts.yearly.empty:
        print("\n=== 逐年收益 ===")
        ret_pivot = artifacts.yearly.pivot(index="year", columns="factor", values="annual_ret")
        print(ret_pivot.to_string(float_format=lambda value: f"{value:+.1f}"))
    if artifacts.attribution:
        print(
            "\n[strategy attribution] "
            f"R²={artifacts.attribution['r_squared']}, "
            f"alpha={artifacts.attribution['annual_alpha']}%"
        )

    print(f"\n[OK] 全部产出写入 {outdir}/")
    for f in sorted(outdir.iterdir()):
        print(f"     {f.name}")


if __name__ == "__main__":
    main()
