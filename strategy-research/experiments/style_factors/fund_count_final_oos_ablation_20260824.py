"""Final-OOS ablation for full-market fund-count features.

This is a focused research runner for the four-arm experiment described in
the fund-portfolio investigation. It reuses the project's feature
mathematics, model factory, sample weighting and cross-sectional
normalization, while building the monthly panel once so that the four arms
do not each repeat the expensive per-symbol daily feature pass.

The runner is diagnostic evidence, not a replacement for the canonical
strategy-pipeline artifact writer. It uses:

* the current full-market PIT universe;
* the 20260821 full fund-portfolio asset (not the stale latest alias);
* the latest 20260824 daily-clean asset for technical features and labels;
* monthly next-rebalance labels with one-day entry delay;
* the same 20% date holdout rule as eval.final_oos.size: 0.2;
* XGBRegressor parameters and date-equal weights from a_share.yml.

The last monthly universe date without a complete next-rebalance label is
kept in the raw panel for coverage diagnostics but is excluded from model
dates, matching the modeling dataset's complete-case behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from sklearn.metrics import r2_score

from alpha_research.modeling import build_model, fit_model
from alpha_research.split import build_sample_weight
from alpha_research.transform import apply_cross_sectional_transform


DATA_ROOT = Path(
    os.environ.get("DATA_PLATFORM_ROOT", Path.home() / "data" / "market-data-platform")
).expanduser()
UNIVERSE_FILE = DATA_ROOT / "assets/universe/a_share_all_full_by_date.csv"
DAILY_DIR = (
    DATA_ROOT
    / "assets/tushare/a_share/daily/a_share_all_20150101_20260824_daily_clean/data"
)
FUND_DIR = (
    DATA_ROOT
    / "assets/tushare/a_share/fund_portfolio_features/"
    "a_share_all_fund_portfolio_features_20260821/data"
)
FUND_MANIFEST = FUND_DIR.parent / "manifest.yml"

TECH_FEATURES = [
    "sma_20",
    "sma_60",
    "sma_120",
    "sma_5_diff",
    "sma_10_diff",
    "sma_20_diff",
    "sma_60_diff",
    "sma_120_diff",
    "rsi_7",
    "rsi_14",
    "rsi_21",
    "macd_hist",
    "ret_5",
    "ret_20",
    "ret_60",
    "rv_20",
    "rv_60",
    "volume_sma5_ratio",
    "volume_sma20_ratio",
    "volume_sma60_ratio",
    "log_vol",
    "vol",
]
FUND_FEATURES = [
    "fund_count_holding_stock",
    "fund_count_holding_stock_qoq_change",
]
MODEL_PARAMS = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "max_depth": 3,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
    "objective": "reg:squarederror",
    "random_state": 42,
}
MODEL_TYPE = "xgb_regressor"
OOS_SIZE = 0.2
TOP_K = 5
N_QUANTILES = 5
CROSS_SECTIONAL_WINSORIZE = 0.01
COST_BPS_GRID = (10.0, 20.0, 30.0)

DAILY_COLUMNS = [
    "trade_date",
    "symbol",
    "tr_close",
    "vol",
    "amount",
    "circ_mv",
    "listed_days",
    "is_st",
    "is_suspended",
    "is_limit_up",
    "is_limit_down",
]
FUND_COLUMNS = [
    "trade_date",
    "symbol",
    "available_date",
    "report_period",
    "disclosure_date",
    "fund_count_holding_stock",
    "fund_count_holding_stock_qoq_change",
]


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_date_series(values: pd.Series) -> pd.Series:
    text = values.astype(str).str.strip()
    compact = text.str.replace("-", "", regex=False)
    yyyymmdd = compact.str.fullmatch(r"\d{8}")
    parsed = pd.to_datetime(
        compact.where(yyyymmdd),
        format="%Y%m%d",
        errors="coerce",
    )
    generic = pd.to_datetime(text.where(~yyyymmdd), errors="coerce")
    return parsed.combine_first(generic).dt.normalize()


def _ema_presma(series: pd.Series, length: int) -> pd.Series:
    """Match pandas_ta EMA with presma=True and adjust=False."""
    result = pd.Series(np.nan, index=series.index, dtype=float)
    if len(series) < length:
        return result
    seeded = pd.to_numeric(series, errors="coerce").astype(float).copy()
    seed = float(seeded.iloc[:length].mean())
    seeded.iloc[: length - 1] = np.nan
    seeded.iloc[length - 1] = seed
    return seeded.ewm(span=length, adjust=False).mean()


def _rsi(series: pd.Series, length: int) -> pd.Series:
    delta = pd.to_numeric(series, errors="coerce").diff()
    positive = delta.copy()
    negative = delta.copy()
    positive[positive < 0] = 0.0
    negative[negative > 0] = 0.0
    positive_avg = positive.ewm(alpha=1.0 / length, adjust=False).mean()
    negative_avg = negative.ewm(alpha=1.0 / length, adjust=False).mean()
    denominator = positive_avg + negative_avg.abs()
    return 100.0 * positive_avg / denominator.replace(0.0, np.nan)


def _add_technical_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the a_share.yml technical features to one symbol's daily frame."""
    out = frame.sort_values("trade_date").reset_index(drop=True).copy()
    price = pd.to_numeric(out["tr_close"], errors="coerce")
    volume = pd.to_numeric(out["vol"], errors="coerce")

    for window in (5, 10, 20, 60, 120):
        sma = price.rolling(window=window, min_periods=window).mean()
        if window in (20, 60, 120):
            out[f"sma_{window}"] = sma
        out[f"sma_{window}_diff"] = sma.pct_change(fill_method=None)

    for length in (7, 14, 21):
        out[f"rsi_{length}"] = _rsi(price, length)

    fast, slow, signal_length = (12, 26, 9)
    fast_ema = _ema_presma(price, fast)
    slow_ema = _ema_presma(price, slow)
    macd = fast_ema - slow_ema
    first_valid = macd.first_valid_index()
    signal = pd.Series(np.nan, index=out.index, dtype=float)
    if first_valid is not None:
        signal.loc[first_valid:] = _ema_presma(macd.loc[first_valid:], signal_length)
    out["macd_hist"] = macd - signal

    for window in (5, 20, 60):
        out[f"ret_{window}"] = price.pct_change(window)
    daily_return = price.pct_change().replace([np.inf, -np.inf], np.nan)
    for window in (20, 60):
        out[f"rv_{window}"] = daily_return.rolling(window=window).std(ddof=0)
    for window in (5, 20, 60):
        volume_sma = volume.rolling(window=window, min_periods=window).mean()
        out[f"volume_sma{window}_ratio"] = volume / volume_sma.replace(0.0, np.nan)
    out["log_vol"] = np.log1p(volume.clip(lower=0.0))
    out["vol"] = volume
    return out


