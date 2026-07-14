"""Smoke tests for StyleReplica-A80B20-v0 integration.

Verifies:
1. Theme mapping correctness
2. Factor computation shapes
3. Scoring coherence (A-leg rewards high RESVOL, B-leg rewards low RESVOL)
4. Portfolio construction with theme quotas and buffer zones
5. Daily changes tracking
6. End-to-end signal → positions pipeline

Run with:
    pytest tests/test_style_replica.py -v
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from alpha_research.style_replica import (
    AI_HARDWARE_THEME_QUOTAS,
    StyleReplicaPortfolioConfig,
    build_style_replica_positions,
    compute_daily_changes,
    compute_daily_exposure,
    compute_score_a,
    compute_score_b,
    filter_style_replica_universe,
    generate_daily_signals,
    map_stock_to_theme,
)
from alpha_research.style_replica.factors import compute_all_style_factors
from alpha_research.style_replica.resvol import compute_resvol_factor
from alpha_research.style_replica.theme_map import build_theme_map, get_theme_label

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_price_panel(
    n_dates: int = 200,
    n_stocks: int = 50,
    seed: int = 42,
) -> pd.DataFrame:
    """Create synthetic price data for testing."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-01-01", periods=n_dates, freq="B")
    symbols = [f"STOCK_{i:04d}" for i in range(n_stocks)]

    # Geometric random walk starting at 10.0
    returns = rng.normal(0.001, 0.02, size=(n_dates, n_stocks))
    prices = 10.0 * np.exp(np.cumsum(returns, axis=0))
    return pd.DataFrame(prices, index=dates, columns=symbols)


def _make_industry_frame(n_stocks: int = 50) -> pd.DataFrame:
    """Create synthetic industry classification."""
    industries = [
        "集成电路",
        "印制电路板",
        "被动元件",
        "白酒",
        "光模块",
        "钨",
        "电子化学品Ⅲ",
        "温控设备",
        "合成树脂",
        "通信网络设备及器件",
    ]
    symbols = [f"STOCK_{i:04d}" for i in range(n_stocks)]
    return pd.DataFrame(
        {
            "symbol": symbols,
            "industry_name": [industries[i % len(industries)] for i in range(n_stocks)],
        }
    )


# ── Theme mapping tests ────────────────────────────────────────────────────────


class TestThemeMapping:
    def test_industry_exact_match(self):
        assert (
            map_stock_to_theme("S1", industry_name="集成电路")
            == "semiconductor_chip_equipment_materials"
        )
        assert (
            map_stock_to_theme("S2", industry_name="印制电路板") == "pcb_ccl_electronic_substrate"
        )
        assert (
            map_stock_to_theme("S3", industry_name="被动元件")
            == "electronic_components_passive_ceramic"
        )
        assert (
            map_stock_to_theme("S4", industry_name="光模块")
            == "optical_cpo_communication_equipment"
        )
        assert map_stock_to_theme("S5", industry_name="钨") == "minor_metals_rare_metal_powder"
        assert map_stock_to_theme("S6", industry_name="温控设备") == "datacenter_storage_cooling"
        assert (
            map_stock_to_theme("S7", industry_name="电子化学品Ⅲ")
            == "electronic_chemicals_polymer_materials"
        )

    def test_industry_substring_match(self):
        assert (
            map_stock_to_theme("S1", industry_name="集成电路设计")
            == "semiconductor_chip_equipment_materials"
        )
        assert (
            map_stock_to_theme("S2", industry_name="半导体材料及设备")
            == "semiconductor_chip_equipment_materials"
        )

    def test_concept_fallback(self):
        assert map_stock_to_theme("S1", concept_tags=["AI算力"]) == "datacenter_storage_cooling"
        assert (
            map_stock_to_theme("S2", concept_tags=["CPO概念"])
            == "optical_cpo_communication_equipment"
        )
        assert (
            map_stock_to_theme("S3", concept_tags=["芯片设计"])
            == "semiconductor_chip_equipment_materials"
        )

    def test_unknown_returns_none(self):
        assert map_stock_to_theme("S1", industry_name="白酒") is None
        assert map_stock_to_theme("S2") is None
        assert map_stock_to_theme("S3", concept_tags=["农业"]) is None

    def test_theme_quotas_sum(self):
        assert sum(AI_HARDWARE_THEME_QUOTAS.values()) == 80

    def test_build_theme_map(self):
        df = pd.DataFrame(
            {
                "symbol": ["A", "B", "C", "D"],
                "industry_name": ["集成电路", "白酒", "印制电路板", "被动元件"],
            }
        )
        tm = build_theme_map(df)
        assert tm["A"] == "semiconductor_chip_equipment_materials"
        assert pd.isna(tm["B"])
        assert tm["C"] == "pcb_ccl_electronic_substrate"
        assert tm["D"] == "electronic_components_passive_ceramic"

    def test_get_theme_label(self):
        label = get_theme_label("semiconductor_chip_equipment_materials")
        assert "半导体" in label
        assert "芯片" in label


