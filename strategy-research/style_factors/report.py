"""Markdown report generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import FACTOR_LABELS


def _markdown_cell(value: object, floatfmt: str | None) -> str:
    if pd.isna(value):
        return "—"
    if floatfmt is not None and isinstance(value, int | float):
        return format(value, floatfmt)
    return str(value).replace("|", "\\|")


def _markdown_table(
    frame: pd.DataFrame,
    *,
    index: bool = True,
    floatfmt: str | None = None,
) -> str:
    """Render the small report tables without pandas' optional tabulate dependency."""
    headers = [str(column) for column in frame.columns]
    if index:
        headers.insert(0, str(frame.index.name or ""))
    rows = []
    for row_index, values in frame.iterrows():
        cells = [_markdown_cell(value, floatfmt) for value in values]
        if index:
            cells.insert(0, _markdown_cell(row_index, None))
        rows.append(cells)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    lines.extend("| " + " | ".join(cells) + " |" for cells in rows)
    return "\n".join(lines)


def _factor_definition_lines(active_factors: set[str] | None = None) -> list[str]:
    rows = [
        "| 因子 | 方向 | 构造方法 |",
        "|------|------|----------|",
    ]
    definitions = {
        "size": "| 市值因子 | 大市值减小市值 | 总市值的自然对数，月度分层 |",
        "value": "| 价值因子 | 低市净率减高市净率 | 市净率倒数，月度分层 |",
        "momentum": "| 21 日动量因子 | 强势减弱势 | 21 日收益，月度分层 |",
        "quality": (
            "| 质量因子 | 高质量减低质量 | 等权合成净资产收益率、低资产负债率、"
            "8 期盈利稳定性和现金流质量 |"
        ),
        "earnings_yield": ("| 盈利收益率因子 | 低市盈率减高市盈率 | 滚动市盈率倒数，月度分层 |"),
        "lowvol": "| 低波动因子 | 低波动减高波动 | 最近 21 个收益观察值的波动率 |",
        "growth": "| 成长因子 | 高增长减低增长 | 净利润同比和营业收入同比，按公告日对齐 |",
        "leverage": "| 低杠杆因子 | 低杠杆减高杠杆 | 资产负债率，按公告日对齐 |",
        "beta": "| 低贝塔因子 | 低贝塔减高贝塔 | 252 日滚动市场贝塔，最少 126 日 |",
        "liquidity": "| 低换手因子 | 低换手减高换手 | 换手率 |",
        "liquidity_flow": ("| 大单资金流因子 | 大单净买入较高减较低 | 大单净买入占比 |"),
        "chip_concentration": ("| 筹码集中度因子 | 集中度较高减较低 | 前十大流通股东持股占比 |"),
        "institution_holding": ("| 机构持仓因子 | 机构持仓较高减较低 | 前十大机构流通持股占比 |"),
        "fund_breadth": (
            "| 公募前十大重仓广度因子 | 前十大重仓基金较多减较少 | "
            "月末可见 PIT 状态下，把该股列入前十大重仓的公募基金数量，log1p 后截面标准化 |"
        ),
        "fund_breadth_change": (
            "| 公募前十大重仓广度变化因子 | 重仓覆盖增加减减少 | "
            "月末可见 PIT 前十大重仓基金数相对上个形成日的变化 |"
        ),
        "fund_ownership": (
            "| 公募前十大重仓比例因子 | 前十大重仓比例较高减较低 | "
            "各基金前十大重仓中该股票占流通股本比例的合计 |"
        ),
        "fund_ownership_change": (
            "| 公募前十大重仓比例变化因子 | 重仓比例增加减减少 | "
            "月末可见 PIT 前十大重仓流通股持仓比例相对上个形成日的变化 |"
        ),
        "dividend_yield": "| 股息率因子 | 高股息率减低股息率 | 过去 12 个月股息率 |",
        "ps_value": "| 市销率价值因子 | 低市销率减高市销率 | 滚动市销率倒数 |",
    }
    selected = active_factors if active_factors is not None else set(FACTOR_LABELS)
    rows.extend(definitions[name] for name in FACTOR_LABELS if name in selected)
    return rows


def _industry_neutralization_note(metadata: dict | None) -> list[str]:
    metadata = metadata or {}
    coverage = metadata.get("industry_coverage")
    coverage_text = f"，样本匹配率 {coverage:.1%}" if isinstance(coverage, int | float) else ""
    return [
        "",
        "## 行业信号处理",
        "",
        "因子先按申万历史一级行业在每期截面内去均值，再进行全市场标准化。"
        "该处理降低行业之间的平均信号差异，最终多空组合仍可能保留行业权重偏离。",
        "",
        f"- 行业成员按历史生效区间匹配{coverage_text}。",
        "- 缺少行业匹配的股票作为残差组单独处理。",
    ]


def _append_yearly_section(lines: list[str], yearly: pd.DataFrame | None) -> None:
    if yearly is None or yearly.empty:
        return
    value_column = "period_return" if "period_return" in yearly.columns else "annual_ret"
    ret_pivot = yearly.pivot(index="year", columns="factor", values=value_column)
    ret_display = ret_pivot.map(lambda value: "—" if pd.isna(value) else f"{value:+.1f}%")
    ret_display = ret_display.rename(columns=FACTOR_LABELS)
    ret_display.index.name = "年份"
    lines.extend(
        [
            "## 逐年收益",
            "",
            _markdown_table(ret_display),
            "",
            "![逐年因子收益](style_factor_yearly.png)",
            "",
        ]
    )