def _load_universe() -> tuple[pd.DataFrame, list[pd.Timestamp], dict[pd.Timestamp, set[str]]]:
    universe = pd.read_csv(UNIVERSE_FILE)
    if "selected" in universe.columns:
        universe = universe.loc[universe["selected"].astype(bool)].copy()
    universe["trade_date"] = _parse_date_series(universe["trade_date"])
    universe["symbol"] = universe["symbol"].astype(str).str.strip()
    universe = universe.dropna(subset=["trade_date", "symbol"])
    universe = universe.drop_duplicates(["trade_date", "symbol"])
    universe = universe.sort_values(["trade_date", "symbol"]).reset_index(drop=True)
    model_dates = sorted(pd.Timestamp(x) for x in universe["trade_date"].unique())
    members = {
        pd.Timestamp(date): set(group["symbol"])
        for date, group in universe.groupby("trade_date", sort=True)
    }
    return universe, model_dates, members


def _load_fund_events() -> pd.DataFrame:
    dataset = ds.dataset(str(FUND_DIR), format="parquet", partitioning="hive")
    events = dataset.to_table(columns=FUND_COLUMNS, use_threads=True).to_pandas()
    events["trade_date"] = _parse_date_series(events["trade_date"])
    events["symbol"] = events["symbol"].astype(str).str.strip()
    events = events.dropna(subset=["trade_date", "symbol"])
    events = events.sort_values(["trade_date", "symbol"])
    duplicate_count = int(events.duplicated(["trade_date", "symbol"]).sum())
    events = events.drop_duplicates(["trade_date", "symbol"], keep="last").reset_index(drop=True)
    events.attrs["duplicate_count_before_dedup"] = duplicate_count
    return events


