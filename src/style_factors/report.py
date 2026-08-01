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
        "size": "| Size 大市值 | 多-空 | ln(总市值)，月度分层 |",
        "value": "| Value 低估值 | 多-空 | 1/PB，月度分层 |",
        "momentum": "| Momentum 动量 | 多-空 | 21日收益（跳过T日），月度分层 |",
        "quality": (
            "| Quality 复合质量 | 多-空 | 等权复合 ROE、低资产负债率、8期盈利稳定性、"
            "现金流质量（OCF/净利润），各子指标逐日截面截尾+z 后合成 |"
        ),
        "earnings_yield": (
            "| Earnings Yield 盈利估值 | 多-空 | 1/PE_TTM，月度分层"
            "（价值组，估值代理而非盈利质量） |"
        ),
        "lowvol": "| LowVol 低波动 | 多-空 | -21个收益观察值波动率，月度分层 |",
        "growth": "| Growth 成长 | 多-空 | 净利润同比和营收同比，按公告日对齐 |",
        "leverage": "| Leverage 低杠杆 | 多-空 | -资产负债率，按公告日对齐 |",
        "beta": "| Beta 低贝塔 | 多-空 | -252日滚动市场 beta（最少126日） |",
        "liquidity": "| Liquidity 低换手 | 多-空 | -换手率 |",
        "liquidity_flow": (
            "| LiquidityFlow 大单资金流 | 多-空 | moneyflow_ths 大单净买占比，"
            "逐日精确匹配、截尾+z |"
        ),
        "chip_concentration": (
            "| ChipConcentration 筹码集中度 | 多-空 | holder_structure 前十大流通股"
            "集中度，逐日精确匹配、截尾+z |"
        ),
        "institution_holding": (
            "| InstitutionHolding 机构持仓 | 多-空 | holder_structure 前十大机构流通"
            "持股占比，逐日精确匹配、截尾+z |"
        ),
        "dividend_yield": ("| DividendYield 股息率 | 多-空 | daily_basic.dv_ttm 股息率，截尾+z |"),
        "ps_value": "| PSValue 市销率价值 | 多-空 | 1/ps_ttm，截尾+z |",
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
        "## 行业信号去均值（申万 PIT L1）",
        "",
        "因子在合成 z-score 前，先按申万一级行业在每期截面内做行业内 demean，"
        "再做跨行业横截面 z-score。该处理降低信号的行业均值暴露，"
        "不等同于最终多空组合的行业权重被严格约束为零。",
        "",
        "- 行业来源：本地已落地的**申万 PIT 行业**（`sw_industry_member` + `sw_industry`），"
        "按 `in_date <= trade_date <= out_date`（out_date 为空=当前）判定每只股票在每个时点的 "
        f"L1 行业{coverage_text}。",
        "- **非静态映射**：不使用 `stock_basic.industry` 或 ths_member 静态行业做中性化"
        "（ths_member 仅作为普通行业标签接入，不参与中性化）。",
        "- 无行业匹配的股票作为残差组单独去均值，不会因行业缺失而从所有因子中删除。",
    ]


def _append_yearly_section(lines: list[str], yearly: pd.DataFrame | None) -> None:
    if yearly is None or yearly.empty:
        return
    value_column = "period_return" if "period_return" in yearly.columns else "annual_ret"
    ret_pivot = yearly.pivot(index="year", columns="factor", values=value_column)
    ret_display = ret_pivot.map(lambda value: "—" if pd.isna(value) else f"{value:+.1f}")
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
            f"策略: **{attribution['strategy']}**",
            "",
            f"- 覆盖: {attribution['days']} 天 ({attribution['years']} 年)",
            f"- 策略几何年化收益: {attribution['geometric_annual_return']:.2f}%",
            f"- 因子解释度 (R²): {attribution['r_squared']:.4f}",
            f"- 回归截距的252日几何年化 alpha: {attribution['annual_alpha']:.2f}%",
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
    compact = yearly_attribution[compact_columns].copy()
    lines.extend(
        [
            "### 逐年策略归因",
            "",
            _markdown_table(compact, index=False, floatfmt=".2f"),
            "",
            "完整逐年 beta、因子收益和贡献见 `strategy_attribution_yearly.csv`。",
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
        coverage = f"{ls.index.min().date()} ~ {ls.index.max().date()}, {len(ls)} 天"
        lines.append(f"- {FACTOR_LABELS[name]}: {coverage}")


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
    return summary[[column for column in columns if column in summary.columns]].rename(
        columns={
            "cumulative_ret": "cumulative_ret_pct",
            "geometric_annual_ret": "geometric_annual_ret_pct",
            "annual_vol": "annual_vol_pct",
            "max_drawdown": "max_drawdown_pct",
            "hit_rate": "hit_rate_pct",
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
    lines = [
        "# A 股风格代理因子研究报告",
        "",
        f"- 生成时间：{generated_at}",
        f"- 日线与估值样本：{data_start} ~ {data_end}",
        f"- 实际输出因子：{len(active_factors)} 个",
        "- 研究姿态：历史风格筛查，不是可交易回测或严格行业中性风险模型",
        "",
        "> 2008 年以来的日线与估值段读取 raw daily / daily_basic；财务因子读取 legacy raw "
        "fundamentals。当前链路未完整消费 daily_clean、逐日 PIT 股票池或 revision-safe PIT v2，"
        "因此长历史结论属于 screen-grade 代理结果。",
        "",
        "## 因子定义",
        "",
        *_factor_definition_lines(active_factors),
        "",
        *_industry_neutralization_note(metadata),
        "",
        "每期按因子 z-score 排名，等分为 5 组。多空两腿在月末等权建仓，"
        "固定份额持有至下一个月末；持有期缺失收益按 0 处理。",
        "展示的是 top quintile long - bottom quintile short 的日收益序列。",
        "",
        "## 因子表现总览",
        "",
        _markdown_table(summary_display, index=False),
        "",
        "主报告使用 252 交易日几何年化；JSON 中保留旧字段 `annual_ret`（日均收益复利年化）"
        "以兼容既有消费者。",
        "",
        "## 因子相关性",
        "",
        _markdown_table(corr, floatfmt=".2f"),
        "",
    ]

    _append_yearly_section(lines, yearly)
    _append_attribution_section(lines, summary, attribution, yearly_attribution)
    _append_coverage(lines, factor_results)
    lines.extend(
        [
            "",
            "*由 style_factors 自动生成 | 数据来源：market-data-platform daily、daily_basic、"
            "legacy fundamentals/cashflow、moneyflow_ths、holder_structure 与申万行业成员历史*",
        ]
    )

    report = "\n".join(lines)
    (outdir / "style_analysis_report.md").write_text(report)
    print(f"[report] → {outdir / 'style_analysis_report.md'}")
    return report