def _append_attribution_section(
    lines: list[str],
    summary: pd.DataFrame,
    attribution: dict | None,
    yearly_attribution: pd.DataFrame | None,
) -> None:
    if not attribution or "error" in attribution:
        return

    lines.extend(
        [
            "## 策略归因",
            "",
            f"策略：{attribution['strategy']}",
            "",
            f"- 覆盖：{attribution['days']} 天（{attribution['years']} 年）",
            f"- 策略几何年化收益：{attribution['geometric_annual_return']:.2f}%",
            f"- 因子解释度（R²）：{attribution['r_squared']:.4f}",
            f"- 回归截距的 252 日几何年化阿尔法：{attribution['annual_alpha']:.2f}%",
            "",
            "| 因子 | 贝塔 | 贡献 |",
            "|------|------|------|",
        ]
    )
    for factor, beta in attribution["betas"].items():
        factor_ann = summary.loc[summary["factor"] == factor, "annual_ret"].values
        factor_ann = float(factor_ann[0]) if len(factor_ann) > 0 else 0.0
        contrib = beta * factor_ann
        lines.append(f"| {FACTOR_LABELS.get(factor, factor)} | {beta:.4f} | {contrib:+.2f}% |")
    lines.append("")

    if yearly_attribution is None or yearly_attribution.empty:
        return
    compact_columns = [
        "year",
        "days",
        "period_return",
        "geometric_annual_return",
        "r_squared",
        "annual_alpha",
    ]
    compact = (
        yearly_attribution[compact_columns]
        .copy()
        .rename(
            columns={
                "year": "年份",
                "days": "观察日",
                "period_return": "期间收益（%）",
                "geometric_annual_return": "几何年化收益（%）",
                "r_squared": "解释度（R²）",
                "annual_alpha": "年化阿尔法（%）",
            }
        )
    )
    lines.extend(
        [
            "### 逐年策略归因",
            "",
            _markdown_table(compact, index=False, floatfmt=".2f"),
            "",
            "完整逐年贝塔、因子收益和贡献保存在逐年归因明细中。",
            "",
        ]
    )


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
        coverage = f"{ls.index.min().date()} 至 {ls.index.max().date()}，{len(ls)} 天"
        lines.append(f"- {FACTOR_LABELS[name]}：{coverage}")


def _summary_for_report(summary: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "factor",
        "days",
        "years",
        "cumulative_ret",
        "geometric_annual_ret",
        "annual_vol",
        "sharpe",
        "max_drawdown",
        "hit_rate",
    ]
    display = summary[[column for column in columns if column in summary.columns]].copy()
    display["factor"] = display["factor"].map(FACTOR_LABELS).fillna(display["factor"])
    return display.rename(
        columns={
            "factor": "因子",
            "days": "观察日",
            "years": "覆盖年数",
            "cumulative_ret": "累计收益（%）",
            "geometric_annual_ret": "几何年化收益（%）",
            "annual_vol": "年化波动率（%）",
            "sharpe": "夏普比率",
            "max_drawdown": "最大回撤（%）",
            "hit_rate": "日胜率（%）",
        }
    )


def generate_report(
    summary: pd.DataFrame,
    corr: pd.DataFrame,
    factor_results: dict,
    outdir: Path,
    attribution: dict | None = None,
    yearly: pd.DataFrame | None = None,
    yearly_attribution: pd.DataFrame | None = None,
    metadata: dict | None = None,
) -> str:
    metadata = metadata or {}
    active_factors = set(factor_results)
    data_start = metadata.get("data_start", "未知")
    data_end = metadata.get("data_end", "未知")
    generated_at = metadata.get("generated_at", "未知")
    summary_display = _summary_for_report(summary)
    corr_display = corr.rename(index=FACTOR_LABELS, columns=FACTOR_LABELS)
    lines = [
        "# A 股风格因子研究报告",
        "",
        f"- 生成时间：{generated_at}",
        f"- 日行情与估值样本：{data_start} 至 {data_end}",
        f"- 实际输出因子：{len(active_factors)} 个",
        "- 研究定位：历史风格筛查和策略归因",
        "",
        "> 长期基准使用基础日行情、日频估值和后续重建的历史财务数据。"
        "约束复核另行检验股票池、交易限制、成本和退市情景。",
        "",
        "## 因子定义",
        "",
        *_factor_definition_lines(active_factors),
        "",
        *_industry_neutralization_note(metadata),
        "",
        "每期按因子标准分排名并分为 5 组。多空两端在月末等权建仓，"
        "固定份额持有至下一个月末。报告展示得分最高的 20% 组合收益"
        "减去得分最低的 20% 组合收益。",
        "",
        "## 因子表现总览",
        "",
        _markdown_table(summary_display, index=False),
        "",
        "主报告使用 252 个交易日几何年化。部分年度和短覆盖因子需要结合实际观察区间解读。",
        "",
        "## 因子相关性",
        "",
        _markdown_table(corr_display, floatfmt=".2f"),
        "",
    ]

    _append_yearly_section(lines, yearly)
    _append_attribution_section(lines, summary, attribution, yearly_attribution)
    _append_coverage(lines, factor_results)
    lines.extend(
        [
            "",
            "数据来源：A 股日行情、日频估值、财务指标、现金流、资金流、"
            "持仓结构、公募基金前十大重仓 PIT 状态和申万历史一级行业数据。",
        ]
    )

    report = "\n".join(lines)
    (outdir / "style_analysis_report.md").write_text(report)
    print(f"[report] → {outdir / 'style_analysis_report.md'}")
    return report
