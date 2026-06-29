"""Markdown report generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from style_factors import FACTOR_LABELS


def _factor_definition_lines() -> list[str]:
    return [
        "| 因子 | 方向 | 构造方法 |",
        "|------|------|----------|",
        "| Size 大市值 | 多-空 | ln(总市值)，月度分层 |",
        "| Value 低估值 | 多-空 | 1/PB，月度分层 |",
        "| Momentum 动量 | 多-空 | 21日收益（跳过T日），月度分层 |",
        "| Quality 盈利 | 多-空 | 1/PE_TTM，月度分层 |",
        "| LowVol 低波动 | 多-空 | -20日波动率，月度分层 |",
        "| Growth 成长 | 多-空 | 净利润同比和营收同比，按公告日对齐 |",
        "| Leverage 低杠杆 | 多-空 | -资产负债率，按公告日对齐 |",
        "| Beta 低贝塔 | 多-空 | -252日滚动市场 beta |",
        "| Liquidity 低换手 | 多-空 | -换手率 |",
    ]


def _append_yearly_section(lines: list[str], yearly: pd.DataFrame | None) -> None:
    if yearly is None or yearly.empty:
        return
    ret_pivot = yearly.pivot(index="year", columns="factor", values="annual_ret")
    lines.extend(
        [
            "## 逐年收益",
            "",
            ret_pivot.to_markdown(floatfmt="+.1f"),
            "",
            "![逐年因子收益](style_factor_yearly.png)",
            "",
        ]
    )


def _append_attribution_section(
    lines: list[str],
    summary: pd.DataFrame,
    attribution: dict | None,
) -> None:
    if not attribution or "error" in attribution:
        return

    lines.extend(
        [
            "## 策略归因",
            "",
            f"策略: **{attribution['strategy']}**",
            "",
            f"- 覆盖: {attribution['days']} 天 ({attribution['years']} 年)",
            f"- 策略年化收益: {attribution['annual_return']:.2f}%",
            f"- 因子解释度 (R²): {attribution['r_squared']:.4f}",
            f"- 纯 alpha (年化): {attribution['annual_alpha']:.2f}%",
            f"- 截距 (年化): {attribution['intercept']:.4f}%",
            "",
            "| 因子 | Beta | 贡献 |",
            "|------|------|------|",
        ]
    )
    for factor, beta in attribution["betas"].items():
        factor_ann = summary.loc[summary["factor"] == factor, "annual_ret"].values
        factor_ann = float(factor_ann[0]) if len(factor_ann) > 0 else 0.0
        contrib = beta * factor_ann
        lines.append(f"| {FACTOR_LABELS.get(factor, factor)} | {beta:.4f} | {contrib:+.2f}% |")
    lines.append("")


def _append_coverage(lines: list[str], factor_results: dict) -> None:
    lines.extend(
        [
            "## 图表",
            "",
            "![因子净值](style_factor_nav.png)",
            "![收益对比](style_factor_comparison.png)",
            "![相关性](style_factor_corr.png)",
            "",
            "## 数据覆盖",
            "",
        ]
    )
    for name in FACTOR_LABELS:
        if name not in factor_results:
            continue
        ls = factor_results[name]["long_short"].dropna()
        if ls.empty:
            continue
        coverage = f"{ls.index.min().date()} ~ {ls.index.max().date()}, {len(ls)} 天"
        lines.append(f"- {FACTOR_LABELS[name]}: {coverage}")


def generate_report(
    summary: pd.DataFrame,
    corr: pd.DataFrame,
    factor_results: dict,
    outdir: Path,
    attribution: dict | None = None,
    yearly: pd.DataFrame | None = None,
) -> str:
    lines = [
        "# A 股全市场风格因子分析报告",
        "",
        "## 因子定义",
        "",
        *_factor_definition_lines(),
        "",
        "每期按因子 z-score 排名，等分为 5 组，等权持有至下一个月末调仓。",
        "展示的是 top quintile long - bottom quintile short 的日收益序列。",
        "",
        "## 因子表现总览",
        "",
        summary.to_markdown(index=False),
        "",
        "## 因子相关性",
        "",
        corr.to_markdown(floatfmt=".2f"),
        "",
    ]

    _append_yearly_section(lines, yearly)
    _append_attribution_section(lines, summary, attribution)
    _append_coverage(lines, factor_results)
    lines.extend(
        [
            "",
            "*由 Hermes Agent 自动生成 | 数据来源: market-data-platform (daily + daily_basic)*",
        ]
    )

    report = "\n".join(lines)
    (outdir / "style_analysis_report.md").write_text(report)
    print(f"[report] → {outdir / 'style_analysis_report.md'}")
    return report
