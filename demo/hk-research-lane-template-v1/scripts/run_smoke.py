from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hk_cstree import run_smoke  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the synthetic HK research smoke workflow.")
    parser.add_argument("--prices", default="fixtures/synthetic_hk_prices.csv")
    parser.add_argument("--out-dir", default="samples")
    parser.add_argument("--top-n", type=int, default=2)
    args = parser.parse_args()
    result = run_smoke(ROOT / args.prices, ROOT / args.out_dir, top_n=args.top_n)
    print(result["summary_path"])
    print(result["targets_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
