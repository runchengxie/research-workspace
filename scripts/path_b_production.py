#!/usr/bin/env python3
# pyright: basic
"""
Path B production version: Concept + Technical feature fusion for ETF rotation.

Enhancements over prototype:
  1. Concept features (from THS hot list)
  2. Technical features (from rotation-v3's feature engine, when available)
  3. Fusion: concept + technical features combined
  4. Hyperparameter grid search
  5. Model persistence for live trading
  6. Proper benchmark alignment (daily CSI300 ETF benchmark)

Compares three signal sources side-by-side:
  A: Concept-only (THS hot list → concept features)
  B: Technical-only (rotation-v3's 17 features)
  C: Fusion (both concept + technical)

Usage:
    cd ~/code/hot-sector-screener
    DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform \
    ETF_ROTATION_ROOT=/home/richard/code/guan-etf-rotation-v3 \
    uv run python /home/richard/code/research-workspace/scripts/path_b_production.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

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

# ═══════════════════════════════════════════════════════════════════════════
# Concept → Exposure dimension mapping
# ═══════════════════════════════════════════════════════════════════════════

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
}

# ── ETF metadata ──

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

BENCHMARK_SYMBOLS = {"159919", "510300"}
TRADING_SYMBOLS = [s for s in ETF_METADATA if s not in BENCHMARK_SYMBOLS]


# ═══════════════════════════════════════════════════════════════════════════
# Feature builders
# ═══════════════════════════════════════════════════════════════════════════

def build_concept_features(
    trade_date_str: str,
    concept_score_history: dict[str, list[tuple[str, float]]],
    top_n_hot: int = 30,
) -> dict[str, dict[str, float]]:
    """Build concept-based feature vector for each ETF.

    Returns: {symbol: {feature_name: value, ...}}
    """
    from hot_sector_screener.data_sources.platform import load_ths_hot as _load

    date_fmt = f"{trade_date_str[:4]}-{trade_date_str[4:6]}-{trade_date_str[6:]}"
    hot = _load(date_fmt, limit=200)
    if hot.empty:
        return {}

    if "rank" in hot.columns:
        hot = hot.sort_values("rank").head(top_n_hot)

    # Extract concepts
    all_concepts: list[str] = []
    for raw in hot["concept"]:
        s = str(raw).strip().strip("[]").strip('"').strip("'")
        parts = re.split(r'[",，]\s*', s)
        for p in parts:
            p = p.strip().strip('"').strip("'")
            if p and p not in ("", "[", "]"):
                all_concepts.append(p)

    # Map to dimension scores
    dim_scores: dict[str, float] = {}
    for c in all_concepts:
        for keyword, dims in CONCEPT_EXPOSURE_MAP.items():
            if keyword.lower() in c.lower() or c.lower() in keyword.lower():
                for dim, weight in dims.items():
                    dim_scores[dim] = dim_scores.get(dim, 0) + weight

    # Score ETFs
    etf_scores: dict[str, float] = {}
    for sym in TRADING_SYMBOLS:
        meta = ETF_METADATA.get(sym)
        if meta is None:
            continue
        score = sum(
            dim_scores.get(dim, 0) * weight
            for dim, weight in meta["exposures"].items()
        )
        etf_scores[sym] = score

    if not etf_scores:
        return {}

    # Update history
    for sym, score in etf_scores.items():
        if sym not in concept_score_history:
            concept_score_history[sym] = []
        concept_score_history[sym].append((trade_date_str, score))
        if len(concept_score_history[sym]) > 30:
            concept_score_history[sym] = concept_score_history[sym][-30:]

    # Build features
    all_scores_list = list(etf_scores.values())
    mean_score = np.mean(all_scores_list) if all_scores_list else 0
    std_score = np.std(all_scores_list) if all_scores_list else 1

    features: dict[str, dict[str, float]] = {}
    for sym in etf_scores:
        hist = concept_score_history.get(sym, [])
        scores_arr = [s for _, s in hist]
        n = len(scores_arr)

        f: dict[str, float] = {}
        f["c_score"] = scores_arr[-1] if n >= 1 else 0
        f["c_lag1"] = scores_arr[-2] if n >= 2 else 0
        f["c_lag2"] = scores_arr[-3] if n >= 3 else 0
        f["c_ma3"] = float(np.mean(scores_arr[-3:])) if n >= 3 else f["c_score"]
        f["c_ma5"] = float(np.mean(scores_arr[-5:])) if n >= 5 else f["c_score"]
        f["c_ma10"] = float(np.mean(scores_arr[-10:])) if n >= 10 else f["c_score"]
        f["c_chg1"] = f["c_score"] - f["c_lag1"]
        f["c_chg3"] = f["c_score"] - scores_arr[-4] if n >= 4 else 0
        f["c_chg5"] = f["c_score"] - scores_arr[-6] if n >= 6 else 0
        f["c_vol5"] = float(np.std(scores_arr[-5:])) if n >= 5 else 0
        f["c_vol10"] = float(np.std(scores_arr[-10:])) if n >= 10 else 0
        f["c_zscore"] = (f["c_score"] - mean_score) / std_score if std_score > 0 else 0
        f["c_rank_pct"] = sum(1 for s in all_scores_list if s < f["c_score"]) / max(len(all_scores_list), 1)
        f["c_breadth"] = float(len(set(all_concepts)))
        f["c_count"] = float(len(all_concepts))
        f["c_sum"] = float(sum(all_scores_list))

        features[sym] = f

    return features


def build_technical_features(
    etf_data: dict[str, pd.DataFrame],
    trade_date_str: str,
) -> dict[str, dict[str, float]] | None:
    """Build rotation-v3 technical features for each ETF on a given date.

    Tries to use rotation-v3's feature engine cache; falls back to on-the-fly
    calculation for a subset of features.
    """
    date_fmt = f"{trade_date_str[:4]}-{trade_date_str[4:6]}-{trade_date_str[6:]}"
    target_date = pd.Timestamp(date_fmt)

    features: dict[str, dict[str, float]] = {}

    for sym, df in etf_data.items():
        if sym in BENCHMARK_SYMBOLS or df is None or df.empty:
            continue
        if target_date not in df.index:
            continue

        # Get data up to this date
        hist = df.loc[:target_date]
        if len(hist) < 60:
            continue

        close = hist["close"].astype(float)
        ret = close.pct_change()

        f: dict[str, float] = {}

        # ROC features
        for n in [12, 18, 20]:
            if len(close) > n:
                f[f"t_roc_{n}"] = float(close.iloc[-1] / close.iloc[-n-1] - 1)
            else:
                f[f"t_roc_{n}"] = 0.0

        # Cumulative return 120d
        if len(ret.dropna()) >= 120:
            f["t_cumret_120"] = float((1 + ret.iloc[-120:]).prod() - 1)
        else:
            f["t_cumret_120"] = 0.0

        # Volatility 120d
        if len(ret.dropna()) >= 120:
            f["t_vol_120"] = float(ret.iloc[-120:].std() * np.sqrt(252))
        else:
            f["t_vol_120"] = 0.0

        # Skew/Kurtosis 60d
        if len(ret.dropna()) >= 60:
            f["t_skew_60"] = float(ret.iloc[-60:].skew())
            f["t_kurt_60"] = float(ret.iloc[-60:].kurt())
        else:
            f["t_skew_60"] = 0.0
            f["t_kurt_60"] = 0.0

        # ATR ratio 20d
        if len(hist) >= 20:
            high = hist["high"].astype(float)
            low = hist["low"].astype(float)
            tr = pd.concat([
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ], axis=1).max(axis=1)
            atr = tr.rolling(20).mean().iloc[-1]
            f["t_atr_ratio"] = float(atr / close.iloc[-1]) if close.iloc[-1] > 0 else 0
        else:
            f["t_atr_ratio"] = 0.0

        # Volume ratio (5d/20d)
        if "volume" in hist.columns and len(hist) >= 20:
            vol = hist["volume"].astype(float)
            ma5 = vol.iloc[-5:].mean()
            ma20 = vol.iloc[-20:].mean()
            f["t_vol_ratio"] = float(ma5 / ma20) if ma20 > 0 else 0
        else:
            f["t_vol_ratio"] = 0.0

        # Aroon
        if len(hist) >= 25:
            high_vals = hist["high"].astype(float)
            low_vals = hist["low"].astype(float)
            window = 25
            aroon_up = (window - (window - 1 - high_vals.iloc[-window:].values.argmax())) / window * 100
            aroon_down = (window - (window - 1 - low_vals.iloc[-window:].values.argmin())) / window * 100
            f["t_aroon_up"] = float(aroon_up)
            f["t_aroon_down"] = float(aroon_down)
        else:
            f["t_aroon_up"] = 0.0
            f["t_aroon_down"] = 0.0

        # Dispersion 5d
        if len(close) >= 5:
            disp = close.iloc[-5:].std() / close.iloc[-5:].mean()
            f["t_dispersion_5"] = float(disp)
        else:
            f["t_dispersion_5"] = 0.0

        # High-Low ratio, Close-Open ratio
        if target_date in hist.index:
            row = hist.loc[target_date]
            f["t_high_low"] = float(row["high"] / row["low"]) if row["low"] > 0 else 1.0
            f["t_close_open"] = float(row["close"] / row["open"]) if row["open"] > 0 else 1.0

        features[sym] = f

    return features if features else None


# ═══════════════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════════════

def load_all_etf_data() -> dict[str, pd.DataFrame]:
    etf_data: dict[str, pd.DataFrame] = {}
    for sym in ETF_METADATA:
        path = ROTATION_ROOT / "data" / "raw" / "etf" / f"{sym}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if not df.empty:
            etf_data[sym] = df
    return etf_data


def load_benchmark_etf() -> pd.DataFrame | None:
    for sym in ("510300", "159919"):
        path = ROTATION_ROOT / "data" / "raw" / "etf" / f"{sym}.csv"
        if path.exists():
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["date"])
            return df.sort_values("date").set_index("date")
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Feature matrix builder
# ═══════════════════════════════════════════════════════════════════════════

def build_feature_matrix(
    date_list: list[str],
    etf_data: dict[str, pd.DataFrame],
    mode: str = "concept",  # "concept", "technical", "fusion"
) -> tuple[pd.DataFrame, pd.Series, list[str], list[str]]:
    """Build feature matrix X and label vector y.

    mode: "concept" = concept features only
          "technical" = technical features only
          "fusion" = both
    """
    if mode in ("concept", "fusion"):
        print(f"  Building concept features ({mode})...")
        concept_score_history: dict[str, list[tuple[str, float]]] = {}
        concept_features_by_date: dict[str, dict[str, dict[str, float]]] = {}
        for i, d in enumerate(date_list):
            cf = build_concept_features(d, concept_score_history)
            if cf:
                concept_features_by_date[d] = cf
            if (i + 1) % 100 == 0:
                print(f"    ... concept: {i + 1}/{len(date_list)}")

    rows: list[dict] = []
    concept_feature_names: set[str] = set()
    tech_feature_names: set[str] = set()

    total = len(date_list)
    for i in range(total - 2):
        t_date = date_list[i]
        t1_date = date_list[i + 1]
        t2_date = date_list[i + 2]

        t1_str = f"{t1_date[:4]}-{t1_date[4:6]}-{t1_date[6:]}"
        t2_str = f"{t2_date[:4]}-{t2_date[4:6]}-{t2_date[6:]}"

        # Get concept features for this date
        concept_feats = concept_features_by_date.get(t_date, {}) if mode in ("concept", "fusion") else {}

        # Get technical features for this date
        tech_feats = {}
        if mode in ("technical", "fusion"):
            tech_feats = build_technical_features(etf_data, t_date) or {}

        for sym in TRADING_SYMBOLS:
            if sym in BENCHMARK_SYMBOLS:
                continue
            df = etf_data.get(sym)
            if df is None:
                continue

            try:
                entry_px = df.loc[t1_str, "open"]
                exit_px = df.loc[t2_str, "open"]
            except KeyError:
                continue

            if entry_px <= 0 or exit_px <= 0:
                continue

            label = (exit_px / entry_px) - 1.0
            if not np.isfinite(label) or abs(label) > 0.5:
                continue

            row = {"symbol": sym, "date": t_date, "label": label}

            if mode in ("concept", "fusion") and sym in concept_feats:
                row.update(concept_feats[sym])
                concept_feature_names.update(concept_feats[sym].keys())

            if mode in ("technical", "fusion") and sym in tech_feats:
                row.update(tech_feats[sym])
                tech_feature_names.update(tech_feats[sym].keys())

            # Only add if we have at least some features
            has_features = (
                (mode in ("concept", "fusion") and sym in concept_feats) or
                (mode in ("technical", "fusion") and sym in tech_feats)
            )
            if not has_features:
                continue

            rows.append(row)

        if (i + 1) % 100 == 0:
            print(f"    ... labels: {i + 1}/{total}, rows: {len(rows)}")

    if not rows:
        return pd.DataFrame(), pd.Series(dtype=float), [], []

    df = pd.DataFrame(rows)
    all_feature_names = sorted(concept_feature_names | tech_feature_names)
    available = [f for f in all_feature_names if f in df.columns and f != "label"]
    X = df[available].astype(float).fillna(0.0)
    y = df["label"].astype(float)

    return X, y, available, df["date"].tolist()


# ═══════════════════════════════════════════════════════════════════════════
# Model
# ═══════════════════════════════════════════════════════════════════════════

class LinearRankModel:
    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.coef_: np.ndarray | None = None
        self.intercept_: float = 0.0
        self.feature_names_: list[str] = []

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: list[str]):
        self.feature_names_ = list(feature_names)
        n_features = X.shape[1]
        X_mean = X.mean(axis=0)
        X_centered = X - X_mean
        y_mean = y.mean()
        A = X_centered.T @ X_centered + self.alpha * np.eye(n_features)
        b = X_centered.T @ (y - y_mean)
        try:
            self.coef_ = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            self.coef_ = np.linalg.lstsq(A, b, rcond=None)[0]
        self.intercept_ = y_mean - X_mean @ self.coef_

    def predict(self, X: np.ndarray) -> np.ndarray:
        return X @ self.coef_ + self.intercept_

    def to_dict(self) -> dict:
        return {
            "model_type": "linear_rank",
            "alpha": self.alpha,
            "feature_names": self.feature_names_,
            "coefficients": [float(v) for v in self.coef_.tolist()] if self.coef_ is not None else [],
            "intercept": float(self.intercept_),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LinearRankModel":
        m = cls(alpha=d.get("alpha", 1.0))
        m.feature_names_ = d.get("feature_names", [])
        m.coef_ = np.array(d.get("coefficients", []), dtype=float)
        m.intercept_ = d.get("intercept", 0.0)
        return m


# ═══════════════════════════════════════════════════════════════════════════
# Walk-forward backtest
# ═══════════════════════════════════════════════════════════════════════════

def walk_forward_backtest(
    X: pd.DataFrame,
    y: pd.Series,
    dates: list[str],
    feature_names: list[str],
    date_list: list[str],
    train_window: int = 180,
    step: int = 20,
    top_k: int = 3,
    alpha: float = 1.0,
    purge_days: int = 3,
    benchmark_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Walk-forward backtest with purged training windows and daily benchmark tracking."""

    unique_dates = sorted(set(dates))
    if len(unique_dates) < train_window + step:
        return {"error": f"Not enough dates: {len(unique_dates)}"}

    # Daily benchmark returns for aligned comparison
    bm_daily: list[float] = []
    daily_returns: list[float] = []
    trade_log: list[dict] = []
    nav = 1.0
    bm_nav = 1.0
    fold_metrics: list[dict] = []
    all_ics: list[float] = []

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

        date_series = pd.Series(dates)
        train_mask = date_series.isin(train_dates).values
        test_mask = date_series.isin(test_dates).values

        X_train = X.iloc[train_mask].values
        y_train_v = y.iloc[train_mask].values
        X_test = X.iloc[test_mask].values
        y_test = y.iloc[test_mask].values

        if len(X_train) < 50 or len(X_test) < 5:
            fold_start += step
            continue

        model = LinearRankModel(alpha=alpha)
        model.fit(X_train, y_train_v, feature_names)
        preds = model.predict(X_test)

        # Rank IC
        if len(set(preds)) > 1 and len(preds) >= 5:
            ic = stats.spearmanr(preds, y_test)[0]
            if np.isfinite(ic):
                all_ics.append(float(ic))

        # Group by date, pick top-K
        test_df = X.iloc[test_mask].copy()
        test_df["pred"] = preds
        test_df["true_label"] = y_test
        test_df["date"] = [dates[i] for i, m in enumerate(test_mask) if m]

        for t_date in sorted(set(test_df["date"])):
            day_rows = test_df[test_df["date"] == t_date]
            if len(day_rows) < top_k:
                continue
            top_etfs = day_rows.nlargest(top_k, "pred")
            avg_ret = top_etfs["true_label"].mean()
            if not np.isfinite(avg_ret):
                continue

            daily_returns.append(avg_ret)
            nav *= (1 + avg_ret)

            # Benchmark daily return
            t_fmt = f"{t_date[:4]}-{t_date[4:6]}-{t_date[6:]}"
            if benchmark_df is not None:
                try:
                    bm_row = benchmark_df.loc[t_fmt]
                    bm_ret = (float(bm_row["close"]) / float(bm_row["open"])) - 1
                    if np.isfinite(bm_ret):
                        bm_daily.append(bm_ret)
                        bm_nav *= (1 + bm_ret)
                except (KeyError, IndexError):
                    bm_daily.append(0.0)

            trade_log.append({
                "date": t_date,
                "etfs": list(top_etfs.index[:top_k]),
                "return": float(avg_ret),
                "nav": float(nav),
            })

        fold_start += step
        fold_idx += 1

    if not daily_returns:
        return {"error": "No trades generated"}

    # Strategy metrics
    rets = np.array(daily_returns)
    total_ret = float(np.prod(1 + rets) - 1)
    ann_ret = float((1 + total_ret) ** (252 / len(rets)) - 1) if len(rets) > 1 else 0
    vol = float(np.std(rets) * np.sqrt(252)) if len(rets) > 1 else 0
    sharpe = float(np.mean(rets) / np.std(rets) * np.sqrt(252)) if len(rets) > 1 and np.std(rets) > 0 else 0
    max_dd = float(np.min(np.minimum.accumulate(1 + rets) / np.maximum.accumulate(1 + rets)) - 1) if len(rets) > 0 else 0
    hit_rate = float(np.mean(rets > 0)) if len(rets) > 0 else 0
    mean_ic = float(np.mean(all_ics)) if all_ics else 0
    icir = float(np.mean(all_ics) / np.std(all_ics)) if all_ics and np.std(all_ics) > 0 else 0

    # Benchmark metrics
    if bm_daily:
        bm_rets = np.array(bm_daily)
        bm_total = float(np.prod(1 + bm_rets) - 1)
        bm_ann = float((1 + bm_total) ** (252 / len(bm_rets)) - 1) if len(bm_rets) > 1 else 0
        excess = total_ret - bm_total
    else:
        bm_total, bm_ann, excess = 0.0, 0.0, 0.0

    return {
        "total_return_pct": round(total_ret * 100, 2),
        "annual_return_pct": round(ann_ret * 100, 2),
        "sharpe": round(sharpe, 3),
        "volatility_pct": round(vol * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "hit_rate_pct": round(hit_rate * 100, 1),
        "trade_count": len(daily_returns),
        "mean_rank_ic": round(mean_ic, 4),
        "icir": round(icir, 3),
        "benchmark_return_pct": round(bm_total * 100, 2),
        "benchmark_annual_pct": round(bm_ann * 100, 2),
        "excess_return_pct": round(excess * 100, 2),
        "folds": len(fold_metrics),
        "feature_count": len(feature_names),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def run_backtest(
    mode: str,
    date_list: list[str],
    etf_data: dict[str, pd.DataFrame],
    benchmark_df: pd.DataFrame | None,
    train_window: int = 180,
    step: int = 20,
    top_k: int = 3,
    alpha: float = 1.0,
) -> dict[str, Any] | None:
    print(f"\n{'='*60}")
    print(f"Mode: {mode.upper()}")
    print(f"Config: train_window={train_window}, step={step}, top_k={top_k}, alpha={alpha}")
    print(f"{'='*60}")

    X, y, feature_names, dates = build_feature_matrix(date_list, etf_data, mode=mode)
    if X.empty:
        print(f"  ERROR: No features generated")
        return None

    print(f"  Samples: {len(X)}, Features: {len(feature_names)}")
    print(f"  Feature names: {feature_names[:5]}..." if len(feature_names) > 5 else f"  Feature names: {feature_names}")
    print(f"  Label: mean={y.mean():.4f}, std={y.std():.4f}")

    result = walk_forward_backtest(
        X, y, dates, feature_names, date_list,
        train_window=train_window, step=step, top_k=top_k, alpha=alpha,
        benchmark_df=benchmark_df,
    )

    if "error" in result:
        print(f"  ERROR: {result['error']}")
        return None

    print(f"  Return: {result['total_return_pct']:+.2f}% total, {result['annual_return_pct']:+.2f}% ann")
    print(f"  Sharpe: {result['sharpe']:.3f}, MaxDD: {result['max_drawdown_pct']:.2f}%")
    print(f"  Hit rate: {result['hit_rate_pct']:.1f}%, Trades: {result['trade_count']}")
    print(f"  Rank IC: {result['mean_rank_ic']:.4f}, ICIR: {result['icir']:.3f}")
    print(f"  Benchmark: {result['benchmark_return_pct']:+.2f}%")
    print(f"  Excess: {result['excess_return_pct']:+.2f}%")

    return result


def main():
    print("=" * 70)
    print("Path B Production: Concept + Technical Feature Fusion for ETF Rotation")
    print("=" * 70)
    print()

    # 1. Load ETF data
    print("[1/4] Loading ETF data...")
    etf_data = load_all_etf_data()
    benchmark_df = load_benchmark_etf()
    trading_etfs = [s for s in etf_data if s not in BENCHMARK_SYMBOLS]
    print(f"  Trading ETFs: {len(trading_etfs)}, Benchmark: {'yes' if benchmark_df is not None else 'no'}")
    print()

    # 2. Build date list
    print("[2/4] Building date list...")
    from hot_sector_screener.data_sources.platform import list_available_dates
    ths_dates = sorted(list_available_dates("ths_hot"))
    etf_dates_set: set[str] = set()
    for df in etf_data.values():
        for d in df.index:
            etf_dates_set.add(d.strftime("%Y%m%d"))
    date_list = sorted(set(ths_dates) & etf_dates_set)
    print(f"  Overlap: {len(date_list)} days, {date_list[0]} ~ {date_list[-1]}")
    print()

    # 3. Run backtest comparisons
    print("[3/4] Running backtests...")

    results: dict[str, Any] = {}

    results["concept"] = run_backtest(
        "concept", date_list, etf_data, benchmark_df,
        train_window=180, step=20, top_k=3, alpha=1.0,
    )

    results["technical"] = run_backtest(
        "technical", date_list, etf_data, benchmark_df,
        train_window=180, step=20, top_k=3, alpha=1.0,
    )

    results["fusion"] = run_backtest(
        "fusion", date_list, etf_data, benchmark_df,
        train_window=180, step=20, top_k=3, alpha=1.0,
    )

    # 4. Summary
    print("\n" + "=" * 70)
    print("[4/4] COMPARISON SUMMARY")
    print("=" * 70)
    print(f"\n{'Mode':>12} {'Total':>10} {'Ann':>10} {'Sharpe':>8} {'MaxDD':>8} {'Excess':>10} {'IC':>8} {'Trades':>8}")
    print("-" * 80)

    for mode, r in results.items():
        if r is None:
            print(f"  {mode:>10} {'FAILED':>10}")
            continue
        print(f"  {mode:>10} {r['total_return_pct']:>9.2f}% {r['annual_return_pct']:>9.2f}% "
              f"{r['sharpe']:>8.3f} {r['max_drawdown_pct']:>7.2f}% "
              f"{r['excess_return_pct']:>9.2f}% {r['mean_rank_ic']:>8.4f} {r['trade_count']:>8}")

    # Winner
    valid = {m: r for m, r in results.items() if r is not None}
    if valid:
        best = max(valid, key=lambda m: valid[m]["sharpe"])
        print(f"\n  Best: {best.upper()} (Sharpe={valid[best]['sharpe']:.3f}, "
              f"Excess={valid[best]['excess_return_pct']:+.2f}%)")

    # Save best model
    if best in valid and valid[best] is not None:
        print(f"\n  Saving best model ({best}) to artifacts/")
        artifacts_dir = Path("/home/richard/code/research-workspace/artifacts")
        artifacts_dir.mkdir(exist_ok=True)

        X, y, feature_names, _ = build_feature_matrix(date_list, etf_data, mode=best)
        if not X.empty:
            model = LinearRankModel(alpha=1.0)
            model.fit(X.values, y.values, feature_names)
            model_path = artifacts_dir / f"concept_etf_model_{best}.json"
            model_path.write_text(json.dumps(model.to_dict(), indent=2))
            print(f"  Model saved to {model_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
