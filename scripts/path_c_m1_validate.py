#!/usr/bin/env python3
# pyright: basic
"""
Path C M1: Hypothesis validation for concept-level ML ranking.

Tests four hypotheses (H1-H4) that must pass before committing to Path C:
  H1: Concepts with more consecutive days on the hot list have higher
      next-day constituent returns (persistence signal).
  H2: Concepts with improving hot-rank have higher next-day returns
      (rank momentum signal).
  H3: Cross-sectional features of concept constituents (median mcap,
      turnover, volatility) can differentiate concept quality.
  H4: kpl concept constituent lists are stable enough for daily ML
      (daily turnover rate < 5%).

Usage:
    cd ~/code/hot-sector-screener
    DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform \
    uv run python /home/richard/code/research-workspace/scripts/path_c_m1_validate.py
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

# ── Paths ──
HOT_SCREENER_ROOT = Path(os.environ.get(
    "HOT_SCREENER_ROOT", "/home/richard/code/hot-sector-screener"
))
DATA_PLATFORM_ROOT = Path(os.environ.get(
    "DATA_PLATFORM_ROOT", "/home/richard/data/market-data-platform"
))

sys.path.insert(0, str(HOT_SCREENER_ROOT / "src"))


# ═══════════════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════════════

def load_ths_hot(trade_date: str) -> pd.DataFrame:
    from hot_sector_screener.data_sources.platform import (
        list_available_dates,
        load_ths_hot as _load,
    )
    return _load(trade_date, limit=200)


def load_kpl(trade_date: str) -> pd.DataFrame:
    from hot_sector_screener.data_sources.platform import load_kpl_concept_cons
    return load_kpl_concept_cons(trade_date)


def load_daily(trade_date: str) -> pd.DataFrame:
    from hot_sector_screener.data_sources.platform import load_daily_data
    return load_daily_data(trade_date)


def list_ths_dates() -> list[str]:
    from hot_sector_screener.data_sources.platform import list_available_dates
    return sorted(list_available_dates("ths_hot"))


def list_kpl_dates() -> list[str]:
    from hot_sector_screener.data_sources.platform import list_available_dates
    return sorted(list_available_dates("kpl_concept_cons"))


def _fmt(date_str: str) -> str:
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"


# ═══════════════════════════════════════════════════════════════════════════
# Concept extraction
# ═══════════════════════════════════════════════════════════════════════════

def extract_concepts_from_hot(hot_df: pd.DataFrame, top_n: int = 50) -> dict[str, dict]:
    """Extract concepts with metadata from THS hot data.

    Returns:
        {concept_name: {rank: int, hot_score: float, stock_count: int}}
    """
    if hot_df.empty:
        return {}

    if "rank" in hot_df.columns:
        hot_df = hot_df.sort_values("rank").head(top_n)

    concept_stats: dict[str, dict] = {}
    for _, row in hot_df.iterrows():
        raw = str(row.get("concept", ""))
        raw = raw.strip().strip("[]").strip('"').strip("'")
        parts = re.split(r'[",，]\s*', raw)
        concepts = [p.strip().strip('"').strip("'") for p in parts if p.strip() and p not in ("", "[", "]")]

        rank = int(row.get("rank", 999))
        hot_score = float(row.get("hot_score", 0))

        for c in concepts:
            if c not in concept_stats:
                concept_stats[c] = {"min_rank": rank, "total_hot_score": 0.0, "stock_count": 0}
            concept_stats[c]["min_rank"] = min(concept_stats[c]["min_rank"], rank)
            concept_stats[c]["total_hot_score"] += hot_score
            concept_stats[c]["stock_count"] += 1

    return concept_stats


# ═══════════════════════════════════════════════════════════════════════════
# Concept → stock mapping
# ═══════════════════════════════════════════════════════════════════════════

def map_concept_to_stocks(concept_name: str, kpl_df: pd.DataFrame) -> list[str]:
    """Map a concept name to its constituent stock codes."""
    if kpl_df.empty:
        return []

    # Build lookup: concept_code → set of stock_codes
    concept_to_stocks: dict[str, set[str]] = {}
    concept_names: dict[str, str] = {}
    for _, row in kpl_df.iterrows():
        cc = str(row.get("ts_code", "")).strip()
        sc = str(row.get("con_code", "")).strip()
        cn = str(row.get("name", "")).strip()
        if cc and sc:
            concept_to_stocks.setdefault(cc, set()).add(sc)
        if cc and cn:
            concept_names[cc] = cn

    candidates: list[str] = []
    cn_lower = concept_name.lower()
    for cc, cn in concept_names.items():
        if cn_lower in cn.lower() or cn.lower() in cn_lower:
            candidates.extend(concept_to_stocks.get(cc, set()))

    if not candidates:
        desc_match = kpl_df[kpl_df["desc"].str.contains(
            re.escape(concept_name), case=False, na=False
        )]
        if not desc_match.empty:
            candidates = list(dict.fromkeys(desc_match["con_code"].astype(str).tolist()))

    return list(dict.fromkeys(candidates))


# ═══════════════════════════════════════════════════════════════════════════
# H1: Consecutive days on hot list → forward returns
# ═══════════════════════════════════════════════════════════════════════════

def test_h1_consecutive_days(
    ths_dates: list[str],
    kpl_dates: set[str],
    lookback: int = 5,
    sample_every: int = 3,
    max_samples: int = 120,
) -> dict[str, Any]:
    """H1: Test if concepts with longer streaks on the hot list have better forward returns.

    For each date, compute how many consecutive prior days each concept appeared.
    Then group by streak length and compute next-day constituent returns.
    """
    print("=" * 70)
    print("H1: Consecutive days on hot list → forward constituent returns")
    print("=" * 70)

    # Track concept appearance history
    concept_history: dict[str, list[str]] = defaultdict(list)  # concept → list of dates

    streak_returns: dict[int, list[float]] = defaultdict(list)
    streak_counts: dict[int, int] = defaultdict(int)

    # Sample dates for performance (daily data loads are expensive: ~3s per date)
    sampled_dates = [d for i, d in enumerate(ths_dates) if i % sample_every == 0][:max_samples]
    # Further limit to kpl overlap
    sampled_dates = [d for d in sampled_dates if d in kpl_dates]
    print(f"  Processing {len(sampled_dates)} dates (sample_every={sample_every}, max={max_samples})...")

    processed = 0
    for d in sampled_dates:
        if d not in kpl_dates:
            continue
        # Find original index in full date list
        i = ths_dates.index(d)
        if i + 2 >= len(ths_dates):
            continue

        hot = load_ths_hot(_fmt(d))
        if hot.empty:
            continue

        concepts = extract_concepts_from_hot(hot, top_n=30)
        concept_names = set(concepts.keys())

        # Load constituent returns
        kpl = load_kpl(d)
        if kpl.empty:
            continue

        # Next-day entry, day-after exit
        entry_date = _fmt(ths_dates[i + 1])
        exit_date = _fmt(ths_dates[i + 2])
        entry_df = load_daily(entry_date)
        exit_df = load_daily(exit_date)
        if entry_df.empty or exit_df.empty:
            continue

        for cn in concept_names:
            stocks = map_concept_to_stocks(cn, kpl)
            if len(stocks) < 3:
                continue

            # Compute equal-weight forward return
            entry_px = entry_df[entry_df["ts_code"].isin(stocks)].set_index("ts_code")["open"].astype(float)
            exit_px = exit_df[exit_df["ts_code"].isin(stocks)].set_index("ts_code")["open"].astype(float)
            common = entry_px.index.intersection(exit_px.index)
            if len(common) < 3:
                continue

            fwd_ret = float((exit_px[common] / entry_px[common] - 1).mean())

            # Count appearances in last N trading days (simpler than consecutive streak for sampled data)
            hist = concept_history.get(cn, [])
            # Check how many of the last `lookback` trading days this concept appeared on
            recent_dates = ths_dates[max(0, i - lookback):i]
            appearance_count = sum(1 for past_d in hist if past_d in recent_dates)
            streak = min(appearance_count + 1, lookback)  # +1 for today

            streak_returns[min(streak, lookback)].append(fwd_ret)
            streak_counts[min(streak, lookback)] += 1

        processed += 1
        if processed % 20 == 0:
            print(f"    ... {processed}/{len(sampled_dates)} dates, streak obs: {sum(streak_counts.values())}")

        # Update history
        for cn in concept_names:
            concept_history[cn].append(d)
            if len(concept_history[cn]) > 30:
                concept_history[cn] = concept_history[cn][-30:]

    # Results
    print(f"\n  Concept observations: {sum(streak_counts.values())}")
    print(f"\n  {'Streak':>8} {'Count':>8} {'Mean Ret':>10} {'Std':>8} {'T-stat':>8} {'Annual':>10}")
    print(f"  {'-'*8} {'-'*8} {'-'*10} {'-'*8} {'-'*8} {'-'*10}")

    results = []
    for streak in sorted(streak_returns.keys()):
        rets = streak_returns[streak]
        if len(rets) < 20:
            continue
        mean = np.mean(rets)
        std = np.std(rets)
        tstat = mean / (std / np.sqrt(len(rets))) if std > 0 else 0
        ann = (1 + mean) ** 252 - 1
        n = len(rets)
        print(f"  {streak:>8} {n:>8} {mean*100:>9.2f}% {std*100:>7.2f}% {tstat:>8.2f} {ann*100:>9.2f}%")
        results.append({"streak": streak, "count": n, "mean_ret": mean, "std": std, "t_stat": tstat, "annual": ann})

    # Test: does streak ≥ 3 outperform streak = 1?
    rets_1 = streak_returns.get(1, [])
    rets_3plus = []
    for s in sorted(streak_returns.keys()):
        if s >= 3:
            rets_3plus.extend(streak_returns[s])

    if len(rets_1) >= 20 and len(rets_3plus) >= 20:
        t_stat, p_value = stats.ttest_ind(rets_3plus, rets_1, equal_var=False)
        print(f"\n  streak>=3 vs streak=1: t={t_stat:.3f}, p={p_value:.4f}")
        passed = t_stat > 0 and p_value < 0.05
    else:
        passed = False
        print(f"\n  Insufficient data for comparison")

    print(f"  H1 PASS: {passed}")

    return {"hypothesis": "H1", "passed": passed, "results": results}


# ═══════════════════════════════════════════════════════════════════════════
# H2: Rank momentum → forward returns
# ═══════════════════════════════════════════════════════════════════════════

def test_h2_rank_momentum(
    ths_dates: list[str],
    kpl_dates: set[str],
    sample_every: int = 3,
    max_samples: int = 120,
) -> dict[str, Any]:
    """H2: Test if concepts with improving hot-rank have better forward returns.

    Rank momentum = yesterday's min_rank - today's min_rank (positive = improving).
    """
    print("\n" + "=" * 70)
    print("H2: Rank momentum → forward constituent returns")
    print("=" * 70)

    prev_concepts: dict[str, int] = {}  # concept → min_rank
    all_momentums: list[float] = []
    all_returns: list[float] = []

    sampled_dates = [d for i, d in enumerate(ths_dates) if i % sample_every == 0][:max_samples]
    print(f"  Processing {len(sampled_dates)} dates...")

    for d in sampled_dates:
        if d not in kpl_dates:
            prev_concepts = {}
            continue
        i = ths_dates.index(d)
        if i + 2 >= len(ths_dates):
            continue

        hot = load_ths_hot(_fmt(d))
        if hot.empty:
            prev_concepts = {}
            continue

        concepts = extract_concepts_from_hot(hot, top_n=30)

        kpl = load_kpl(d)
        if kpl.empty:
            prev_concepts = {}
            continue

        entry_date = _fmt(ths_dates[i + 1])
        exit_date = _fmt(ths_dates[i + 2])
        entry_df = load_daily(entry_date)
        exit_df = load_daily(exit_date)
        if entry_df.empty or exit_df.empty:
            prev_concepts = {}
            continue

        today_concepts: dict[str, int] = {}
        for cn, cstats in concepts.items():
            today_concepts[cn] = cstats["min_rank"]

            # Compute rank momentum
            prev_rank = prev_concepts.get(cn)
            if prev_rank is not None:
                momentum = prev_rank - cstats["min_rank"]  # +ve = improving
                stocks = map_concept_to_stocks(cn, kpl)
                if len(stocks) < 3:
                    continue

                entry_px = entry_df[entry_df["ts_code"].isin(stocks)].set_index("ts_code")["open"].astype(float)
                exit_px = exit_df[exit_df["ts_code"].isin(stocks)].set_index("ts_code")["open"].astype(float)
                common = entry_px.index.intersection(exit_px.index)
                if len(common) < 3:
                    continue

                fwd_ret = float((exit_px[common] / entry_px[common] - 1).mean())
                all_momentums.append(momentum)
                all_returns.append(fwd_ret)

        prev_concepts = today_concepts

    print(f"\n  Observations: {len(all_momentums)}")

    if len(all_momentums) >= 50:
        corr, p_value = stats.spearmanr(all_momentums, all_returns)
        print(f"  Spearman rank correlation: {corr:.4f} (p={p_value:.4f})")

        # Group by momentum quintile
        df = pd.DataFrame({"momentum": all_momentums, "return": all_returns})
        df["quintile"] = pd.qcut(df["momentum"], 5, labels=False, duplicates="drop")

        print(f"\n  {'Quintile':>10} {'Count':>8} {'Mean Ret':>10} {'Annual':>10}")
        print(f"  {'-'*10} {'-'*8} {'-'*10} {'-'*10}")
        for q in sorted(df["quintile"].unique()):
            subset = df[df["quintile"] == q]
            mean = subset["return"].mean()
            ann = (1 + mean) ** 252 - 1
            print(f"  {q:>10} {len(subset):>8} {mean*100:>9.2f}% {ann*100:>9.2f}%")

        top = df[df["quintile"] == df["quintile"].max()]["return"]
        bot = df[df["quintile"] == df["quintile"].min()]["return"]
        spread = top.mean() - bot.mean()
        print(f"\n  Top-Bottom quintile spread: {spread*100:.3f}% per day")

        passed = corr > 0.02 and p_value < 0.10
    else:
        corr, p_value = 0, 1
        passed = False

    print(f"  H2 PASS: {passed} (threshold: rank IC > 0.02, p < 0.10)")

    return {
        "hypothesis": "H2",
        "passed": passed,
        "rank_ic": corr,
        "p_value": p_value,
        "n": len(all_momentums),
    }


# ═══════════════════════════════════════════════════════════════════════════
# H3: Constituent cross-sectional features → forward returns
# ═══════════════════════════════════════════════════════════════════════════

def test_h3_constituent_features(
    ths_dates: list[str],
    kpl_dates: set[str],
) -> dict[str, Any]:
    """H3: Test if concept constituent cross-sectional features predict returns.

    Features: median market cap, median turnover rate, median volatility.
    """
    print("\n" + "=" * 70)
    print("H3: Constituent cross-sectional features → forward returns")
    print("=" * 70)

    feature_ics: dict[str, list[float]] = {
        "median_mcap": [],
        "median_turnover": [],
        "median_volatility": [],
    }

    for i, d in enumerate(ths_dates[:50]):  # Sample first 50 days for speed
        if d not in kpl_dates:
            continue
        if i + 2 >= len(ths_dates):
            continue

        hot = load_ths_hot(_fmt(d))
        if hot.empty:
            continue

        concepts = extract_concepts_from_hot(hot, top_n=30)
        kpl = load_kpl(d)
        if kpl.empty:
            continue

        entry_date = _fmt(ths_dates[i + 1])
        exit_date = _fmt(ths_dates[i + 2])
        entry_df = load_daily(entry_date)
        exit_df = load_daily(exit_date)
        if entry_df.empty or exit_df.empty:
            continue

        concept_features: dict[str, dict[str, float]] = {}
        concept_returns: dict[str, float] = {}

        for cn in list(concepts.keys()):
            stocks = map_concept_to_stocks(cn, kpl)
            if len(stocks) < 5:
                continue

            # Get constituent daily data
            entry_sub = entry_df[entry_df["ts_code"].isin(stocks)]
            if entry_sub.empty or len(entry_sub) < 5:
                continue

            # Constituent features
            amounts = entry_sub["amount"].astype(float).dropna()
            turnovers = entry_sub["turnover_rate"].astype(float).dropna() if "turnover_rate" in entry_sub.columns else pd.Series(dtype=float)
            pct_chgs = entry_sub["pct_chg"].astype(float).dropna()

            concept_features[cn] = {
                "median_mcap": np.log1p(amounts.median()) if not amounts.empty else 0,
                "median_turnover": turnovers.median() if not turnovers.empty else 0,
                "median_volatility": pct_chgs.std() if len(pct_chgs) > 1 else 0,
            }

            # Forward return
            exit_px = exit_df[exit_df["ts_code"].isin(stocks)].set_index("ts_code")["open"].astype(float)
            entry_px = entry_sub.set_index("ts_code")["open"].astype(float)
            common = entry_px.index.intersection(exit_px.index)
            if len(common) >= 5:
                concept_returns[cn] = float((exit_px[common] / entry_px[common] - 1).mean())

        # Compute cross-sectional rank IC for each feature
        if len(concept_features) >= 10 and len(concept_returns) >= 10:
            common_cn = set(concept_features) & set(concept_returns)
            for feat in feature_ics:
                feat_vals = [concept_features[cn][feat] for cn in common_cn]
                ret_vals = [concept_returns[cn] for cn in common_cn]
                if len(set(feat_vals)) > 1:
                    ic, _ = stats.spearmanr(feat_vals, ret_vals)
                    feature_ics[feat].append(ic)

    print(f"\n  Sampled {len(ths_dates[:50])} dates")
    for feat, ics in feature_ics.items():
        if ics:
            mean_ic = np.mean(ics)
            t_stat = np.mean(ics) / (np.std(ics) / np.sqrt(len(ics))) if np.std(ics) > 0 else 0
            print(f"  {feat:>20}: mean IC={mean_ic:.4f}, t={t_stat:.2f}, n={len(ics)}")
        else:
            print(f"  {feat:>20}: no data")

    # Best feature
    best_feat = max(feature_ics, key=lambda f: np.mean(feature_ics[f]) if feature_ics[f] else 0)
    best_mean_ic = np.mean(feature_ics[best_feat]) if feature_ics[best_feat] else 0
    passed = best_mean_ic > 0.02

    print(f"\n  Best feature: {best_feat} (mean IC={best_mean_ic:.4f})")
    print(f"  H3 PASS: {passed} (threshold: any feature mean rank IC > 0.02)")

    return {
        "hypothesis": "H3",
        "passed": passed,
        "feature_ics": {f: float(np.mean(ics)) if ics else 0 for f, ics in feature_ics.items()},
    }


# ═══════════════════════════════════════════════════════════════════════════
# H4: kpl constituent list stability
# ═══════════════════════════════════════════════════════════════════════════

def test_h4_kpl_stability(kpl_dates: list[str]) -> dict[str, Any]:
    """H4: Test if kpl concept constituent lists are stable day-over-day.

    Computes Jaccard similarity for the top 30 concepts between consecutive days.
    """
    print("\n" + "=" * 70)
    print("H4: kpl concept constituent list stability")
    print("=" * 70)

    # Get concept stock sets for consecutive dates
    daily_stocks: dict[str, dict[str, set[str]]] = {}

    for d in kpl_dates[:60]:  # First 60 kpl dates
        kpl = load_kpl(d)
        if kpl.empty:
            continue

        concept_stocks: dict[str, set[str]] = {}
        for _, row in kpl.iterrows():
            cn = str(row.get("name", "")).strip()
            sc = str(row.get("con_code", "")).strip()
            if cn and sc:
                concept_stocks.setdefault(cn, set()).add(sc)

        daily_stocks[d] = concept_stocks

    # Compute daily overlap for common concepts
    sorted_dates = sorted(daily_stocks.keys())
    jaccards: list[float] = []
    turnover_rates: list[float] = []

    for i in range(len(sorted_dates) - 1):
        d1, d2 = sorted_dates[i], sorted_dates[i + 1]
        stocks1, stocks2 = daily_stocks[d1], daily_stocks[d2]

        common_concepts = set(stocks1) & set(stocks2)
        if not common_concepts:
            continue

        for cn in common_concepts:
            s1, s2 = stocks1[cn], stocks2[cn]
            if not s1 or not s2:
                continue
            intersection = s1 & s2
            union = s1 | s2
            if union:
                jaccard = len(intersection) / len(union)
                jaccards.append(jaccard)
                turnover = 1 - jaccard
                turnover_rates.append(turnover)

    mean_jaccard = np.mean(jaccards) if jaccards else 0
    mean_turnover = np.mean(turnover_rates) if turnover_rates else 0

    print(f"\n  Concept-day observations: {len(jaccards)}")
    print(f"  Mean Jaccard similarity: {mean_jaccard:.4f}")
    print(f"  Mean turnover rate: {mean_turnover*100:.2f}% per day")
    print(f"  Percentile distribution:")
    for pct in [5, 25, 50, 75, 95]:
        val = np.percentile(turnover_rates, pct) * 100 if turnover_rates else 0
        print(f"    P{pct}: {val:.2f}%")

    passed = mean_turnover < 0.05

    print(f"\n  H4 PASS: {passed} (threshold: mean daily turnover < 5%)")

    return {
        "hypothesis": "H4",
        "passed": passed,
        "mean_jaccard": float(mean_jaccard),
        "mean_turnover_pct": float(mean_turnover * 100),
        "n": len(jaccards),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("Path C M1: Hypothesis Validation for Concept-Level ML Ranking")
    print()

    ths_dates = list_ths_dates()
    kpl_dates = list_kpl_dates()
    kpl_set = set(kpl_dates)
    overlap = sorted(set(ths_dates) & kpl_set)

    print(f"ths_hot: {len(ths_dates)} days, {ths_dates[0]} ~ {ths_dates[-1]}")
    print(f"kpl_concept_cons: {len(kpl_dates)} days, {kpl_dates[0]} ~ {kpl_dates[-1]}")
    print(f"Overlap: {len(overlap)} days")
    print()

    results = []

    # H1 - use aggressive sampling: every 10th date, max 40 dates
    r1 = test_h1_consecutive_days(ths_dates, kpl_set, sample_every=10, max_samples=40)
    results.append(r1)

    # H2 - same sampling
    r2 = test_h2_rank_momentum(ths_dates, kpl_set, sample_every=10, max_samples=40)
    results.append(r2)

    # H3 - even fewer: 20 dates
    r3 = test_h3_constituent_features(ths_dates[:200], kpl_set)  # already limited to 50 in function
    results.append(r3)

    # H4
    r4 = test_h4_kpl_stability(sorted(kpl_dates))
    results.append(r4)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  {r['hypothesis']}: {status}")

    all_pass = all(r["passed"] for r in results)
    print(f"\n  ALL PASS: {all_pass}")
    if all_pass:
        print("  → Path C is viable. Proceed to M2 (data engineering).")
    else:
        failed = [r["hypothesis"] for r in results if not r["passed"]]
        print(f"  → Path C BLOCKED. Failed hypotheses: {', '.join(failed)}")
        print("  → Do NOT invest further time in concept-level ML until these pass.")


if __name__ == "__main__":
    main()
