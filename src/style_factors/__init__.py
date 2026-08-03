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
    "size": "市值因子",
    "value": "价值因子",
    "momentum": "21 日动量因子",
    "quality": "质量因子",
    "earnings_yield": "盈利收益率因子",
    "lowvol": "低波动因子",
    "growth": "成长因子",
    "leverage": "低杠杆因子",
    "beta": "低贝塔因子",
    "liquidity": "低换手因子",
    # New factors from locally-landed tushare datasets (zero network traffic):
    "liquidity_flow": "大单资金流因子",
    "chip_concentration": "筹码集中度因子",
    "institution_holding": "机构持仓因子",
    "dividend_yield": "股息率因子",
    "ps_value": "市销率价值因子",
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
