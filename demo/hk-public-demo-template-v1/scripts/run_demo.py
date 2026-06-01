from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hk_strategy_demo.pipeline import run_demo  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prices", default="fixtures/synthetic_prices.csv")
    parser.add_argument("--out-dir", default="samples")
    parser.add_argument("--top-n", type=int, default=2)
    args = parser.parse_args()
    result = run_demo(
        ROOT / args.prices,
        ROOT / args.out_dir,
        top_n=args.top_n,
    )
    print(result["summary_path"])
    print(result["targets_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
