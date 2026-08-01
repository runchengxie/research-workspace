"""A-share style-factor proxy analysis with 15 candidate factors.

Size, Value, Momentum, Quality (composite), Earnings Yield, LowVol, Growth,
Leverage, Beta, Liquidity.

``factor_quality`` is now a composite operating-quality score (ROE, low
leverage, earnings stability, cashflow quality).  Earnings yield (1/PE_TTM)
lives in the value group as ``factor_earnings_yield``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.font_manager as fm

matplotlib.use("Agg")


def _font_properties() -> fm.FontProperties:
    font_path = Path("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc")
    if font_path.is_file():
        return fm.FontProperties(fname=str(font_path))
    return fm.FontProperties()


# CJK font & dark theme
CJK = _font_properties()
BG, FG, LG = "#1a1a2e", "#e0e0e0", "#333"
matplotlib.rcParams.update(
    {
        "figure.facecolor": BG,
        "axes.facecolor": BG,
        "axes.edgecolor": LG,
        "axes.labelcolor": FG,
        "text.color": FG,
        "xtick.color": "#999",
        "ytick.color": "#999",
    }
)

FACTOR_LABELS = {
    "size": "Size 大市值",
    "value": "Value 低估值",
    "momentum": "Momentum 动量",
    "quality": "Quality 复合质量",
    "earnings_yield": "Earnings Yield 盈利估值",
    "lowvol": "LowVol 低波动",
    "growth": "Growth 成长",
    "leverage": "Leverage 低杠杆",
    "beta": "Beta 低贝塔",
    "liquidity": "Liquidity 低换手",
    # New factors from locally-landed tushare datasets (zero network traffic):
    "liquidity_flow": "LiquidityFlow 大单资金流",
    "chip_concentration": "ChipConcentration 筹码集中度",
    "institution_holding": "InstitutionHolding 机构持仓",
    "dividend_yield": "DividendYield 股息率",
    "ps_value": "PSValue 市销率价值",
}

FACTOR_ORDER = list(FACTOR_LABELS)

COLORS = [
    "#ff6b6b",  # size
    "#00d4aa",  # value
    "#ffd93d",  # momentum
    "#6c5ce7",  # quality
    "#a8e6cf",  # earnings_yield
    "#f9ca24",  # lowvol
    "#e056a0",  # growth
    "#3498db",  # leverage
    "#e67e22",  # beta
    "#2ecc71",  # liquidity
    "#ff9f43",  # liquidity_flow
    "#ee5253",  # chip_concentration
    "#48dbfb",  # institution_holding
    "#1dd1a1",  # dividend_yield
    "#f368e0",  # ps_value
]

FACTOR_COLORS = dict(zip(FACTOR_ORDER, COLORS, strict=True))
