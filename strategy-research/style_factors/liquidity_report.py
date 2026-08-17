"""Chinese report and charts for low-turnover factor diagnostics."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import BG, CJK, LG
from .liquidity_signals import liquidity_signal_labels


def _fmt_pct(value: object) -> str:
    if pd.isna(value):
        return "暂无"
    number = float(value)
    if abs(number) < 0.005:
        number = 0.0
    return f"{number:+.2f}%"


def _fmt_number(value: object, digits: int = 2) -> str:
    if pd.isna(value):
        return "暂无"
    number = float(value)
    if abs(number) < 0.5 * 10 ** (-digits):
        number = 0.0
    return f"{number:.{digits}f}"


def _fmt_ratio_pct(value: object) -> str:
    if pd.isna(value):
        return "暂无"
    return f"{float(value):.2f}%"


def _fmt_date(value: object) -> str:
    date = pd.Timestamp(value)
    return f"{date.year} 年 {date.month} 月 {date.day} 日"


def _display_summary(summary: pd.DataFrame) -> pd.DataFrame:
    labels = liquidity_signal_labels()
    display = summary.copy()
    display.insert(1, "口径", display["variant"].map(labels))
    display = display[
        [
            "口径",
            "long_short_annual_return",
            "long_annual_return",
            "long_excess_annual_return",
            "monotonicity_spearman",
            "improving_quintile_steps",
            "mean_size_correlation",
            "mean_lowvol_correlation",
            "baseline_return_correlation",
        ]
    ]
    return display.rename(
        columns={
            "long_short_annual_return": "多空年化收益",
            "long_annual_return": "低换手多头年化收益",
            "long_excess_annual_return": "多头相对样本年化收益",
            "monotonicity_spearman": "五组单调相关",
            "improving_quintile_steps": "相邻改善步数",
            "mean_size_correlation": "与市值平均相关",
            "mean_lowvol_correlation": "与低波动平均相关",
            "baseline_return_correlation": "与单日口径收益相关",
        }
    )


def _display_quintiles(summary: pd.DataFrame) -> pd.DataFrame:
    labels = liquidity_signal_labels()
    display = summary.copy()
    display.insert(1, "口径", display["variant"].map(labels))
    display = display[
        [
            "口径",
            "q1_annual_return",
            "q2_annual_return",
            "q3_annual_return",
            "q4_annual_return",
            "q5_annual_return",
        ]
    ]
    return display.rename(
        columns={
            "q1_annual_return": "第一组，高换手",
            "q2_annual_return": "第二组",
            "q3_annual_return": "第三组",
            "q4_annual_return": "第四组",
            "q5_annual_return": "第五组，低换手",
        }
    )


def _display_risk(summary: pd.DataFrame) -> pd.DataFrame:
    labels = liquidity_signal_labels()
    display = summary.copy()
    display.insert(1, "口径", display["variant"].map(labels))
    display["positive_year_pct"] = display["long_short_positive_year_ratio"] * 100
    display = display[
        [
            "口径",
            "long_short_annual_return",
            "long_short_sharpe",
            "long_short_max_drawdown",
            "positive_year_pct",
        ]
    ]
    return display.rename(
        columns={
            "long_short_annual_return": "多空年化收益",
            "long_short_sharpe": "夏普比率",
            "long_short_max_drawdown": "最大回撤",
            "positive_year_pct": "正收益年份占比",
        }
    )


def _markdown_table(frame: pd.DataFrame, percent_columns: set[str]) -> str:
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    for _index, row in frame.iterrows():
        cells = []
        for column in headers:
            value = row[column]
            if column in percent_columns:
                cells.append(_fmt_pct(value))
            elif column == "正收益年份占比":
                cells.append(_fmt_ratio_pct(value))
            elif column == "相邻改善步数" and pd.notna(value):
                cells.append(str(int(value)))
            elif isinstance(value, int | float | np.number) and not isinstance(value, bool):
                cells.append(_fmt_number(value))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def plot_liquidity_signal_nav(
    portfolios: dict[str, dict[str, object]],
    outdir: Path,
) -> None:
    labels = liquidity_signal_labels()
    groups = [
        ("原始口径", [name for name in labels if not name.endswith("_neutral")]),
        ("剔除市值和低波动影响", [name for name in labels if name.endswith("_neutral")]),
    ]
    fig, axes = plt.subplots(2, 1, figsize=(17, 12), sharex=True)
    colors = plt.get_cmap("viridis")(np.linspace(0.08, 0.92, 5))
    for axis, (title, variants) in zip(axes, groups, strict=True):
        for color, variant in zip(colors, variants, strict=True):
            returns = portfolios[variant]["long_short"].dropna()
            nav = (1 + returns).cumprod()
            axis.plot(nav.index, nav, linewidth=1.3, color=color, label=labels[variant])
        axis.axhline(1, color="#777", linewidth=0.6, linestyle="--")
        axis.set_yscale("log")
        axis.set_ylabel("多空净值（对数刻度）", fontproperties=CJK)
        axis.set_title(title, fontproperties=CJK, fontsize=12)
        axis.legend(prop=CJK, fontsize=8, ncol=2, framealpha=0.4)
        axis.grid(axis="y", color=LG, linewidth=0.4, alpha=0.35)
    fig.suptitle("低换手因子不同定义的多空净值", fontproperties=CJK, fontsize=15)
    fig.tight_layout()
    fig.savefig(outdir / "liquidity_signal_nav.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def plot_liquidity_quintiles(summary: pd.DataFrame, outdir: Path) -> None:
    labels = liquidity_signal_labels()
    values = summary.set_index("variant")[
        [f"q{quantile}_annual_return" for quantile in range(1, 6)]
    ]
    array = values.to_numpy(dtype=float)
    finite = np.abs(array[np.isfinite(array)])
    limit = max(10.0, float(np.percentile(finite, 95))) if finite.size else 10.0
    fig, axis = plt.subplots(figsize=(12, 9))
    image = axis.imshow(array, cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    axis.set_xticks(range(5))
    axis.set_xticklabels(
        ["第一组\n高换手", "第二组", "第三组", "第四组", "第五组\n低换手"],
        fontproperties=CJK,
    )
    axis.set_yticks(range(len(values)))
    axis.set_yticklabels([labels[name] for name in values.index], fontproperties=CJK, fontsize=9)
    for row in range(array.shape[0]):
        for column in range(array.shape[1]):
            value = array[row, column]
            if np.isfinite(value):
                axis.text(
                    column,
                    row,
                    f"{value:+.1f}%",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if abs(value) > limit * 0.55 else "#222",
                )
    axis.set_title("低换手因子五组年化收益", fontproperties=CJK, fontsize=14)
    colorbar = fig.colorbar(image, ax=axis, shrink=0.85)
    colorbar.set_label("几何年化收益（%）", fontproperties=CJK)
    fig.tight_layout()
    fig.savefig(
        outdir / "liquidity_quintile_returns.png",
        dpi=150,
        facecolor=BG,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_liquidity_long_only(summary: pd.DataFrame, outdir: Path) -> None:
    labels = liquidity_signal_labels()
    ordered = summary.set_index("variant")
    positions = np.arange(len(ordered))
    height = 0.24
    fig, axis = plt.subplots(figsize=(15, 10))
    axis.barh(
        positions - height,
        ordered["long_annual_return"],
        height=height,
        label="低换手多头",
        color="#00d4aa",
    )
    axis.barh(
        positions,
        ordered["long_excess_annual_return"],
        height=height,
        label="多头相对样本",
        color="#ffd93d",
    )
    axis.barh(
        positions + height,
        ordered["long_short_annual_return"],
        height=height,
        label="低换手减高换手",
        color="#ff6b6b",
    )
    axis.set_yticks(positions)
    axis.set_yticklabels([labels[name] for name in ordered.index], fontproperties=CJK, fontsize=9)
    axis.axvline(0, color="#777", linewidth=0.6)
    axis.set_xlabel("几何年化收益（%）", fontproperties=CJK)
    axis.set_title("低换手多头、相对样本收益和多空收益", fontproperties=CJK, fontsize=14)
    axis.legend(prop=CJK)
    axis.grid(axis="x", color=LG, linewidth=0.4, alpha=0.35)
    fig.tight_layout()
    fig.savefig(outdir / "liquidity_long_only.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def _tieout_text(metadata: dict[str, object]) -> str:
    tieout = metadata.get("baseline_tieout", {})
    if not isinstance(tieout, dict) or not tieout.get("performed"):
        return "未提供历史基准产物，本次没有执行逐日收益对账。"
    status = "通过" if tieout.get("passed") else "未通过"
    return (
        f"单日换手率口径与当前主线算法基准在 {tieout['common_days']} 个共同交易日完成对账，"
        f"最大绝对差异为 {tieout['maximum_absolute_difference']:.3e}，结果为{status}。"
    )


def _conclusion_lines(
    summary: pd.DataFrame,
    metadata: dict[str, object],
) -> list[str]:
    base = summary[~summary["neutralized"]].copy()
    neutral = summary[summary["neutralized"]].copy()
    positive_base = int((base["long_short_annual_return"] > 0).sum())
    positive_neutral = int((neutral["long_short_annual_return"] > 0).sum())
    monotonic_base = int((base["monotonicity_spearman"] >= 0.8).sum())
    smoothed_base = base[base["variant"] != "turnover_1d"]
    smoothed_neutral = neutral[neutral["variant"] != "turnover_1d_neutral"]
    smoothed_base_range = (
        smoothed_base["long_short_annual_return"].min(),
        smoothed_base["long_short_annual_return"].max(),
    )
    smoothed_neutral_range = (
        smoothed_neutral["long_short_annual_return"].min(),
        smoothed_neutral["long_short_annual_return"].max(),
    )
    smoothed_excess_range = (
        smoothed_neutral["long_excess_annual_return"].min(),
        smoothed_neutral["long_excess_annual_return"].max(),
    )
    return [
        f"- 五种原始口径中有 {positive_base} 种取得正向多空年化收益。",
        f"- 五种中性化口径中有 {positive_neutral} 种取得正向多空年化收益。",
        f"- 五种原始口径中有 {monotonic_base} 种的五组收益单调相关系数达到 0.8。",
        f"- 四种平滑口径的多空年化收益介于 {_fmt_pct(smoothed_base_range[0])} 和 "
        f"{_fmt_pct(smoothed_base_range[1])} 之间。联合剔除市值和低波动影响后，区间为 "
        f"{_fmt_pct(smoothed_neutral_range[0])} 至 {_fmt_pct(smoothed_neutral_range[1])}。",
        f"- 中性化平滑口径的低换手多头相对同期有效样本年化收益介于 "
        f"{_fmt_pct(smoothed_excess_range[0])} 和 {_fmt_pct(smoothed_excess_range[1])} 之间。",
        f"- {_tieout_text(metadata)}",
        "- 平滑口径保留了正向收益和较强的五组单调性，说明结果具有一定持续性。"
        "单日口径收益更高，表明月末单日交易状态也贡献了部分差异。",
    ]


def _method_and_boundary_lines(metadata: dict[str, object]) -> list[str]:
    minimum_coverage = float(metadata.get("minimum_coverage", 0.75))
    labels = liquidity_signal_labels()
    return [
        "## 计算方法",
        "",
        "- 换手率先限制在 0.01% 至 100% 范围内。20 日和 60 日统计至少需要各自窗口 "
        f"{minimum_coverage:.0%} 的有效观察。",
        "- 每个月末对低换手信号进行截面缩尾、申万历史一级行业内去均值和全市场标准化。",
        "- 中性化口径逐月回归剔除市值因子和低波动因子的线性影响，再对残差进行标准化。",
        "- 第一组为高换手股票，第五组为低换手股票。"
        "五组从下一交易日开始等权持有，月内保持固定份额。",
        "- 多头相对样本收益等于第五组收益减去当期所有有效样本股票的等权收益。",
        "",
        "## 数据和方法边界",
        "",
        "- 本诊断使用与长期基准相同的基础日行情、日频估值和行业处理方法。",
        "- 替代口径尚未接入停牌、涨跌停、退市压力情景和交易成本，不能替代全历史约束稳健性复核。",
        "- 中性化只剔除市值和低波动的线性截面关系，非线性暴露和其他防御风格仍可能保留。",
        "- 低换手多头收益是历史等权组合结果，容量、冲击成本和实际可买入性仍需单独评估。",
        "- 多空收益中的高换手组仍是理论空头代理，真实券源和借券成本尚未纳入。",
        "",
        "## 口径名称",
        "",
        *[f"- {label}" for label in labels.values()],
        "",
        f"复算日期：{_fmt_date(metadata['generated_at'])}。",
    ]


def generate_liquidity_report(
    summary: pd.DataFrame,
    metadata: dict[str, object],
    outdir: Path,
) -> str:

    display_summary = _display_summary(summary)
    percent_columns = {
        "多空年化收益",
        "低换手多头年化收益",
        "多头相对样本年化收益",
    }
    quintile_display = _display_quintiles(summary)
    quintile_percent_columns = set(quintile_display.columns[1:])
    risk_display = _display_risk(summary)
    risk_percent_columns = {"多空年化收益", "最大回撤", "正收益年份占比"}
    lines = [
        "# A 股低换手因子定义与暴露诊断",
        "",
        f"> 数据截至：{_fmt_date(metadata['data_end'])}",
        f"> 观察区间：{_fmt_date(metadata['data_start'])}至 {_fmt_date(metadata['data_end'])}",
        f"> 月末形成日：{metadata['formation_dates']} 个",
        "> 报告定位：研究筛查级因子定义诊断",
        "",
        "本报告比较月末单日换手率、20 日和 60 日平均换手率、20 日和 60 日中位换手率，"
        "并检验剔除市值和低波动线性影响后的结果。每种口径同时观察五组收益、低换手多头、"
        "多头相对样本收益和低换手减高换手收益。",
        "",
        "## 核心结论",
        "",
        *_conclusion_lines(summary, metadata),
        "",
        "## 口径对照",
        "",
        _markdown_table(display_summary, percent_columns),
        "",
        "五组单调相关越接近 1，收益越倾向于从高换手组向低换手组依次改善。"
        "相邻改善步数的满分为 4。相关系数用于描述信号与控制变量的截面关系。",
        "",
        "## 五组收益",
        "",
        _markdown_table(quintile_display, quintile_percent_columns),
        "",
        "## 风险对照",
        "",
        _markdown_table(risk_display, risk_percent_columns),
        "",
        "![不同定义的多空净值](liquidity_signal_nav.png)",
        "",
        "![五组年化收益](liquidity_quintile_returns.png)",
        "",
        "![多头和多空收益对照](liquidity_long_only.png)",
        "",
        *_method_and_boundary_lines(metadata),
    ]
    report = "\n".join(lines) + "\n"
    (outdir / "liquidity_factor_diagnostics.md").write_text(report, encoding="utf-8")
    return report