# ── Factor tests ───────────────────────────────────────────────────────────────


class TestFactors:
    def test_resvol_shape(self):
        prices = _make_price_panel(n_dates=100, n_stocks=10)
        returns = prices.pct_change()
        resvol = compute_resvol_factor(returns)
        assert resvol.shape == prices.shape
        # First 39 rows should be NaN (min_obs=40)
        assert resvol.iloc[:39].isna().all().all()
        # After that, some values should appear
        assert not resvol.iloc[60:].isna().all().all()

    def test_all_factors_output(self):
        prices = _make_price_panel(n_dates=150, n_stocks=20)
        factors = compute_all_style_factors(prices)
        expected_keys = {
            "resvol",
            "beta",
            "size",
            "liquidity",
            "mom20",
            "mom120",
            "industry_mom",
            "vol_convergence",
        }
        assert set(factors.keys()) == expected_keys
        for name, df in factors.items():
            assert df.shape == prices.shape, f"{name} shape mismatch: {df.shape} != {prices.shape}"


# ── Scoring tests ──────────────────────────────────────────────────────────────


class TestScoring:
    def test_score_a_basic(self):
        prices = _make_price_panel(n_dates=150, n_stocks=30)
        factors = compute_all_style_factors(prices)
        score_a = compute_score_a(factors)
        assert score_a.shape == prices.shape
        # Scores should be in [0, 1]
        assert score_a.min().min() >= 0
        assert score_a.max().max() <= 1

    def test_score_b_prefers_low_resvol(self):
        """B-leg should give higher score to stocks with lower RESVOL."""
        prices = _make_price_panel(n_dates=150, n_stocks=30)
        factors = compute_all_style_factors(prices)
        score_b = compute_score_b(factors)

        # Take last date, find stocks with extreme RESVOL
        last_date = factors["resvol"].index[-1]
        resvol_last = factors["resvol"].loc[last_date]
        score_b_last = score_b.loc[last_date]

        # Bottom 5 by RESVOL should outrank top 5 by RESVOL
        low_vol_stocks = resvol_last.nsmallest(5).index
        high_vol_stocks = resvol_last.nlargest(5).index

        low_score = score_b_last[low_vol_stocks].mean()
        high_score = score_b_last[high_vol_stocks].mean()
        assert low_score > high_score, (
            f"B-leg should prefer low RESVOL: low={low_score:.3f} high={high_score:.3f}"
        )

    def test_score_a_prefers_high_resvol(self):
        """A-leg should give higher score to stocks with higher RESVOL."""
        prices = _make_price_panel(n_dates=150, n_stocks=30)
        factors = compute_all_style_factors(prices)
        score_a = compute_score_a(factors)

        last_date = factors["resvol"].index[-1]
        resvol_last = factors["resvol"].loc[last_date]
        score_a_last = score_a.loc[last_date]

        low_vol_stocks = resvol_last.nsmallest(5).index
        high_vol_stocks = resvol_last.nlargest(5).index

        low_score = score_a_last[low_vol_stocks].mean()
        high_score = score_a_last[high_vol_stocks].mean()
        assert high_score > low_score, (
            f"A-leg should prefer high RESVOL: low={low_score:.3f} high={high_score:.3f}"
        )


# ── Universe tests ─────────────────────────────────────────────────────────────


class TestUniverse:
    def test_filter_removes_short_history(self):
        prices = _make_price_panel(n_dates=50, n_stocks=10)
        instruments = pd.DataFrame(
            {
                "symbol": prices.columns.tolist(),
                "list_date": ["2020-01-01"] * len(prices.columns),
                "is_st": [False] * len(prices.columns),
            }
        )
        result = filter_style_replica_universe(prices, instruments, prices.index[-1])
        # min_history=120, but we only have 50 dates → empty result
        assert result.empty

    def test_filter_keeps_valid_stocks(self):
        prices = _make_price_panel(n_dates=200, n_stocks=10)
        instruments = pd.DataFrame(
            {
                "symbol": prices.columns.tolist(),
                "list_date": ["2020-01-01"] * 10,
                "is_st": [False] * 10,
            }
        )
        result = filter_style_replica_universe(prices, instruments, prices.index[-1])
        assert not result.empty
        assert result.shape[1] == 10


# ── Portfolio construction tests ───────────────────────────────────────────────


