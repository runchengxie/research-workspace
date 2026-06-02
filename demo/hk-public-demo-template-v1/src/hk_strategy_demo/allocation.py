from __future__ import annotations

from .research import Score


def select_top(scores: list[Score], top_n: int) -> list[Score]:
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    return scores[: min(top_n, len(scores))]


def build_targets(selected: list[Score], *, asof: str) -> dict[str, object]:
    if not selected:
        raise ValueError("selected scores must not be empty")
    weight = 1.0 / len(selected)
    return {
        "source": "hk-cross-sectional-strategy-demo",
        "asof": asof,
        "target_gross_exposure": 1.0,
        "targets": [
            {
                "symbol": row.symbol.removesuffix(".HK"),
                "market": "HK",
                "target_weight": weight,
            }
            for row in selected
        ],
    }
