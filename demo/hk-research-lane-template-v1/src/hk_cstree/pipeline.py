from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

TARGET_CONTRACT = "quant-execution-engine.targets/v2"


def _broker_symbol(symbol: str) -> str:
    text = str(symbol).strip().upper()
    if text.endswith(".HK"):
        text = text[:-3]
    return text.lstrip("0") or "0"


def _build_signals(prices: pd.DataFrame) -> pd.DataFrame:
    work = prices.copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce")
    work.sort_values(["symbol", "trade_date"], inplace=True)
    work["return_1d"] = work.groupby("symbol")["close"].pct_change()
    latest_date = work["trade_date"].max()
    latest = work[work["trade_date"] == latest_date].copy()
    latest["raw_pred"] = latest["return_1d"].fillna(0.0) + latest["market_cap"].rank(pct=True) * 0.001
    latest["signal_eval"] = latest["raw_pred"]
    latest["signal_backtest"] = latest["raw_pred"]
    latest["rank"] = latest["signal_backtest"].rank(ascending=False, method="first").astype(int)
    latest["signal_date"] = latest["trade_date"].dt.strftime("%Y%m%d")
    latest["model_version"] = "synthetic_hk_template:v1"
    latest["feature_set_id"] = "synthetic_return_market_cap:v1"
    latest["eligible_for_backtest"] = True
    latest["eligible_for_live"] = False
    return latest[
        [
            "signal_date",
            "symbol",
            "raw_pred",
            "signal_eval",
            "signal_backtest",
            "rank",
            "model_version",
            "feature_set_id",
            "eligible_for_backtest",
            "eligible_for_live",
            "close",
            "amount",
            "market_cap",
        ]
    ].reset_index(drop=True)


def _build_positions(signals: pd.DataFrame, top_n: int) -> pd.DataFrame:
    selected = signals.sort_values(["rank", "symbol"]).head(top_n).copy()
    if selected.empty:
        return pd.DataFrame(columns=["symbol", "weight", "rank", "signal", "side"])
    selected["weight"] = 1.0 / len(selected)
    selected["signal"] = selected["signal_backtest"]
    selected["side"] = "long"
    return selected[["symbol", "weight", "rank", "signal", "side"]].reset_index(drop=True)


def _build_targets(positions: pd.DataFrame, *, asof: str) -> dict[str, Any]:
    return {
        "asof": asof,
        "source": "hk-cross-sectional-research-template",
        "target_gross_exposure": 1.0,
        "targets": [
            {
                "symbol": _broker_symbol(row["symbol"]),
                "market": "HK",
                "target_weight": float(row["weight"]),
            }
            for _, row in positions.iterrows()
        ],
    }


def run_smoke(
    prices_path: str | Path,
    out_dir: str | Path,
    *,
    top_n: int = 2,
) -> dict[str, Any]:
    prices = pd.read_csv(prices_path)
    signals = _build_signals(prices)
    positions = _build_positions(signals, top_n=top_n)
    asof = str(signals["signal_date"].max())
    targets = _build_targets(positions, asof=asof)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    signals_path = out / "signals.csv"
    positions_path = out / "positions_current.csv"
    targets_path = out / "targets.json"
    summary_path = out / "summary.json"
    signals.to_csv(signals_path, index=False)
    positions.to_csv(positions_path, index=False)
    targets_path.write_text(json.dumps(targets, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "market": "HK",
        "synthetic_only": True,
        "signal_rows": int(len(signals)),
        "position_rows": int(len(positions)),
        "target_contract": TARGET_CONTRACT,
        "signals_file": str(signals_path),
        "positions_file": str(positions_path),
        "targets_file": str(targets_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "summary_path": summary_path,
        "signals_path": signals_path,
        "positions_path": positions_path,
        "targets_path": targets_path,
        "summary": summary,
    }