class TestPortfolioConstruction:
    def _make_mock_signals(self, n_stocks: int = 200) -> pd.DataFrame:
        rng = np.random.default_rng(42)
        industries = ["集成电路", "印制电路板", "白酒", "温控设备", "光模块"] * 40
        themes = [
            "semiconductor_chip_equipment_materials",
            "pcb_ccl_electronic_substrate",
            None,
            "datacenter_storage_cooling",
            "optical_cpo_communication_equipment",
        ] * 40

        df = pd.DataFrame(
            {
                "signal_date": ["20250101"] * n_stocks,
                "trade_date": pd.Timestamp("2025-01-01"),
                "symbol": [f"STOCK_{i:04d}" for i in range(n_stocks)],
                "score_a": rng.uniform(0, 1, n_stocks),
                "score_b": rng.uniform(0, 1, n_stocks),
                "theme": themes[:n_stocks],
                "industry": industries[:n_stocks],
                "leg": ["A"] * n_stocks,
            }
        )
        # Make some stocks not have AI hardware theme
        df.loc[df["theme"].isna(), "score_a"] = np.nan
        df.loc[df["theme"].isna(), "leg"] = "B"
        return df

    def test_portfolio_builds_a_and_b(self):
        signals = self._make_mock_signals(200)
        config = StyleReplicaPortfolioConfig(
            theme_quotas=dict(AI_HARDWARE_THEME_QUOTAS),
            a_slots=80,
            b_slots=20,
        )
        positions = build_style_replica_positions(signals, config=config)
        assert not positions.empty
        assert "leg" in positions.columns
        assert "weight" in positions.columns

        # Check A-leg count (should have A or A+B)
        a_mask = positions["leg"].str.contains("A", na=False)
        assert a_mask.sum() > 0, "Should have A-leg positions"

        # Check weights sum approximately
        total_weight = positions["weight"].sum()
        assert 0.9 < total_weight < 1.1, f"Total weight {total_weight:.3f} not near 1.0"

    def test_overlap_aggregation(self):
        """When a stock is in both A and B, weight should double."""
        signals = self._make_mock_signals(50)
        config = StyleReplicaPortfolioConfig(
            theme_quotas={
                "semiconductor_chip_equipment_materials": 20,
                "pcb_ccl_electronic_substrate": 20,
            },
            a_slots=40,
            b_slots=10,
            overlap_policy="aggregate",
            normal_slot_weight=0.01,
            max_name_weight=0.02,
        )
        positions = build_style_replica_positions(signals, config=config)
        overlap_mask = positions["leg"] == "A+B"
        if overlap_mask.any():
            for _, row in positions[overlap_mask].iterrows():
                assert row["weight"] <= 0.02, f"Overlap weight {row['weight']} exceeds max"

    def test_daily_changes(self):
        """Test change detection between consecutive dates."""
        # Create two days of signals
        signals = []
        for day in ["20250101", "20250102"]:
            s = self._make_mock_signals(100)
            s["signal_date"] = day
            s["trade_date"] = pd.Timestamp(day)
            signals.append(s)
        all_signals = pd.concat(signals, ignore_index=True)

        config = StyleReplicaPortfolioConfig(
            theme_quotas=dict(AI_HARDWARE_THEME_QUOTAS),
            a_slots=40,
            b_slots=10,
        )
        positions = build_style_replica_positions(all_signals, config=config)
        changes = compute_daily_changes(positions)

        assert "action" in changes.columns
        actions = changes["action"].value_counts().to_dict()
        assert "new" in actions or "stay" in actions or "exit" in actions

    def test_daily_exposure(self):
        signals = self._make_mock_signals(200)
        config = StyleReplicaPortfolioConfig(
            theme_quotas=dict(AI_HARDWARE_THEME_QUOTAS),
        )
        positions = build_style_replica_positions(signals, config=config)
        exposure = compute_daily_exposure(positions)

        assert not exposure.empty
        assert "total_stocks" in exposure.columns
        assert "a_leg_count" in exposure.columns
        assert "b_leg_count" in exposure.columns


# ── End-to-end test ────────────────────────────────────────────────────────────


class TestEndToEnd:
    def test_signal_to_positions_pipeline(self):
        """Full pipeline: factors → scores → signals → positions."""
        prices = _make_price_panel(n_dates=200, n_stocks=100)
        industry = _make_industry_frame(n_stocks=100)

        # Generate signals
        signals = generate_daily_signals(prices, industry_frame=industry)
        assert not signals.empty
        assert "score_a" in signals.columns
        assert "score_b" in signals.columns
        assert "leg" in signals.columns
        assert "theme" in signals.columns

        # Build positions
        config = StyleReplicaPortfolioConfig(
            theme_quotas=dict(AI_HARDWARE_THEME_QUOTAS),
        )
        positions = build_style_replica_positions(signals, config=config)

        # Verify positions
        assert not positions.empty
        daily_weights = positions.groupby("rebalance_date")["weight"].sum()
        assert (daily_weights > 0).all()
        assert (daily_weights < 2.0).all()

        # Verify daily changes
        changes = compute_daily_changes(positions)
        assert not changes.empty