def _symbol_rows(
    path: Path,
    *,
    model_dates: list[pd.Timestamp],
    members: dict[pd.Timestamp, set[str]],
    next_rebalance: dict[pd.Timestamp, pd.Timestamp],
) -> pd.DataFrame:
    frame = pq.read_table(path, columns=DAILY_COLUMNS).to_pandas()
    if frame.empty:
        return pd.DataFrame()
    frame["trade_date"] = _parse_date_series(frame["trade_date"])
    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    frame = (
        frame.dropna(subset=["trade_date", "symbol"])
        .drop_duplicates(["trade_date", "symbol"], keep="last")
        .sort_values("trade_date")
        .reset_index(drop=True)
    )
    if frame.empty:
        return pd.DataFrame()
    symbol = str(frame["symbol"].iloc[0])
    wanted_dates = [date for date in model_dates if symbol in members.get(date, set())]
    if not wanted_dates:
        return pd.DataFrame()

    engineered = _add_technical_features(frame)
    price = pd.to_numeric(engineered["tr_close"], errors="coerce")
    entry_price = price.shift(-1)
    entry_by_date = pd.Series(
        entry_price.to_numpy(dtype=float),
        index=pd.DatetimeIndex(engineered["trade_date"]),
    )

    selected = engineered.loc[engineered["trade_date"].isin(wanted_dates)].copy()
    selected["entry_price"] = selected["trade_date"].map(entry_by_date)
    selected["next_rebalance_date"] = selected["trade_date"].map(next_rebalance)
    selected["exit_price"] = selected["next_rebalance_date"].map(entry_by_date)
    selected["future_return"] = selected["exit_price"] / selected["entry_price"] - 1.0
    selected["is_tradable"] = (
        ~selected["is_suspended"].fillna(False).astype(bool)
        & ~selected["is_limit_up"].fillna(False).astype(bool)
        & ~selected["is_limit_down"].fillna(False).astype(bool)
    )
    keep = [
        "trade_date",
        "symbol",
        "tr_close",
        "entry_price",
        "exit_price",
        "future_return",
        "amount",
        "circ_mv",
        "listed_days",
        "is_st",
        "is_tradable",
        *TECH_FEATURES,
    ]
    return selected[keep].copy()


