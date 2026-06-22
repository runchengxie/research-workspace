#!/usr/bin/env python3
# pyright: basic
"""
Path B prototype: Concept-based ETF features → ML ranking → walk-forward backtest.

Replaces rotation-v3's 17 technical features with THS hot-concept-derived
features, then trains a linear rank model with walk-forward to predict
which ETFs will outperform tomorrow.

Usage:
    cd ~/code/research-workspace
    DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform \
    uv run python scripts/concept_etf_ml_backtest.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ── Paths ──
HOT_SCREENER_ROOT = Path(os.environ.get(
    "HOT_SCREENER_ROOT", "/home/richard/code/hot-sector-screener"
))
ROTATION_ROOT = Path(os.environ.get(
    "ETF_ROTATION_ROOT", "/home/richard/code/guan-etf-rotation-v3"
))
DATA_PLATFORM_ROOT = Path(os.environ.get(
    "DATA_PLATFORM_ROOT", "/home/richard/data/market-data-platform"
))

sys.path.insert(0, str(HOT_SCREENER_ROOT / "src"))
sys.path.insert(0, str(ROTATION_ROOT / "src"))

# ── Concept → Exposure dimension mapping (copied from hot-sector-screener) ──

CONCEPT_EXPOSURE_MAP: dict[str, dict[str, float]] = {
    "半导体": {"semiconductor": 1.0, "tech": 0.8},
    "芯片": {"semiconductor": 0.9, "tech": 0.8},
    "集成电路": {"semiconductor": 1.0, "tech": 0.9},
    "AI": {"tech": 1.0, "growth": 0.7},
    "人工智能": {"tech": 1.0, "growth": 0.7},
    "ChatGPT": {"tech": 1.0, "growth": 0.6},
    "算力": {"tech": 1.0, "growth": 0.6},
    "大数据": {"tech": 0.9, "growth": 0.5},
    "云计算": {"tech": 1.0, "growth": 0.7},
    "信创": {"tech": 0.9, "defense": 0.3},
    "华为": {"tech": 0.8, "telecom": 0.6},
    "5G": {"tech": 0.7, "telecom": 0.9},
    "6G": {"tech": 0.7, "telecom": 1.0},
    "通信": {"telecom": 1.0, "tech": 0.6},
    "光纤": {"telecom": 0.9, "tech": 0.5},
    "CPO": {"tech": 0.8, "telecom": 0.7},
    "光通信": {"telecom": 0.9, "tech": 0.7},
    "新能源汽车": {"new_energy": 1.0, "growth": 0.7},
    "新能源车": {"new_energy": 1.0, "growth": 0.7},
    "锂电池": {"new_energy": 0.9, "growth": 0.6},
    "光伏": {"new_energy": 1.0, "growth": 0.7},
    "风电": {"new_energy": 0.9, "growth": 0.5},
    "储能": {"new_energy": 0.8, "growth": 0.6},
    "新能源": {"new_energy": 0.9, "growth": 0.5},
    "军工": {"defense": 1.0, "growth": 0.4},
    "航天": {"defense": 0.9, "growth": 0.4},
    "低空经济": {"defense": 0.6, "growth": 0.7, "tech": 0.4},
    "飞行汽车": {"defense": 0.5, "growth": 0.8, "tech": 0.5},
    "医疗": {"healthcare": 1.0, "growth": 0.5},
    "医药": {"healthcare": 1.0, "growth": 0.5},
    "创新药": {"healthcare": 1.0, "growth": 0.7},
    "医疗器械": {"healthcare": 1.0},
    "消费": {"consumer": 1.0},
    "白酒": {"consumer": 1.0, "liquor": 1.0, "value": 0.3},
    "食品": {"consumer": 1.0},
    "免税": {"consumer": 0.9},
    "旅游": {"consumer": 0.8},
    "游戏": {"tech": 0.8, "internet": 0.7, "consumer": 0.5},
    "互联网": {"internet": 1.0, "tech": 0.8},
    "黄金": {"commodity_gold": 1.0},
    "白银": {"commodity_gold": 0.9},
    "贵金属": {"commodity_gold": 0.9},
    "石油": {"commodity_oil": 1.0},
    "原油": {"commodity_oil": 1.0},
    "煤炭": {"commodity_energy": 0.8},
    "电力": {"commodity_energy": 0.7, "growth": 0.3},
    "创业板": {"growth": 0.8, "tech": 0.5, "broad_market": 0.4},
    "中证1000": {"broad_market": 0.8, "growth": 0.5},
    "纳指": {"us_equity": 1.0, "tech": 0.9},
    "纳斯达克": {"us_equity": 1.0, "tech": 0.9},
    "港股": {"hongkong_equity": 1.0},
    "恒生": {"hongkong_equity": 1.0},
    "日经": {"japan_equity": 1.0},
    "日本": {"japan_equity": 1.0},
    "豆粕": {"commodity_agriculture": 1.0},
    "猪肉": {"commodity_agriculture": 0.8, "consumer": 0.5},
    "农业": {"commodity_agriculture": 0.7, "consumer": 0.4},
    "金融": {"finance": 0.9, "value": 0.6},
    "券商": {"finance": 1.0, "growth": 0.5},
    "银行": {"finance": 1.0, "value": 0.8},
    "地产": {"real_estate": 1.0, "value": 0.5},
    "红利": {"dividend_value": 1.0, "value": 0.9},
    "高股息": {"dividend_value": 1.0, "value": 0.9},
    "超超临界": {"commodity_energy": 0.8},
}

# ── ETF metadata (exposure profiles) ──

ETF_METADATA: dict[str, dict[str, Any]] = {
    "162719": {"name": "广发道琼斯美国石油开发", "exposures": {"overseas_equity": 1.0, "us_equity": 1.0, "commodity_oil": 0.9}},
    "159915": {"name": "创业板ETF", "exposures": {"china_equity": 1.0, "growth": 1.0, "tech": 0.45, "broad_market": 0.4}},
    "159985": {"name": "豆粕ETF", "exposures": {"commodity_agriculture": 1.0}},
    "515030": {"name": "新能源车ETF", "exposures": {"china_equity": 1.0, "new_energy": 1.0, "growth": 0.8, "tech": 0.35}},
    "513060": {"name": "恒生医疗ETF", "exposures": {"hongkong_equity": 1.0, "healthcare": 1.0, "growth": 0.5}},
    "512560": {"name": "中证军工ETF", "exposures": {"china_equity": 1.0, "defense": 1.0, "growth": 0.4}},
    "516510": {"name": "云计算ETF", "exposures": {"china_equity": 1.0, "tech": 1.0, "growth": 0.8}},
    "515880": {"name": "通信ETF", "exposures": {"china_equity": 1.0, "tech": 0.85, "growth": 0.5, "telecom": 0.7}},
    "515790": {"name": "光伏ETF", "exposures": {"china_equity": 1.0, "new_energy": 1.0, "growth": 0.8}},
    "513100": {"name": "纳指ETF", "exposures": {"us_equity": 1.0, "tech": 0.75, "growth": 0.75}},
    "512100": {"name": "中证1000ETF", "exposures": {"china_equity": 1.0, "broad_market": 0.7, "growth": 0.35}},
    "512690": {"name": "酒ETF", "exposures": {"china_equity": 1.0, "consumer": 1.0, "value": 0.35, "liquor": 0.9}},
    "513330": {"name": "恒生互联网ETF", "exposures": {"hongkong_equity": 1.0, "tech": 0.85, "growth": 0.8, "internet": 0.9}},
    "518880": {"name": "黄金ETF", "exposures": {"commodity_gold": 1.0}},
    "161128": {"name": "标普科技LOF", "exposures": {"us_equity": 1.0, "tech": 1.0, "growth": 0.85}},
    "513300": {"name": "纳斯达克100ETF", "exposures": {"us_equity": 1.0, "tech": 0.75, "growth": 0.75}},
    "513310": {"name": "中韩半导体ETF", "exposures": {"semiconductor": 1.0, "tech": 1.0, "growth": 0.8}},
    "513880": {"name": "日经225ETF", "exposures": {"japan_equity": 1.0, "broad_market": 0.6}},
    "515100": {"name": "红利100ETF", "exposures": {"dividend_value": 1.0, "value": 0.8, "china_equity": 0.8}},
    "515980": {"name": "人工智能ETF", "exposures": {"tech": 1.0, "growth": 0.8, "china_equity": 0.9}},
    "512480": {"name": "半导体ETF", "exposures": {"semiconductor": 1.0, "tech": 1.0, "growth": 0.7, "china_equity": 0.9}},
    "512980": {"name": "传媒ETF", "exposures": {"internet": 0.8, "consumer": 0.6, "tech": 0.6, "china_equity": 0.9}},
    "513690": {"name": "恒生高股息ETF", "exposures": {"hongkong_equity": 1.0, "dividend_value": 0.9, "value": 0.7}},
    "516640": {"name": "芯片ETF", "exposures": {"semiconductor": 1.0, "tech": 1.0, "growth": 0.7}},
    "561910": {"name": "电池ETF", "exposures": {"new_energy": 0.9, "growth": 0.7, "china_equity": 1.0}},
    "588000": {"name": "科创50ETF", "exposures": {"tech": 0.9, "growth": 0.9, "semiconductor": 0.5, "china_equity": 0.9}},
    "159329": {"name": "纳斯达克ETF", "exposures": {"us_equity": 1.0, "tech": 0.8, "growth": 0.7}},
    "159919": {"name": "沪深300ETF", "exposures": {"china_equity": 1.0, "broad_market": 1.0, "value": 0.5}},
}

# Benchmark ETFs (not in the trading pool)
BENCHMARK_SYMBOLS = {"159919", "510300"}


# ═══════════════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════════════

def load_ths_hot(trade_date: str) -> pd.DataFrame:
    """Load THS hot data for a date from the data lake."""
    from hot_sector_screener.data_sources.platform import load_ths_hot as _load
    return _load(trade_date, limit=200)


def load_etf_csv(symbol: str) -> pd.DataFrame | None:
    """Load an ETF CSV file from rotation-v3's data/raw/etf/."""
    path = ROTATION_ROOT / "data" / "raw" / "etf" / f"{symbol}.csv"
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        print(f"  Failed to load {symbol}: {e}")
        return None


