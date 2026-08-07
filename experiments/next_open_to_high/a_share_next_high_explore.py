#!/usr/bin/env python3
"""Lightweight A-share next-high exploration.

This is intentionally outside the main strategy pipeline. It reads the local
TuShare clean daily panel, builds a compact feature set around size, turnover,
volume and daily candle pressure, trains a small XGBoost regressor, then writes
bucket diagnostics for size and turnover.

Example:
    uv run python scripts/research/a_share_next_high_explore.py \
        --start-date 2024-01-01 --train-end 2025-12-31 --top-k 10,20,30
"""

# ruff: noqa: SIM905

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

DATA_ROOT = Path(os.environ.get("DATA_PLATFORM_ROOT", "/home/richard/data/market-data-platform"))
DEFAULT_DAILY_DIR = DATA_ROOT / "assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data"
DEFAULT_OUT_BASE = Path("artifacts/reports")

RAW_COLUMNS: list[str] = list(
    """
trade_date symbol open high low close pre_close pct_chg vol amount adj_open adj_high adj_low
adj_close tr_close turnover_rate turnover_rate_f volume_ratio total_mv circ_mv up_limit
down_limit is_limit_up is_limit_down is_suspended is_st listed_days board
""".split()
)

BASE_FEATURES: list[str] = list(
    """
log_mcap log_circ_mcap turnover_rate turnover_rate_f amount_log volume_ratio
mcap_turnover_interaction small_high_turnover ret_1 ret_5 ret_20 rv_20 amount_ratio_5
amount_ratio_20 turnover_ratio_5 turnover_ratio_20 turnover_z20 amount_z20 daily_range
upper_shadow lower_shadow body_return close_pos gap_open signed_amount_pressure
pressure_balance_5 down_amount_share_5
""".split()
)

KEY_FACTOR_COLUMNS: list[str] = list(
    """
cs_log_mcap small_score cs_turnover_rate cs_mcap_turnover_interaction
cs_small_high_turnover cs_amount_log cs_amount_ratio_20 cs_upper_shadow cs_lower_shadow
cs_close_pos cs_pressure_balance_5
""".split()
)


@dataclass(frozen=True)
class RunConfig:
    daily_dir: str
    outdir: str
    start_date: str
    end_date: str | None
    train_end: str
    target: str
    max_symbols: int
    train_sample_per_date: int
    top_k: list[int]
    participation_rate: float
    random_state: int


def _compact_date(value: str | None) -> str | None:
    if value is None:
        return None
    return cast(pd.Timestamp, pd.Timestamp(value)).strftime("%Y%m%d")