def _attach_fund_state(panel: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    left = panel.sort_values(["trade_date", "symbol"]).copy()
    source = events.sort_values(["trade_date", "symbol"]).rename(
        columns={"trade_date": "fund_available_date"}
    )
    source_columns = [
        "fund_available_date",
        "symbol",
        "available_date",
        "report_period",
        "disclosure_date",
        "fund_count_holding_stock",
        "fund_count_holding_stock_qoq_change",
    ]
    source = source[source_columns]
    merged = pd.merge_asof(
        left,
        source,
        left_on="trade_date",
        right_on="fund_available_date",
        by="symbol",
        direction="backward",
        allow_exact_matches=True,
    )
    merged["fund_state_observed"] = merged["fund_available_date"].notna()
    merged["fund_state_age_days"] = (
        merged["trade_date"] - merged["fund_available_date"]
    ).dt.days
    return merged.sort_values(["trade_date", "symbol"]).reset_index(drop=True)


def build_panel(*, max_symbols: int | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    _, model_dates, members = _load_universe()
    next_rebalance = dict(zip(model_dates[:-1], model_dates[1:], strict=False))
    universe_symbols = sorted({symbol for group in members.values() for symbol in group})
    files = {path.stem: path for path in DAILY_DIR.glob("*.parquet")}
    selected_symbols = [symbol for symbol in universe_symbols if symbol in files]
    if max_symbols is not None:
        selected_symbols = selected_symbols[: int(max_symbols)]
    missing_symbols = sorted(set(universe_symbols) - set(files))
    events = _load_fund_events()

    frames: list[pd.DataFrame] = []
    started = time.time()
    for index, symbol in enumerate(selected_symbols, start=1):
        rows = _symbol_rows(
            files[symbol],
            model_dates=model_dates,
            members=members,
            next_rebalance=next_rebalance,
        )
        if not rows.empty:
            frames.append(rows)
        if index % 500 == 0:
            elapsed = time.time() - started
            print(
                f"[panel] symbols={index}/{len(selected_symbols)} "
                f"rows={sum(len(item) for item in frames)} elapsed={elapsed:.1f}s",
                flush=True,
            )
    if not frames:
        raise RuntimeError("No monthly panel rows were built.")
    panel = pd.concat(frames, ignore_index=True)
    panel = _attach_fund_state(panel, events)
    panel = panel.sort_values(["trade_date", "symbol"]).reset_index(drop=True)
    metadata = {
        "universe_file": str(UNIVERSE_FILE),
        "universe_sha256": _sha256(UNIVERSE_FILE),
        "daily_dir": str(DAILY_DIR),
        "fund_dir": str(FUND_DIR),
        "fund_manifest": str(FUND_MANIFEST),
        "fund_manifest_sha256": _sha256(FUND_MANIFEST),
        "universe_dates": len(model_dates),
        "universe_start": str(model_dates[0].date()),
        "universe_end": str(model_dates[-1].date()),
        "universe_symbols": len(universe_symbols),
        "daily_symbols_used": len(selected_symbols),
        "missing_daily_symbols": missing_symbols[:50],
        "missing_daily_symbol_count": len(missing_symbols),
        "fund_event_rows": len(events),
        "fund_event_dates": int(events["trade_date"].nunique()),
        "fund_event_start": str(events["trade_date"].min().date()),
        "fund_event_end": str(events["trade_date"].max().date()),
        "fund_event_duplicate_keys_before_dedup": int(
            events.attrs.get("duplicate_count_before_dedup", 0)
        ),
        "daily_asset_as_of": "2026-08-24",
        "fund_asset_as_of": "2026-08-21",
        "panel_rows": len(panel),
        "panel_symbols": int(panel["symbol"].nunique()),
        "panel_dates": int(panel["trade_date"].nunique()),
    }
    return panel, metadata


def _fill_fund_missing(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    out = panel.copy()
    before = {column: int(out[column].isna().sum()) for column in FUND_FEATURES}
    medians: dict[str, float] = {}
    for column in FUND_FEATURES:
        by_date = out.groupby("trade_date")[column].transform("median")
        medians[column] = float(out[column].median()) if out[column].notna().any() else 0.0
        out[column] = out[column].fillna(by_date).fillna(medians[column])
    after = {column: int(out[column].isna().sum()) for column in FUND_FEATURES}
    return out, {
        "missing_before": before,
        "missing_after": after,
        "fill_method": "cross_sectional_median_then_global_median",
        "global_medians": medians,
    }


def _shuffle_fund_columns(panel: pd.DataFrame, seed: int) -> pd.DataFrame:
    out = panel.copy()
    rng = np.random.default_rng(seed)
    for _date, index in out.groupby("trade_date", sort=False).groups.items():
        positions = np.asarray(index)
        for column in FUND_FEATURES:
            values = out.loc[positions, column].to_numpy(copy=True)
            rng.shuffle(values)
            out.loc[positions, column] = values
    return out


def _prepare_model_panel(
    raw_panel: pd.DataFrame,
    *,
    shuffle_fund: bool = False,
    shuffle_seed: int = 20260824,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    filled, fill_meta = _fill_fund_missing(raw_panel)
    if shuffle_fund:
        filled = _shuffle_fund_columns(filled, shuffle_seed)
    # Match alpha_research.modeling_dataset: complete-case filtering happens
    # before cross-sectional winsorization/normalization. Otherwise the
    # transform's NaN -> 0 fallback would create artificial early dates.
    filled = filled.dropna(
        subset=[*TECH_FEATURES, "tr_close", "future_return"]
    ).copy()
    transformed = apply_cross_sectional_transform(
        filled,
        TECH_FEATURES + FUND_FEATURES,
        "robust",
        CROSS_SECTIONAL_WINSORIZE,
    )
    return transformed, {
        "fill": fill_meta,
        "shuffle_fund": shuffle_fund,
        "shuffle_seed": shuffle_seed if shuffle_fund else None,
    }


def _complete_model_dates(panel: pd.DataFrame, features: list[str]) -> list[pd.Timestamp]:
    complete = panel.dropna(subset=[*features, "tr_close", "future_return"])
    return sorted(pd.Timestamp(x) for x in complete["trade_date"].unique())


def _safe_spearman(left: pd.Series, right: pd.Series) -> float:
    if len(left) < 3 or left.nunique(dropna=True) < 2 or right.nunique(dropna=True) < 2:
        return float("nan")
    return float(left.rank(method="average").corr(right.rank(method="average")))


def _max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return float("nan")
    nav = (1.0 + returns.fillna(0.0)).cumprod()
    drawdown = nav / nav.cummax() - 1.0
    return float(drawdown.min())


def _period_metrics(
    scored: pd.DataFrame,
    *,
    oos_dates: list[pd.Timestamp],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    periods: list[dict[str, Any]] = []
    previous_names: set[str] | None = None
    for date in oos_dates:
        group = scored.loc[scored["trade_date"].eq(date)].copy()
        group = group.dropna(subset=["pred", "future_return"])
        if group.empty:
            continue
        group = group.sort_values(["pred", "symbol"], kind="mergesort")
        q_labels = pd.qcut(
            np.arange(len(group)),
            q=N_QUANTILES,
            labels=False,
            duplicates="drop",
        )
        group["_bucket"] = q_labels
        bucket = group.groupby("_bucket", observed=True)["future_return"].mean()
        q1 = float(bucket.iloc[0]) if len(bucket) >= 1 else float("nan")
        q5 = float(bucket.iloc[-1]) if len(bucket) >= 1 else float("nan")
        ic = _safe_spearman(group["pred"], group["future_return"])

        tradable = group.loc[group["is_tradable"]].copy()
        if len(tradable) < TOP_K:
            tradable = group
        selected = tradable.sort_values(["pred", "symbol"], ascending=[False, True]).head(TOP_K)
        names = set(selected["symbol"])
        name_turnover = 1.0 if previous_names is None else (
            1.0 - len(names.intersection(previous_names)) / max(TOP_K, 1)
        )
        previous_names = names
        amount = pd.to_numeric(selected["amount"], errors="coerce")
        capacity_multiple = amount * 1000.0 * 0.05 / (1_000_000.0 / TOP_K)
        periods.append(
            {
                "trade_date": date,
                "n_obs": int(len(group)),
                "n_tradable": int(len(tradable)),
                "rank_ic": ic,
                "q1_return": q1,
                "q5_return": q5,
                "q5_q1": q5 - q1,
                "top5_gross_return": float(selected["future_return"].mean()),
                "top5_positive": float(selected["future_return"].mean() > 0),
                "top5_name_turnover": name_turnover,
                "top5_median_amount_cny": float(amount.median() * 1000.0),
                "top5_min_amount_cny": float(amount.min() * 1000.0),
                "top5_min_capacity_multiple": float(capacity_multiple.min()),
                "top5_symbols": ",".join(sorted(names)),
            }
        )

    detail = pd.DataFrame(periods)
    if detail.empty:
        return detail, {"periods": 0}
    metrics: dict[str, Any] = {
        "periods": int(len(detail)),
        "rank_ic_mean": float(detail["rank_ic"].mean()),
        "rank_ic_median": float(detail["rank_ic"].median()),
        "rank_ic_ir": float(
            detail["rank_ic"].mean() / detail["rank_ic"].std(ddof=1) * math.sqrt(len(detail))
        )
        if detail["rank_ic"].std(ddof=1) > 0
        else float("nan"),
        "rank_ic_positive_ratio": float((detail["rank_ic"] > 0).mean()),
        "q5_q1_mean": float(detail["q5_q1"].mean()),
        "q5_q1_positive_ratio": float((detail["q5_q1"] > 0).mean()),
        "top5_gross_mean": float(detail["top5_gross_return"].mean()),
        "top5_positive_ratio": float(detail["top5_positive"].mean()),
        "top5_name_turnover_mean": float(detail["top5_name_turnover"].mean()),
        "top5_median_amount_cny": float(detail["top5_median_amount_cny"].median()),
        "top5_min_capacity_multiple_p10": float(
            detail["top5_min_capacity_multiple"].quantile(0.10)
        ),
    }
    net_by_cost: dict[str, dict[str, float]] = {}
    for cost_bps in COST_BPS_GRID:
        fee = detail["top5_name_turnover"].copy() * 2.0 * cost_bps / 10000.0
        fee.iloc[0] = cost_bps / 10000.0
        net = detail["top5_gross_return"] - fee
        mean = float(net.mean())
        std = float(net.std(ddof=1))
        total = float((1.0 + net).prod() - 1.0)
        net_by_cost[str(int(cost_bps))] = {
            "mean_period_return": mean,
            "total_return": total,
            "annualized_return": float((1.0 + total) ** (12.0 / len(net)) - 1.0)
            if 1.0 + total > 0
            else float("nan"),
            "annualized_vol": std * math.sqrt(12.0),
            "sharpe": mean / std * math.sqrt(12.0) if std > 0 else float("nan"),
            "max_drawdown": _max_drawdown(net),
            "avg_cost_drag": float(fee.mean()),
        }
        detail[f"net_return_{int(cost_bps)}bp"] = net
    metrics["cost_grid"] = net_by_cost
    return detail, metrics


def run_arm(
    panel: pd.DataFrame,
    *,
    arm: str,
    features: list[str],
    oos_dates: list[pd.Timestamp],
    train_dates: list[pd.Timestamp],
) -> tuple[dict[str, Any], pd.DataFrame]:
    work = panel.dropna(subset=[*features, "tr_close", "future_return"]).copy()
    train = work.loc[work["trade_date"].isin(train_dates)].copy()
    test = work.loc[work["trade_date"].isin(oos_dates)].copy()
    if train.empty or test.empty:
        raise RuntimeError(f"{arm}: empty train/test frame.")
    weights = build_sample_weight(train, "date_equal")
    model = build_model(MODEL_TYPE, MODEL_PARAMS)
    fit_model(
        model,
        MODEL_TYPE,
        train,
        features=features,
        target_col="future_return",
        sample_weight=weights,
    )
    test = test.copy()
    test["pred"] = model.predict(test[features])
    detail, metrics = _period_metrics(test, oos_dates=oos_dates)
    y_true = test["future_return"].to_numpy(dtype=float)
    y_pred = test["pred"].to_numpy(dtype=float)
    metrics.update(
        {
            "arm": arm,
            "feature_count": len(features),
            "features": features,
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "train_dates": len(train_dates),
            "test_dates": len(oos_dates),
            "first_oos_date": str(oos_dates[0].date()) if oos_dates else None,
            "last_oos_date": str(oos_dates[-1].date()) if oos_dates else None,
            "r2": float(r2_score(y_true, y_pred)),
        }
    )
    metrics["completed_period_dates"] = int(len(detail))
    return metrics, detail


def _raw_factor_diagnostics(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for factor in FUND_FEATURES:
        for date, group in panel.groupby("trade_date", sort=True):
            group = group.dropna(subset=[factor, "future_return"]).copy()
            if len(group) < 100:
                continue
            group = group.sort_values([factor, "symbol"], kind="mergesort")
            buckets = pd.qcut(
                np.arange(len(group)),
                q=N_QUANTILES,
                labels=False,
                duplicates="drop",
            )
            grouped = group.assign(_bucket=buckets).groupby(
                "_bucket", observed=True
            )["future_return"].mean()
            rows.append(
                {
                    "factor": factor,
                    "trade_date": date,
                    "n_obs": int(len(group)),
                    "rank_ic": _safe_spearman(group[factor], group["future_return"]),
                    "q5_q1": float(grouped.iloc[-1] - grouped.iloc[0]),
                    "zero_share": float((group[factor].abs() < 1e-12).mean()),
                }
            )
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail
    detail["regime"] = np.select(
        [
            detail["trade_date"].dt.year <= 2019,
            detail["trade_date"].dt.year <= 2023,
        ],
        ["2015-2019", "2020-2023"],
        default="2024-2026",
    )
    return detail


def _summarize_raw_factor_diagnostics(detail: pd.DataFrame) -> pd.DataFrame:
    if detail.empty:
        return detail
    return (
        detail.groupby(["factor", "regime"], as_index=False)
        .agg(
            dates=("trade_date", "nunique"),
            mean_rank_ic=("rank_ic", "mean"),
            median_rank_ic=("rank_ic", "median"),
            q5_q1_mean=("q5_q1", "mean"),
            q5_q1_positive_ratio=("q5_q1", lambda s: float((s > 0).mean())),
            zero_share_mean=("zero_share", "mean"),
        )
        .sort_values(["factor", "regime"])
    )


def _quality_report(raw_panel: pd.DataFrame, metadata: dict[str, Any]) -> dict[str, Any]:
    report = dict(metadata)
    report.update(
        {
            "duplicate_panel_keys": int(
                raw_panel.duplicated(["trade_date", "symbol"]).sum()
            ),
            "raw_fund_missing_share": {
                col: float(raw_panel[col].isna().mean()) for col in FUND_FEATURES
            },
            "raw_fund_observed_share": float(raw_panel["fund_state_observed"].mean()),
            "fund_state_age_days_median": float(raw_panel["fund_state_age_days"].median()),
            "fund_state_age_days_p90": float(raw_panel["fund_state_age_days"].quantile(0.90)),
            "fund_state_age_days_p99": float(raw_panel["fund_state_age_days"].quantile(0.99)),
            "raw_fund_qoq_zero_share": float(
                (
                    raw_panel["fund_count_holding_stock_qoq_change"].fillna(0).abs()
                    < 1e-12
                ).mean()
            ),
            "complete_label_share": float(raw_panel["future_return"].notna().mean()),
            "raw_panel_start": str(raw_panel["trade_date"].min().date()),
            "raw_panel_end": str(raw_panel["trade_date"].max().date()),
        }
    )
    return report


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(pd.Timestamp(value))
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    return value


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_readme(
    outdir: Path,
    *,
    metadata: dict[str, Any],
    quality: dict[str, Any],
    metrics: list[dict[str, Any]],
) -> None:
    lines = [
        "# Fund-count Final OOS ablation",
        "",
        "Diagnostic runner; not canonical promotion evidence.",
        "",
        f"- full-market PIT universe: {metadata['universe_file']}",
        f"- fund asset: {metadata['fund_dir']}",
        f"- fund event range: {metadata['fund_event_start']} ~ {metadata['fund_event_end']}",
        f"- panel: {metadata['panel_rows']:,} rows, {metadata['panel_dates']} dates, "
        f"{metadata['panel_symbols']:,} symbols",
        f"- raw fund observed share: {quality['raw_fund_observed_share']:.3f}",
        f"- qoq zero share: {quality['raw_fund_qoq_zero_share']:.3f}",
        "",
        "Arms:",
        "",
        "- baseline: technical features only",
        "- +fund_count: technical + fund_count_holding_stock",
        "- +fund_count_qoq_change: technical + fund_count_holding_stock_qoq_change",
        "- +both: technical + both fund fields",
        "- +both_placebo: both fund fields shuffled within date",
        "",
        "Cost returns use the same two-sided bps approximation as the project's "
        "turnover diagnostics: initial entry is one side; subsequent rebalance "
        "cost is 2 x bps x name turnover.",
        "",
    ]
    for row in metrics:
        cost10 = row.get("cost_grid", {}).get("10", {})
        lines.append(
            f"- {row['arm']}: IC={row.get('rank_ic_mean'):.4f}, "
            f"Q5-Q1={row.get('q5_q1_mean'):.4%}, "
            f"turnover={row.get('top5_name_turnover_mean'):.2%}, "
            f"10bp Sharpe={cost10.get('sharpe')}"
        )
    (outdir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(tempfile.gettempdir()) / "fund_count_final_oos_ablation_20260824",
    )
    parser.add_argument("--panel-path", type=Path, default=None)
    parser.add_argument("--max-symbols", type=int, default=None)
    parser.add_argument("--skip-placebo", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.panel_path is not None and args.panel_path.exists():
        raw_panel = pd.read_parquet(args.panel_path)
        metadata = {
            "panel_source": str(args.panel_path),
            "universe_file": str(UNIVERSE_FILE),
            "universe_sha256": _sha256(UNIVERSE_FILE),
            "daily_dir": str(DAILY_DIR),
            "fund_dir": str(FUND_DIR),
            "fund_manifest": str(FUND_MANIFEST),
            "fund_manifest_sha256": _sha256(FUND_MANIFEST),
            "fund_event_start": str(raw_panel["fund_available_date"].min().date()),
            "fund_event_end": str(raw_panel["fund_available_date"].max().date()),
            "panel_rows": len(raw_panel),
            "panel_symbols": int(raw_panel["symbol"].nunique()),
            "panel_dates": int(raw_panel["trade_date"].nunique()),
        }
    else:
        raw_panel, metadata = build_panel(max_symbols=args.max_symbols)
        raw_panel.to_parquet(args.output_dir / "raw_panel.parquet", index=False)
    quality = _quality_report(raw_panel, metadata)
    _write_json(quality, args.output_dir / "quality.json")

    transformed, transform_meta = _prepare_model_panel(raw_panel)
    base_complete_dates = _complete_model_dates(transformed, TECH_FEATURES)
    if len(base_complete_dates) < 10:
        raise RuntimeError(f"Too few complete model dates: {len(base_complete_dates)}")
    oos_len = max(1, int(math.floor(len(base_complete_dates) * OOS_SIZE)))
    oos_dates = base_complete_dates[-oos_len:]
    train_dates = base_complete_dates[:-oos_len]
    oos_rows = transformed.loc[transformed["trade_date"].isin(oos_dates)]
    split_meta = {
        "all_complete_model_dates": len(base_complete_dates),
        "all_complete_model_start": str(base_complete_dates[0].date()),
        "all_complete_model_end": str(base_complete_dates[-1].date()),
        "final_oos_size": OOS_SIZE,
        "final_oos_len": oos_len,
        "final_oos_start": str(oos_dates[0].date()),
        "final_oos_end": str(oos_dates[-1].date()),
        "train_dates": len(train_dates),
        "train_end": str(train_dates[-1].date()),
        "oos_dates_with_any_complete_label": int(
            oos_rows.groupby("trade_date")["future_return"].apply(lambda s: s.notna().any()).sum()
        ),
    }

    arm_specs = {
        "baseline": TECH_FEATURES,
        "+fund_count": TECH_FEATURES + ["fund_count_holding_stock"],
        "+fund_count_qoq_change": TECH_FEATURES + [
            "fund_count_holding_stock_qoq_change"
        ],
        "+both": TECH_FEATURES + FUND_FEATURES,
    }
    all_metrics: list[dict[str, Any]] = []
    detail_frames: list[pd.DataFrame] = []
    for arm, features in arm_specs.items():
        print(f"[model] fitting {arm} ({len(features)} features) ...", flush=True)
        metrics, detail = run_arm(
            transformed,
            arm=arm,
            features=features,
            oos_dates=oos_dates,
            train_dates=train_dates,
        )
        all_metrics.append(metrics)
        detail.insert(0, "arm", arm)
        detail_frames.append(detail)

    if not args.skip_placebo:
        placebo_panel, placebo_meta = _prepare_model_panel(
            raw_panel,
            shuffle_fund=True,
            shuffle_seed=20260824,
        )
        print("[model] fitting +both_placebo ...", flush=True)
        placebo_metrics, placebo_detail = run_arm(
            placebo_panel,
            arm="+both_placebo",
            features=TECH_FEATURES + FUND_FEATURES,
            oos_dates=oos_dates,
            train_dates=train_dates,
        )
        placebo_metrics["placebo"] = placebo_meta
        all_metrics.append(placebo_metrics)
        placebo_detail.insert(0, "arm", "+both_placebo")
        detail_frames.append(placebo_detail)

    metrics_frame = pd.DataFrame(
        [
            {
                "arm": row["arm"],
                "feature_count": row["feature_count"],
                "train_rows": row["train_rows"],
                "test_rows": row["test_rows"],
                "completed_periods": row["completed_period_dates"],
                "rank_ic_mean": row["rank_ic_mean"],
                "rank_ic_ir": row["rank_ic_ir"],
                "q5_q1_mean": row["q5_q1_mean"],
                "top5_gross_mean": row["top5_gross_mean"],
                "top5_positive_ratio": row["top5_positive_ratio"],
                "top5_name_turnover_mean": row["top5_name_turnover_mean"],
                "top5_median_amount_cny": row["top5_median_amount_cny"],
                "top5_min_capacity_multiple_p10": row[
                    "top5_min_capacity_multiple_p10"
                ],
                "r2": row["r2"],
                **{
                    f"return_{cost}bp": row["cost_grid"][cost]["total_return"]
                    for cost in ("10", "20", "30")
                },
                **{
                    f"sharpe_{cost}bp": row["cost_grid"][cost]["sharpe"]
                    for cost in ("10", "20", "30")
                },
            }
            for row in all_metrics
        ]
    )
    metrics_frame.to_csv(args.output_dir / "metrics.csv", index=False)
    pd.concat(detail_frames, ignore_index=True).to_csv(
        args.output_dir / "periods.csv", index=False
    )

    raw_detail = _raw_factor_diagnostics(raw_panel)
    raw_summary = _summarize_raw_factor_diagnostics(raw_detail)
    raw_detail.to_csv(args.output_dir / "raw_factor_periods.csv", index=False)
    raw_summary.to_csv(args.output_dir / "raw_factor_regimes.csv", index=False)

    summary = {
        "runner": str(Path(__file__)),
        "model_type": MODEL_TYPE,
        "model_params": MODEL_PARAMS,
        "features": {"technical": TECH_FEATURES, "fund": FUND_FEATURES},
        "transform": transform_meta,
        "split": split_meta,
        "quality": quality,
        "metrics": all_metrics,
        "raw_factor_regimes": raw_summary.to_dict(orient="records"),
        "outputs": {
            "metrics": str(args.output_dir / "metrics.csv"),
            "periods": str(args.output_dir / "periods.csv"),
            "raw_factor_regimes": str(args.output_dir / "raw_factor_regimes.csv"),
        },
    }
    _write_json(summary, args.output_dir / "summary.json")
    _write_readme(
        args.output_dir,
        metadata=metadata,
        quality=quality,
        metrics=all_metrics,
    )
    print(f"[done] outputs={args.output_dir}", flush=True)
    print(metrics_frame.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