def load_all_etf_data() -> dict[str, pd.DataFrame]:
    """Load all ETF CSVs, skipping benchmarks."""
    etf_data: dict[str, pd.DataFrame] = {}
    for sym in ETF_METADATA:
        if sym in BENCHMARK_SYMBOLS:
            continue
        df = load_etf_csv(sym)
        if df is not None and not df.empty:
            etf_data[sym] = df
    print(f"Loaded {len(etf_data)} ETFs ({len(ETF_METADATA) - len(BENCHMARK_SYMBOLS)} in pool)")
    return etf_data


def load_benchmark_etf() -> pd.DataFrame | None:
    """Load CSI300 ETF (159919 or 510300) for benchmark."""
    for sym in ("510300", "159919"):
        path = ROTATION_ROOT / "data" / "raw" / "etf" / f"{sym}.csv"
        if path.exists():
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values("date").set_index("date")
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Concept → ETF feature construction
# ═══════════════════════════════════════════════════════════════════════════

def extract_concepts_from_hot(trade_date: str, top_n: int = 30) -> list[str]:
    """Extract concept names from THS hot data for a given date."""
    df = load_ths_hot(trade_date)
    if df.empty:
        return []

    if "rank" in df.columns:
        df = df.sort_values("rank").head(top_n)

    all_concepts: list[str] = []
    for raw in df["concept"]:
        s = str(raw).strip().strip("[]").strip('"').strip("'")
        parts = re.split(r'[",，]\s*', s)
        for p in parts:
            p = p.strip().strip('"').strip("'")
            if p and p not in ("", "[", "]"):
                all_concepts.append(p)
    return all_concepts


