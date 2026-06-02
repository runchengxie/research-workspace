from __future__ import annotations

from dataclasses import dataclass

from .data import PriceRows


@dataclass(frozen=True)
class Score:
    symbol: str
    score: float

    def to_json(self) -> dict[str, float | str]:
        return {"symbol": self.symbol, "score": self.score}


def rank_trailing_returns(prices: PriceRows) -> list[Score]:
    scores = []
    for symbol, rows in prices.items():
        first_close = rows[0][1]
        last_close = rows[-1][1]
        scores.append(Score(symbol=symbol, score=(last_close / first_close) - 1.0))
    return sorted(scores, key=lambda row: (-row.score, row.symbol))
