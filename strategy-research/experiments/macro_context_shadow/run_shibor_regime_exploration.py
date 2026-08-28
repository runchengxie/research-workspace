"""Run the first Shibor regime exploration against published workspace assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.dataset as ds

from .shibor_regime import build_shibor_regimes


def _forward_return(series: pd.Series, horizon: int) -> pd.Series:
    future = series.shift(-1)
    return (
        (1.0 + future.iloc[::-1])
        .rolling(horizon, min_periods=horizon)
        .apply(lambda values: values.prod() - 1.0, raw=True)
        .iloc[::-1]
    )


def summarize_market_by_regime(
    market: pd.DataFrame, regimes: pd.DataFrame, *, horizon: int = 20
) -> dict[str, Any]:
    """Join the latest visible regime and summarize equal-weight market returns."""

    required = {"trade_date", "ew_daily_return", "stocks"}
    missing = required.difference(market.columns)
    if missing:
        raise ValueError(f"market frame missing columns: {', '.join(sorted(missing))}")
    frame = market.copy().sort_values("trade_date")
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], utc=True)
    context = regimes.sort_values("period_end")
    frame = pd.merge_asof(
        frame,
        context,
        left_on="trade_date",
        right_on="period_end",
        direction="backward",
    )
    frame[f"fwd_{horizon}d"] = _forward_return(frame["ew_daily_return"], horizon)
    groups: dict[str, Any] = {}
    for name, group in frame.dropna(subset=["regime"]).groupby("regime", sort=True):
        groups[str(name)] = {
            "observations": len(group),
            "mean_forward_return": float(group[f"fwd_{horizon}d"].mean()),
            "mean_daily_return": float(group["ew_daily_return"].mean()),
            "strict_pit_observations": int(
                group["strict_pit"].astype("boolean").fillna(False).sum()
            ),
        }
    return {"horizon": horizon, "groups": groups}


def load_market_daily(data_root: Path, contract: Any) -> pd.DataFrame:
    asset = contract.asset("daily_clean")
    path = asset.resolve_data_path("data")
    table = ds.dataset(str(path), format="parquet").to_table(
        columns=["trade_date", "pct_chg", "is_suspended"]
    )
    frame = table.to_pandas()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], utc=True)
    frame = frame.loc[~frame["is_suspended"].fillna(False) & frame["pct_chg"].notna()]
    return frame.groupby("trade_date", as_index=False).agg(
        ew_daily_return=("pct_chg", lambda value: float(value.mean()) / 100.0),
        stocks=("pct_chg", "size"),
    )


def run(data_root: str | Path, *, as_of: str, output: str | Path | None = None) -> dict[str, Any]:
    from market_data_platform.published_assets import PublishedAssetContract

    root = Path(data_root).expanduser().resolve()
    a_share = PublishedAssetContract.load_current(root, market="a_share")
    context = PublishedAssetContract.load_current(root, market="cn_context")
    pit_asset = context.asset("context_pit")
    pit = pd.read_parquet(pit_asset.resolve_data_path("data.parquet"))
    cutoff = pd.Timestamp(as_of, tz="UTC")
    regimes = build_shibor_regimes(pit, cutoff)
    market = load_market_daily(root, a_share)
    result: dict[str, Any] = {
        "experiment_id": "shibor_regime_exploration_v1",
        "as_of": cutoff.isoformat(),
        "contract_hashes": {
            "a_share": a_share.contract_sha256,
            "cn_context": context.contract_sha256,
        },
        "context_rows": len(pit),
        "regime_rows": len(regimes),
        "strict_pit_regime_rows": int(regimes["strict_pit"].sum()),
        "summary": summarize_market_by_regime(market, regimes),
        "evidence_status": "exploratory_only",
        "limitations": [
            "historical Shibor rows may be reconstructed",
            "this is equal-weight market conditioning, not stock-level alpha attribution",
            "no production eligibility",
        ],
    }
    if output is not None:
        Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    print(
        json.dumps(
            run(args.data_root, as_of=args.as_of, output=args.output),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