def concepts_to_dimension_scores(concepts: list[str]) -> dict[str, float]:
    """Map concept names to exposure dimension scores."""
    dim_scores: dict[str, float] = {}
    for c in concepts:
        for keyword, dims in CONCEPT_EXPOSURE_MAP.items():
            if keyword.lower() in c.lower() or c.lower() in keyword.lower():
                for dim, weight in dims.items():
                    dim_scores[dim] = dim_scores.get(dim, 0) + weight
    return dim_scores


def score_etfs(dim_scores: dict[str, float]) -> dict[str, float]:
    """Score each ETF by dot product of its exposures with dimension scores."""
    scores: dict[str, float] = {}
    for sym, meta in ETF_METADATA.items():
        if sym in BENCHMARK_SYMBOLS:
            continue
        score = 0.0
        for dim, weight in meta["exposures"].items():
            if dim in dim_scores:
                score += dim_scores[dim] * weight
        scores[sym] = score
    return scores


def build_concept_features_for_date(
    trade_date_str: str,
    concept_score_history: dict[str, list[tuple[str, float]]],
    top_n_hot: int = 30,
) -> dict[str, dict[str, float]]:
    """Build concept-based feature vector for each ETF on a given date.

    Returns:
        {symbol: {feature_name: value, ...}}
    """
    date_fmt = f"{trade_date_str[:4]}-{trade_date_str[4:6]}-{trade_date_str[6:]}"

    # 1. Get today's concept scores
    concepts = extract_concepts_from_hot(date_fmt, top_n=top_n_hot)
    dim_scores = concepts_to_dimension_scores(concepts)
    etf_scores = score_etfs(dim_scores)

    if not etf_scores:
        return {}

    # 2. Update score history
    for sym, score in etf_scores.items():
        if sym not in concept_score_history:
            concept_score_history[sym] = []
        concept_score_history[sym].append((trade_date_str, score))
        # Keep last 30 days
        if len(concept_score_history[sym]) > 30:
            concept_score_history[sym] = concept_score_history[sym][-30:]

    # 3. Build features per ETF
    features: dict[str, dict[str, float]] = {}
    for sym in etf_scores:
        hist = concept_score_history.get(sym, [])
        scores_arr = [s for _, s in hist]

        f: dict[str, float] = {}
        f["concept_score"] = scores_arr[-1] if scores_arr else 0.0

        # Lagged features
        f["concept_score_lag1"] = scores_arr[-2] if len(scores_arr) >= 2 else 0.0
        f["concept_score_lag2"] = scores_arr[-3] if len(scores_arr) >= 3 else 0.0

        # Moving averages
        f["concept_score_ma3"] = np.mean(scores_arr[-3:]) if len(scores_arr) >= 3 else f["concept_score"]
        f["concept_score_ma5"] = np.mean(scores_arr[-5:]) if len(scores_arr) >= 5 else f["concept_score"]

        # Changes (momentum)
        f["concept_score_chg_1d"] = f["concept_score"] - f["concept_score_lag1"]
        f["concept_score_chg_3d"] = (
            f["concept_score"] - scores_arr[-4]
        ) if len(scores_arr) >= 4 else 0.0

        # Volatility of scores
        f["concept_score_vol_5d"] = np.std(scores_arr[-5:]) if len(scores_arr) >= 5 else 0.0

        # Relative rank (z-score among ETFs today)
        all_scores = list(etf_scores.values())
        mean_score = np.mean(all_scores) if all_scores else 0.0
        std_score = np.std(all_scores) if all_scores else 1.0
        f["concept_score_zscore"] = (
            (f["concept_score"] - mean_score) / std_score if std_score > 0 else 0.0
        )

        # Market-wide features (same for all ETFs)
        f["concept_breadth"] = float(len(set(concepts)))
        f["concept_count"] = float(len(concepts))
        f["concept_score_sum"] = float(sum(all_scores))

        features[sym] = f

    return features


