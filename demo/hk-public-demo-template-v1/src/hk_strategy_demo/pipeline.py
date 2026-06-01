from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _load_prices(path: Path) -> dict[str, list[tuple[str, float]]]:
    prices: dict[str, list[tuple[str, float]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            prices[str(row["symbol"])].append(
                (str(row["trade_date"]), float(row["close"]))
            )
    if not prices:
        raise ValueError("synthetic price fixture is empty")
    return {symbol: sorted(rows) for symbol, rows in prices.items()}


def run_demo(prices_path: str | Path, out_dir: str | Path, *, top_n: int = 2) -> dict[str, Any]:
    prices = _load_prices(Path(prices_path))
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    scores = []
    for symbol, rows in prices.items():
        first_close = rows[0][1]
        last_close = rows[-1][1]
        scores.append(
            {
                "symbol": symbol,
                "score": (last_close / first_close) - 1.0,
            }
        )
    ranked = sorted(scores, key=lambda row: (-float(row["score"]), str(row["symbol"])))
    selected = ranked[: min(top_n, len(ranked))]
    weight = 1.0 / len(selected)
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
        "selected": selected,
    }
    targets = {
        "source": "hk-cross-sectional-strategy-demo",
        "asof": asof,
        "target_gross_exposure": 1.0,
        "targets": [
            {
                "symbol": str(row["symbol"]).removesuffix(".HK"),
                "market": "HK",
                "target_weight": weight,
            }
            for row in selected
        ],
    }
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
