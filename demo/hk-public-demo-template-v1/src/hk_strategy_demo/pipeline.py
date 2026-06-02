from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .allocation import build_targets, select_top
from .data import load_prices
from .research import rank_trailing_returns


def run_demo(prices_path: str | Path, out_dir: str | Path, *, top_n: int = 2) -> dict[str, Any]:
    prices = load_prices(prices_path)
    ranked = rank_trailing_returns(prices)
    selected = select_top(ranked, top_n)
    asof = max(date for rows in prices.values() for date, _close in rows)
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)

    summary = {
        "schema_version": "hk_strategy_demo.summary.v1",
        "status": "passed",
        "market": "hk",
        "data_policy": "synthetic_fixture_only",
        "asof": asof,
        "symbols": len(prices),
        "selected": [row.to_json() for row in selected],
    }
    targets = build_targets(selected, asof=asof)
    summary_path = output / "summary.json"
    targets_path = output / "targets.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    targets_path.write_text(json.dumps(targets, indent=2) + "\n", encoding="utf-8")
    return {
        "summary_path": str(summary_path),
        "targets_path": str(targets_path),
        "summary": summary,
        "targets": targets,
    }