# ═══════════════════════════════════════════════════════════════════════════
# Model and backtest
# ═══════════════════════════════════════════════════════════════════════════

class LinearRankModel:
    """Simple ridge regression model for cross-sectional ranking."""

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.coef_: np.ndarray | None = None
        self.intercept_: float = 0.0
        self.feature_names_: list[str] = []

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: list[str]):
        """Fit ridge regression."""
        self.feature_names_ = list(feature_names)
        n_samples, n_features = X.shape

        # Add intercept
        X_mean = X.mean(axis=0)
        X_centered = X - X_mean
        y_mean = y.mean()

        # Ridge: (X'X + alpha*I)^-1 X'y
        A = X_centered.T @ X_centered + self.alpha * np.eye(n_features)
        b = X_centered.T @ (y - y_mean)

        try:
            self.coef_ = np.linalg.solve(A, b)
            self.intercept_ = y_mean - X_mean @ self.coef_
        except np.linalg.LinAlgError:
            # Fallback: pseudoinverse
            self.coef_ = np.linalg.lstsq(A, b, rcond=None)[0]
            self.intercept_ = y_mean - X_mean @ self.coef_

    def predict(self, X: np.ndarray) -> np.ndarray:
        return X @ self.coef_ + self.intercept_


def build_training_matrix(
    features_by_date: dict[str, dict[str, dict[str, float]]],
    etf_data: dict[str, pd.DataFrame],
    date_list: list[str],
) -> tuple[pd.DataFrame, pd.Series, list[str], list[str]]:
    """Build feature matrix X and label vector y.

    Label: (T+2 open / T+1 open) - 1, the same as rotation-v3's next_open_to_open.
    """
    rows: list[dict] = []
    feature_names: set[str] = set()

    for i in range(len(date_list) - 2):
        t_date = date_list[i]       # signal date
        t1_date = date_list[i + 1]  # entry date
        t2_date = date_list[i + 2]  # exit date

        features_t = features_by_date.get(t_date, {})
        if not features_t:
            continue

        for sym, feats in features_t.items():
            df = etf_data.get(sym)
            if df is None:
                continue

            # Get entry and exit prices
            t1_str = f"{t1_date[:4]}-{t1_date[4:6]}-{t1_date[6:]}"
            t2_str = f"{t2_date[:4]}-{t2_date[4:6]}-{t2_date[6:]}"

            try:
                entry_px = df.loc[t1_str, "open"]
                exit_px = df.loc[t2_str, "open"]
            except KeyError:
                continue

            if entry_px <= 0 or exit_px <= 0:
                continue

            label = (exit_px / entry_px) - 1.0
            if not np.isfinite(label):
                continue

            row = {"symbol": sym, "date": t_date, "label": label}
            row.update(feats)
            rows.append(row)
            feature_names.update(feats.keys())

    if not rows:
        return pd.DataFrame(), pd.Series(dtype=float), [], []

    df = pd.DataFrame(rows)
    feature_list = sorted(feature_names)
    X = df[feature_list].astype(float).fillna(0.0)
    y = df["label"].astype(float)

    return X, y, feature_list, df["date"].tolist()