def _float_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return _float_or_none(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return str(value)


def _parse_top_k(text: str) -> list[int]:
    values = sorted({int(part.strip()) for part in text.split(",") if part.strip()})
    if not values or min(values) <= 0:
        raise argparse.ArgumentTypeError("--top-k must contain positive integers")
    return values


def _daily_files(daily_dir: Path, max_symbols: int) -> list[Path]:
    files = sorted(daily_dir.glob("*.parquet"))
    if max_symbols > 0:
        files = files[:max_symbols]
    if not files:
        raise FileNotFoundError(f"No symbol parquet files found under {daily_dir}")
    return files


def load_daily_clean(
    daily_dir: Path,
    *,
    start_date: str,
    end_date: str | None,
    max_symbols: int,
) -> pd.DataFrame:
    start = _compact_date(start_date)
    end = _compact_date(end_date)
    parts: list[pd.DataFrame] = []
    files = _daily_files(daily_dir, max_symbols)
    print(f"[load] files={len(files):,} dir={daily_dir}")
    for idx, path in enumerate(files, start=1):
        frame = pd.read_parquet(path, columns=RAW_COLUMNS)
        date_text = frame["trade_date"].astype(str)
        mask = date_text.ge(start)
        if end is not None:
            mask &= date_text.le(end)
        frame = frame.loc[mask].copy()
        if frame.empty:
            continue
        frame["trade_date"] = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d")
        parts.append(frame)
        if idx % 500 == 0:
            print(f"[load] {idx:,}/{len(files):,} files, rows={sum(len(p) for p in parts):,}")
    if not parts:
        raise ValueError("No rows loaded for requested date range")
    data = pd.concat(parts, ignore_index=True)
    data["symbol"] = data["symbol"].astype(str)
    data = data.drop_duplicates(["trade_date", "symbol"], keep="last")
    data = data.sort_values(["symbol", "trade_date"]).reset_index(drop=True)
    print(
        "[load] rows={:,} symbols={:,} dates={}..{}".format(
            len(data),
            data["symbol"].nunique(),
            data["trade_date"].min().date(),
            data["trade_date"].max().date(),
        )
    )
    return data


def _rolling_by_symbol(df: pd.DataFrame, column: str, window: int, min_periods: int) -> pd.Series:
    return df.groupby("symbol", sort=False)[column].transform(
        lambda values: values.rolling(window, min_periods=min_periods).mean()
    )


def _rolling_std_by_symbol(
    df: pd.DataFrame, column: str, window: int, min_periods: int
) -> pd.Series:
    return df.groupby("symbol", sort=False)[column].transform(
        lambda values: values.rolling(window, min_periods=min_periods).std(ddof=0)
    )


def _safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    clean_denominator = denominator.where(denominator.notna() & denominator.ne(0))
    return numerator / clean_denominator


def add_labels_and_features(data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy()
    for column in RAW_COLUMNS:
        if column not in {"trade_date", "symbol", "board"}:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    grouped = df.groupby("symbol", sort=False)
    for column in ("adj_open", "adj_high", "adj_low", "adj_close", "open", "high", "low", "close"):
        df[f"next_{column}"] = grouped[column].shift(-1)

    df["next_high_return"] = _safe_div(df["next_adj_high"], df["adj_close"]) - 1.0
    df["next_open_to_high"] = _safe_div(df["next_adj_high"], df["next_adj_open"]) - 1.0
    df["next_open_to_close"] = _safe_div(df["next_adj_close"], df["next_adj_open"]) - 1.0
    df["next_close_return"] = _safe_div(df["next_adj_close"], df["adj_close"]) - 1.0

    df["ret_1"] = grouped["adj_close"].pct_change()
    df["ret_5"] = grouped["adj_close"].pct_change(5)
    df["ret_20"] = grouped["adj_close"].pct_change(20)
    df["rv_20"] = _rolling_std_by_symbol(df, "ret_1", 20, 10)

    amount_ma5 = _rolling_by_symbol(df, "amount", 5, 3)
    amount_ma20 = _rolling_by_symbol(df, "amount", 20, 10)
    turnover_ma5 = _rolling_by_symbol(df, "turnover_rate", 5, 3)
    turnover_ma20 = _rolling_by_symbol(df, "turnover_rate", 20, 10)
    turnover_std20 = _rolling_std_by_symbol(df, "turnover_rate", 20, 10)
    amount_std20 = _rolling_std_by_symbol(df, "amount", 20, 10)

    df["adv20_amount"] = amount_ma20
    df["adv20_cny"] = amount_ma20 * 1000.0
    df["amount_ratio_5"] = _safe_div(df["amount"], amount_ma5)
    df["amount_ratio_20"] = _safe_div(df["amount"], amount_ma20)
    df["turnover_ratio_5"] = _safe_div(df["turnover_rate"], turnover_ma5)
    df["turnover_ratio_20"] = _safe_div(df["turnover_rate"], turnover_ma20)
    df["turnover_z20"] = _safe_div(df["turnover_rate"] - turnover_ma20, turnover_std20)
    df["amount_z20"] = _safe_div(df["amount"] - amount_ma20, amount_std20)

    price_base = df["pre_close"].where(df["pre_close"].gt(0), df["close"])
    high_low = (df["high"] - df["low"]).replace(0, np.nan)
    df["daily_range"] = _safe_div(df["high"] - df["low"], price_base)
    df["upper_shadow"] = _safe_div(df["high"] - df[["open", "close"]].max(axis=1), price_base)
    df["lower_shadow"] = _safe_div(df[["open", "close"]].min(axis=1) - df["low"], price_base)
    df["body_return"] = _safe_div(df["close"], df["open"]) - 1.0
    df["close_pos"] = _safe_div(df["close"] - df["low"], high_low)
    df["gap_open"] = _safe_div(df["open"], df["pre_close"]) - 1.0

    df["log_mcap"] = np.log1p(df["total_mv"].clip(lower=0))
    df["log_circ_mcap"] = np.log1p(df["circ_mv"].clip(lower=0))
    df["amount_log"] = np.log1p(df["amount"].clip(lower=0))
    df["mcap_turnover_interaction"] = df["log_mcap"] * df["turnover_rate"]
    df["small_high_turnover"] = -df["log_mcap"] * df["turnover_rate"]

    signed_amount = np.sign(df["pct_chg"].fillna(0.0)) * df["amount"].fillna(0.0)
    down_amount = df["amount"].where(df["pct_chg"].lt(0), 0.0)
    df["_signed_amount"] = signed_amount
    df["_down_amount"] = down_amount
    signed_sum5 = _rolling_by_symbol(df, "_signed_amount", 5, 3)
    down_sum5 = _rolling_by_symbol(df, "_down_amount", 5, 3)
    amount_sum5 = df.groupby("symbol", sort=False)["amount"].transform(
        lambda values: values.rolling(5, min_periods=3).sum()
    )
    df["signed_amount_pressure"] = (df["pct_chg"] / 100.0) * df["amount_log"]
    df["pressure_balance_5"] = _safe_div(signed_sum5, amount_sum5)
    df["down_amount_share_5"] = _safe_div(down_sum5, amount_sum5)
    df = df.drop(columns=["_signed_amount", "_down_amount"])

    return add_cross_sectional_features(df)


def add_cross_sectional_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    by_date = out.groupby("trade_date", sort=False)
    for column in BASE_FEATURES:
        rank = by_date[column].rank(method="average", pct=True)
        out[f"cs_{column}"] = rank - 0.5
    out["small_score"] = -out["cs_log_mcap"]
    out["size_bucket"] = pd.cut(
        by_date["log_mcap"].rank(method="average", pct=True),
        bins=[0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0],
        labels=["small", "mid", "large"],
        include_lowest=True,
    )
    out["turnover_bucket"] = pd.cut(
        by_date["turnover_rate"].rank(method="average", pct=True),
        bins=[0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0],
        labels=["low_turnover", "mid_turnover", "high_turnover"],
        include_lowest=True,
    )
    return out


def filter_research_rows(df: pd.DataFrame, target: str) -> pd.DataFrame:
    tradable = (
        df["amount"].gt(0)
        & df["total_mv"].gt(0)
        & df["turnover_rate"].gt(0)
        & ~df["is_suspended"].fillna(False).astype(bool)
        & ~df["is_st"].fillna(False).astype(bool)
        & df["listed_days"].fillna(0).ge(60)
    )
    required = [target, "next_open_to_high", "next_open_to_close", "adv20_amount"]
    out = df.loc[tradable].copy()
    out = out.replace([np.inf, -np.inf], np.nan)
    return out.dropna(subset=required)


def sample_train_rows(
    train: pd.DataFrame,
    *,
    per_date: int,
    random_state: int,
) -> pd.DataFrame:
    if per_date <= 0:
        return train
    parts = [
        group.sample(n=min(len(group), per_date), random_state=random_state)
        for _, group in train.groupby("trade_date", sort=False)
    ]
    return pd.concat(parts, ignore_index=True) if parts else train.iloc[0:0].copy()


def date_equal_weights(frame: pd.DataFrame) -> np.ndarray:
    counts = frame.groupby("trade_date", sort=False)["symbol"].transform("size").to_numpy()
    weights = 1.0 / np.maximum(counts.astype(float), 1.0)
    return weights * (len(weights) / weights.sum())


def fit_model(
    train: pd.DataFrame,
    features: list[str],
    target: str,
    *,
    random_state: int,
) -> XGBRegressor:
    model = XGBRegressor(
        n_estimators=160,
        max_depth=3,
        learning_rate=0.045,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.0,
        reg_lambda=2.0,
        objective="reg:squarederror",
        tree_method="hist",
        n_jobs=max(1, min(os.cpu_count() or 1, 8)),
        random_state=random_state,
    )
    x_train = train[features].fillna(0.0).astype("float32")
    y_train = train[target].astype("float32")
    model.fit(x_train, y_train, sample_weight=date_equal_weights(train))
    return model


def _daily_corr_rows(
    frame: pd.DataFrame,
    score_col: str,
    target_col: str,
    *,
    min_obs: int = 20,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for date, group in frame.groupby("trade_date", sort=False):
        valid = group[[score_col, target_col]].dropna()
        if len(valid) < min_obs:
            continue
        rows.append(
            {
                "trade_date": date,
                "obs": len(valid),
                "pearson_ic": valid[score_col].corr(valid[target_col], method="pearson"),
                "rank_ic": valid[score_col].corr(valid[target_col], method="spearman"),
            }
        )
    return pd.DataFrame(rows)


def _summarize_ic(rows: pd.DataFrame, prefix: str = "") -> dict[str, Any]:
    if rows.empty:
        return {
            f"{prefix}days": 0,
            f"{prefix}rank_ic_mean": None,
            f"{prefix}rank_ic_ir": None,
            f"{prefix}pearson_ic_mean": None,
        }
    rank = rows["rank_ic"].dropna()
    pearson = rows["pearson_ic"].dropna()
    return {
        f"{prefix}days": int(rows["trade_date"].nunique()),
        f"{prefix}rank_ic_mean": _float_or_none(rank.mean()),
        f"{prefix}rank_ic_ir": (
            _float_or_none(rank.mean() / rank.std(ddof=0)) if len(rank) > 1 else None
        ),
        f"{prefix}pearson_ic_mean": _float_or_none(pearson.mean()),
    }


def factor_ic_summary(
    frame: pd.DataFrame,
    columns: list[str],
    target_col: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for column in columns:
        if column not in frame.columns:
            continue
        daily = _daily_corr_rows(frame, column, target_col)
        summary = _summarize_ic(daily)
        rows.append({"factor": column, **summary})
    return pd.DataFrame(rows).sort_values("rank_ic_mean", ascending=False, na_position="last")


def bucket_ic(frame: pd.DataFrame, target_col: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    specs = [
        ("size_bucket", ["size_bucket"]),
        ("turnover_bucket", ["turnover_bucket"]),
        ("size_x_turnover", ["size_bucket", "turnover_bucket"]),
    ]
    for bucket_name, group_cols in specs:
        for bucket_values, group in frame.groupby(group_cols, observed=True, sort=False):
            if not isinstance(bucket_values, tuple):
                bucket_values = (bucket_values,)
            daily = _daily_corr_rows(group, "pred", target_col, min_obs=10)
            summary = _summarize_ic(daily)
            row: dict[str, Any] = {"bucket_type": bucket_name}
            row.update(
                {col: str(value) for col, value in zip(group_cols, bucket_values, strict=True)}
            )
            row.update(summary)
            row["rows"] = len(group)
            rows.append(row)
    return pd.DataFrame(rows)


def evaluate_topk(
    frame: pd.DataFrame,
    target_col: str,
    *,
    top_k_values: list[int],
    participation_rate: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    daily_rows: list[dict[str, Any]] = []
    selected_parts: list[pd.DataFrame] = []
    prev_by_k: dict[int, set[str]] = {}
    for date, group in frame.groupby("trade_date", sort=False):
        ranked = group.sort_values("pred", ascending=False)
        for top_k in top_k_values:
            selected = ranked.head(top_k).copy()
            tickers = set(selected["symbol"].astype(str))
            prev = prev_by_k.get(top_k, set())
            overlap = len(tickers & prev) if prev else 0
            turnover = 1.0 - overlap / max(len(tickers), 1) if prev else 1.0
            prev_by_k[top_k] = tickers
            selected["top_k"] = top_k
            selected_parts.append(selected)
            daily_rows.append(
                {
                    "trade_date": date,
                    "top_k": top_k,
                    "names": len(selected),
                    "turnover": turnover,
                    "target_mean": selected[target_col].mean(),
                    "next_high_mean": selected["next_high_return"].mean(),
                    "next_open_to_high_mean": selected["next_open_to_high"].mean(),
                    "next_open_to_close_mean": selected["next_open_to_close"].mean(),
                    "hit_2pct": selected["next_high_return"].ge(0.02).mean(),
                    "hit_3pct": selected["next_high_return"].ge(0.03).mean(),
                    "hit_5pct": selected["next_high_return"].ge(0.05).mean(),
                    "median_adv20_cny": selected["adv20_cny"].median(),
                    "p25_adv20_cny": selected["adv20_cny"].quantile(0.25),
                    "capacity_cny_at_participation": selected["adv20_cny"].sum()
                    * participation_rate,
                }
            )
    topk_daily = pd.DataFrame(daily_rows)
    selected_all = (
        pd.concat(selected_parts, ignore_index=True) if selected_parts else pd.DataFrame()
    )
    topk_summary = (
        topk_daily.groupby("top_k", sort=True)
        .agg(
            days=("trade_date", "nunique"),
            avg_names=("names", "mean"),
            avg_turnover=("turnover", "mean"),
            target_mean=("target_mean", "mean"),
            next_high_mean=("next_high_mean", "mean"),
            next_open_to_high_mean=("next_open_to_high_mean", "mean"),
            next_open_to_close_mean=("next_open_to_close_mean", "mean"),
            hit_2pct=("hit_2pct", "mean"),
            hit_3pct=("hit_3pct", "mean"),
            hit_5pct=("hit_5pct", "mean"),
            median_adv20_cny=("median_adv20_cny", "median"),
            p25_adv20_cny=("p25_adv20_cny", "median"),
            capacity_cny_at_participation=("capacity_cny_at_participation", "median"),
        )
        .reset_index()
    )
    return topk_daily, topk_summary, selected_all


def selected_bucket_mix(selected: pd.DataFrame, target_col: str) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame()
    rows = []
    for keys, group in selected.groupby(
        ["top_k", "size_bucket", "turnover_bucket"], observed=True, sort=False
    ):
        top_k, size_bucket, turnover_bucket = cast(tuple[Any, Any, Any], keys)
        rows.append(
            {
                "top_k": int(top_k),
                "size_bucket": str(size_bucket),
                "turnover_bucket": str(turnover_bucket),
                "rows": len(group),
                "selection_share": len(group) / max(len(selected[selected["top_k"].eq(top_k)]), 1),
                "target_mean": group[target_col].mean(),
                "next_open_to_close_mean": group["next_open_to_close"].mean(),
                "median_adv20_cny": group["adv20_cny"].median(),
            }
        )
    return pd.DataFrame(rows).sort_values(["top_k", "size_bucket", "turnover_bucket"])


def write_report(
    outdir: Path,
    *,
    config: RunConfig,
    summary: dict[str, Any],
    model_ic: pd.DataFrame,
    factor_ic: pd.DataFrame,
    topk_summary: pd.DataFrame,
    bucket: pd.DataFrame,
    feature_importance: pd.DataFrame,
) -> None:
    def table(frame: pd.DataFrame, *, max_rows: int = 30, index: bool = False) -> str:
        if frame.empty:
            return "No rows."
        shown = frame.head(max_rows)
        return "```text\n" + shown.to_string(index=index) + "\n```"

    lines = [
        "# A-share next-high exploration",
        "",
        "This is a lightweight research probe, not a promoted strategy run.",
        "",
        "## Config",
        "",
        "```json",
        json.dumps(asdict(config), indent=2, ensure_ascii=False),
        "```",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default),
        "```",
        "",
        "## Model IC",
        "",
        table(model_ic.describe(), index=True) if not model_ic.empty else "No model IC rows.",
        "",
        "## Top-k summary",
        "",
        table(topk_summary, index=False) if not topk_summary.empty else "No top-k rows.",
        "",
        "## Single-factor IC",
        "",
        table(factor_ic, max_rows=20, index=False) if not factor_ic.empty else "No factor IC rows.",
        "",
        "## Bucket IC",
        "",
        table(bucket, index=False) if not bucket.empty else "No bucket rows.",
        "",
        "## Model feature importance",
        "",
        table(feature_importance, max_rows=30, index=False)
        if not feature_importance.empty
        else "No feature importance.",
        "",
        "## Caveats",
        "",
        (
            "- `next_high_return` measures next-day upside from signal close, "
            "not a directly executable close-to-close return."
        ),
        "- Capacity uses 20-day average TuShare `amount` converted from thousand CNY to CNY.",
        (
            "- This probe does not model minute-level target exits, price-limit queueing, "
            "or intraday order priority."
        ),
        (
            "- The train sample is date-balanced and downsampled by default "
            "to keep this local run cheap."
        ),
        "",
    ]
    (outdir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _resolve_outdir(args: argparse.Namespace) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.outdir or DEFAULT_OUT_BASE / f"a_share_next_high_explore_{timestamp}")
    outdir = outdir.expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


def _build_run_config(args: argparse.Namespace, daily_dir: Path, outdir: Path) -> RunConfig:
    config = RunConfig(
        daily_dir=str(daily_dir),
        outdir=str(outdir),
        start_date=args.start_date,
        end_date=args.end_date,
        train_end=args.train_end,
        target=args.target,
        max_symbols=int(args.max_symbols),
        train_sample_per_date=int(args.train_sample_per_date),
        top_k=args.top_k,
        participation_rate=float(args.participation_rate),
        random_state=int(args.random_state),
    )
    (outdir / "config.json").write_text(
        json.dumps(asdict(config), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return config


def _load_research_panel(
    args: argparse.Namespace,
    daily_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = load_daily_clean(
        daily_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        max_symbols=int(args.max_symbols),
    )
    panel = filter_research_rows(add_labels_and_features(raw), args.target)
    return raw, panel


def _split_panel(
    panel: pd.DataFrame,
    args: argparse.Namespace,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_end = pd.Timestamp(args.train_end)
    train = panel[panel["trade_date"].le(train_end)].copy()
    test = panel[panel["trade_date"].gt(train_end)].copy()
    if train.empty or test.empty:
        raise ValueError("Train or test split is empty; adjust --start-date/--train-end/--end-date")

    train_sample = sample_train_rows(
        train,
        per_date=int(args.train_sample_per_date),
        random_state=int(args.random_state),
    )
    print(
        "[split] train_rows={:,} sampled={:,} test_rows={:,} train_dates={} test_dates={}".format(
            len(train),
            len(train_sample),
            len(test),
            train["trade_date"].nunique(),
            test["trade_date"].nunique(),
        )
    )
    return train, train_sample, test


def _fit_and_score(
    train_sample: pd.DataFrame,
    test: pd.DataFrame,
    args: argparse.Namespace,
    model_features: list[str],
) -> tuple[Any, pd.DataFrame]:
    model = fit_model(
        train_sample,
        model_features,
        args.target,
        random_state=int(args.random_state),
    )
    test = test.copy()
    test["pred"] = model.predict(test[model_features].fillna(0.0).astype("float32"))
    return model, test


def _write_outputs(
    outdir: Path,
    *,
    config: RunConfig,
    raw: pd.DataFrame,
    panel: pd.DataFrame,
    train: pd.DataFrame,
    train_sample: pd.DataFrame,
    test: pd.DataFrame,
    model: Any,
    model_features: list[str],
    args: argparse.Namespace,
) -> None:
    model_ic = _daily_corr_rows(test, "pred", args.target)
    factor_ic = factor_ic_summary(test, KEY_FACTOR_COLUMNS, args.target)
    bucket = bucket_ic(test, args.target)
    topk_daily, topk_summary, selected = evaluate_topk(
        test,
        args.target,
        top_k_values=args.top_k,
        participation_rate=float(args.participation_rate),
    )
    mix = selected_bucket_mix(selected, args.target)

    feature_importance = pd.DataFrame(
        {
            "feature": model_features,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "rows_loaded": len(raw),
        "rows_research": len(panel),
        "symbols": int(panel["symbol"].nunique()),
        "date_start": panel["trade_date"].min().date().isoformat(),
        "date_end": panel["trade_date"].max().date().isoformat(),
        "train_rows": len(train),
        "train_sample_rows": len(train_sample),
        "test_rows": len(test),
        "target": args.target,
        **_summarize_ic(model_ic, prefix="model_"),
    }

    raw.head(200).to_parquet(outdir / "raw_sample.parquet", index=False)
    model_ic.to_csv(outdir / "model_daily_ic.csv", index=False)
    factor_ic.to_csv(outdir / "single_factor_ic.csv", index=False)
    bucket.to_csv(outdir / "bucket_ic.csv", index=False)
    topk_daily.to_csv(outdir / "topk_daily.csv", index=False)
    topk_summary.to_csv(outdir / "topk_summary.csv", index=False)
    mix.to_csv(outdir / "selected_bucket_mix.csv", index=False)
    feature_importance.to_csv(outdir / "feature_importance.csv", index=False)
    (outdir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default) + "\n",
        encoding="utf-8",
    )
    write_report(
        outdir,
        config=config,
        summary=summary,
        model_ic=model_ic,
        factor_ic=factor_ic,
        topk_summary=topk_summary,
        bucket=bucket,
        feature_importance=feature_importance,
    )
    print(f"[done] {outdir}")


def run(args: argparse.Namespace) -> Path:
    daily_dir = Path(args.daily_dir).expanduser().resolve()
    outdir = _resolve_outdir(args)
    config = _build_run_config(args, daily_dir, outdir)
    raw, panel = _load_research_panel(args, daily_dir)
    model_features = [f"cs_{column}" for column in BASE_FEATURES]
    train, train_sample, test = _split_panel(panel, args)
    model, test = _fit_and_score(train_sample, test, args, model_features)
    _write_outputs(
        outdir,
        config=config,
        raw=raw,
        panel=panel,
        train=train,
        train_sample=train_sample,
        test=test,
        model=model,
        model_features=model_features,
        args=args,
    )
    return outdir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-dir", default=str(DEFAULT_DAILY_DIR))
    parser.add_argument("--outdir")
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date")
    parser.add_argument("--train-end", default="2025-12-31")
    parser.add_argument(
        "--target",
        choices=["next_high_return", "next_open_to_high", "next_close_return"],
        default="next_high_return",
    )
    parser.add_argument("--max-symbols", type=int, default=0, help="0 means all symbols")
    parser.add_argument("--train-sample-per-date", type=int, default=900)
    parser.add_argument("--top-k", type=_parse_top_k, default=_parse_top_k("10,20,30"))
    parser.add_argument("--participation-rate", type=float, default=0.05)
    parser.add_argument("--random-state", type=int, default=42)
    return parser


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
