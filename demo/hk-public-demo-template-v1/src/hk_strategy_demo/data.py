from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

PriceRows = dict[str, list[tuple[str, float]]]


def load_prices(path: str | Path) -> PriceRows:
    prices: defaultdict[str, list[tuple[str, float]]] = defaultdict(list)
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            prices[str(row["symbol"])].append((str(row["trade_date"]), float(row["close"])))
    if not prices:
        raise ValueError("synthetic price fixture is empty")
    return {symbol: sorted(rows) for symbol, rows in prices.items()}