def walk_forward_backtest(
    X: pd.DataFrame,
    y: pd.Series,
    dates: list[str],
    feature_names: list[str],
    etf_data: dict[str, pd.DataFrame],
    features_by_date: dict[str, dict[str, dict[str, float]]],
    date_list: list[str],
    train_window: int = 120,
    step: int = 20,
    top_k: int = 3,
    alpha: float = 1.0,
) -> dict[str, Any]:
    """Walk-forward backtest with purged training windows.

    Each fold:
      1. Train on dates [fold_start, cutoff)
      2. Test on dates [cutoff, cutoff + step)
      3. Purge 3 days between train and test
    """
    unique_dates = sorted(set(dates))
    if len(unique_dates) < train_window + step:
        print(f"  Not enough dates for walk-forward: {len(unique_dates)}")
        return {"error": "Not enough data"}

    daily_returns: list[float] = []
    trade_log: list[dict] = []
    nav = 1.0
    all_predictions: list[dict] = []
    fold_metrics: list[dict] = []

    purge_days = 3

    # Walk-forward
    fold_start = 0
    fold_idx = 0
    while fold_start + train_window + step <= len(unique_dates):
        train_end_idx = fold_start + train_window
        test_start_idx = train_end_idx + purge_days
        test_end_idx = min(test_start_idx + step, len(unique_dates))

        if test_start_idx >= len(unique_dates):
            break

        train_dates = unique_dates[fold_start:train_end_idx]
        test_dates = unique_dates[test_start_idx:test_end_idx]

        # Build training mask
        date_series = pd.Series(dates)
        train_mask = date_series.isin(train_dates).values
        test_mask = date_series.isin(test_dates).values

        X_train = X.iloc[train_mask].values
        y_train = y.iloc[train_mask].values
        X_test = X.iloc[test_mask].values
        y_test = y.iloc[test_mask].values
        test_date_list = [dates[i] for i, m in enumerate(test_mask) if m]

        if len(X_train) < 50 or len(X_test) < 5:
            fold_start += step
            continue

        # Train
        model = LinearRankModel(alpha=alpha)
        model.fit(X_train, y_train, feature_names)

        # Predict on test set
        preds = model.predict(X_test)

        # Compute rank IC on test set
        if len(preds) >= 5:
            ic = np.corrcoef(preds, y_test)[0, 1] if len(set(preds)) > 1 else 0.0
        else:
            ic = 0.0

        # Group predictions by date and pick top-K ETFs per day
        test_df = X.iloc[test_mask].copy()
        test_df["pred"] = preds
        test_df["true_label"] = y_test
        test_df["date"] = test_date_list

        fold_daily_returns: list[float] = []
        for t_date in sorted(set(test_date_list)):
            day_rows = test_df[test_df["date"] == t_date]
            if len(day_rows) < top_k:
                continue

            top_etfs = day_rows.nlargest(top_k, "pred")
            avg_ret = top_etfs["true_label"].mean()

            if np.isfinite(avg_ret):
                daily_returns.append(avg_ret)
                fold_daily_returns.append(avg_ret)
                nav *= (1 + avg_ret)
                trade_log.append({
                    "date": t_date,
                    "etfs": list(top_etfs.index),
                    "return": float(avg_ret),
                    "nav": float(nav),
                })

        fold_sharpe = (
            np.mean(fold_daily_returns) / np.std(fold_daily_returns) * np.sqrt(252)
            if len(fold_daily_returns) > 1 and np.std(fold_daily_returns) > 0
            else 0.0
        )

        fold_metrics.append({
            "fold": fold_idx,
            "train_dates": f"{train_dates[0]}~{train_dates[-1]}",
            "test_dates": f"{test_dates[0]}~{test_dates[-1]}",
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "rank_ic": round(float(ic), 4),
            "fold_sharpe": round(fold_sharpe, 3),
            "fold_return": round(float(np.prod(1 + np.array(fold_daily_returns)) - 1) * 100, 2) if fold_daily_returns else 0.0,
        })

        fold_start += step
        fold_idx += 1

    # Benchmark (buy & hold CSI300 ETF)
    bm_df = load_benchmark_etf()
    bm_return = None
    if bm_df is not None and len(trade_log) > 0:
        first_date = trade_log[0]["date"]
        last_date = trade_log[-1]["date"]
        first_fmt = f"{first_date[:4]}-{first_date[4:6]}-{first_date[6:]}"
        last_fmt = f"{last_date[:4]}-{last_date[4:6]}-{last_date[6:]}"
        try:
            bm_entry = bm_df.loc[first_fmt, "open"]
            bm_exit = bm_df.loc[last_fmt, "close"]
            bm_return = float(bm_exit / bm_entry - 1)
        except KeyError:
            pass

    # Strategy metrics
    rets = np.array(daily_returns)
    total_ret = float(np.prod(1 + rets) - 1) if len(rets) > 0 else 0.0
    ann_ret = float((1 + total_ret) ** (252 / len(rets)) - 1) if len(rets) > 1 else 0.0
    vol = float(np.std(rets) * np.sqrt(252)) if len(rets) > 1 else 0.0
    sharpe = float(np.mean(rets) / np.std(rets) * np.sqrt(252)) if len(rets) > 1 and np.std(rets) > 0 else 0.0
    max_dd = float(np.min(np.minimum.accumulate(1 + rets) / np.maximum.accumulate(1 + rets)) - 1) if len(rets) > 0 else 0.0
    hit_rate = float(np.mean(rets > 0)) if len(rets) > 0 else 0.0

    excess = (total_ret - bm_return) if bm_return is not None else None

    return {
        "period": f"{date_list[0]} ~ {date_list[-1]}",
        "config": {
            "train_window": train_window,
            "step": step,
            "top_k": top_k,
            "alpha": alpha,
            "feature_count": len(feature_names),
        },
        "strategy": {
            "total_return_pct": round(total_ret * 100, 2),
            "annual_return_pct": round(ann_ret * 100, 2),
            "sharpe": round(sharpe, 3),
            "volatility_pct": round(vol * 100, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "hit_rate_pct": round(hit_rate * 100, 1),
            "trade_count": len(daily_returns),
        },
        "benchmark": {
            "label": "CSI300 ETF 买入持有",
            "total_return_pct": round(bm_return * 100, 2) if bm_return is not None else None,
        },
        "excess_return_pct": round(excess * 100, 2) if excess is not None else None,
        "fold_metrics": fold_metrics,
        "feature_names": feature_names,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("Path B Prototype: Concept → ETF ML Backtest")
    print("=" * 70)
    print()

    # 1. Load ETF data
    print("[1/4] Loading ETF data...")
    etf_data = load_all_etf_data()
    if len(etf_data) < 5:
        print("ERROR: Need at least 5 ETFs with data. Run download first:")
        print("  cd ~/code/guan-etf-rotation-v3")
        print("  uv run etf-rotation download --config configs/experiments/small_pool_linear_rank.yml --data-source efinance")
        return
    print(f"  Trading ETFs: {list(etf_data.keys())}")
    print()

    # 2. Get THS hot dates and build date list
    print("[2/4] Building concept features...")
    from hot_sector_screener.data_sources.platform import list_available_dates
    ths_dates = sorted(list_available_dates("ths_hot"))
    print(f"  THS hot data: {len(ths_dates)} days, {ths_dates[0]} ~ {ths_dates[-1]}")

    # Find common dates with ETF data
    etf_dates: set[str] = set()
    for df in etf_data.values():
        for d in df.index:
            etf_dates.add(d.strftime("%Y%m%d"))

    date_list = sorted(set(ths_dates) & etf_dates)
    print(f"  Overlap (THS ∩ ETF): {len(date_list)} days, {date_list[0]} ~ {date_list[-1]}")

    if len(date_list) < 150:
        print(f"  ERROR: Need at least 150 overlapping dates, got {len(date_list)}")
        return

    # 3. Build feature matrix
    print("  Computing concept features for each date...")
    concept_score_history: dict[str, list[tuple[str, float]]] = {}
    features_by_date: dict[str, dict[str, dict[str, float]]] = {}

    for i, d in enumerate(date_list):
        feats = build_concept_features_for_date(d, concept_score_history)
        if feats:
            features_by_date[d] = feats
        if (i + 1) % 50 == 0:
            print(f"    ... {i + 1}/{len(date_list)} dates processed")

    print(f"  Feature dates: {len(features_by_date)}")
    print()

    # 4. Build training matrix and run backtests
    print("[3/4] Building training matrix...")
    X, y, feature_names, dates = build_training_matrix(
        features_by_date, etf_data, date_list
    )
    print(f"  Samples: {len(X)}, Features: {len(feature_names)}")
    print(f"  Feature names: {feature_names}")
    print(f"  Label stats: mean={y.mean():.4f}, std={y.std():.4f}, min={y.min():.4f}, max={y.max():.4f}")
    print()

    # 5. Run walk-forward backtests with multiple parameter sets
    print("[4/4] Running walk-forward backtests...")
    print()

    configs = [
        {"train_window": 120, "step": 20, "top_k": 3, "alpha": 1.0},
        {"train_window": 120, "step": 20, "top_k": 5, "alpha": 1.0},
        {"train_window": 180, "step": 20, "top_k": 3, "alpha": 1.0},
        {"train_window": 120, "step": 20, "top_k": 3, "alpha": 10.0},
    ]

    for cfg in configs:
        print(f"  Config: train_window={cfg['train_window']}, step={cfg['step']}, "
              f"top_k={cfg['top_k']}, alpha={cfg['alpha']}")
        result = walk_forward_backtest(
            X, y, dates, feature_names, etf_data, features_by_date, date_list,
            **cfg,
        )

        if "error" in result:
            print(f"    ERROR: {result['error']}")
            continue

        s = result["strategy"]
        print(f"    Return: {s['total_return_pct']:+.2f}% total, "
              f"{s['annual_return_pct']:+.2f}% ann")
        print(f"    Sharpe: {s['sharpe']:.3f}, MaxDD: {s['max_drawdown_pct']:.2f}%")
        print(f"    Hit rate: {s['hit_rate_pct']:.1f}%, Trades: {s['trade_count']}")
        if result.get("excess_return_pct") is not None:
            print(f"    Excess vs CSI300: {result['excess_return_pct']:+.2f}%")
        print(f"    Folds: {len(result['fold_metrics'])}")
        print()

    print("Done. Full results above.")


if __name__ == "__main__":
    main()
