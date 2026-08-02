"""Artifacts and Markdown appendix for the constrained robustness profile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from . import CJK, FACTOR_LABELS, FACTOR_ORDER
from .report import _markdown_table
from .robustness_backtest import ConstrainedBacktestArtifacts, RobustnessConfig


def _comparison_wide(comparison: pd.DataFrame) -> pd.DataFrame:
    metrics = ["days", "geometric_annual_ret", "max_drawdown", "sharpe"]
    selected = comparison[["factor", "profile", *metrics]].copy()
    wide = selected.pivot(index="factor", columns="profile", values=metrics)
    wide.columns = [f"{metric}_{profile}" for metric, profile in wide.columns]
    wide = wide.reset_index()
    ordered = [factor for factor in FACTOR_ORDER if factor in set(wide["factor"])]
    wide["_order"] = wide["factor"].map({name: index for index, name in enumerate(ordered)})
    wide = wide.sort_values("_order").drop(columns="_order")
    wide.insert(1, "factor_label", wide["factor"].map(FACTOR_LABELS).fillna(wide["factor"]))
    net = "geometric_annual_ret_constrained_net"
    raw = "geometric_annual_ret_raw_gross_matched_window"
    if {net, raw} <= set(wide.columns):
        wide["net_minus_raw_annual_pct"] = wide[net] - wide[raw]
    return wide


def _report_table(wide: pd.DataFrame) -> pd.DataFrame:
    columns = {
        "factor_label": "因子",
        "days_constrained_net": "共同观察日",
        "geometric_annual_ret_raw_gross_matched_window": "raw/gross 年化%",
        "geometric_annual_ret_constrained_gross": "constrained/gross 年化%",
        "geometric_annual_ret_constrained_net": "constrained/net 年化%",
        "net_minus_raw_annual_pct": "net-raw 百分点",
        "max_drawdown_constrained_net": "net 最大回撤%",
    }
    present = [column for column in columns if column in wide.columns]
    table = wide[present].rename(columns=columns)
    if "共同观察日" in table.columns:
        table["共同观察日"] = table["共同观察日"].astype(int)
    return table


def _scenario_excerpt(scenarios: pd.DataFrame) -> pd.DataFrame:
    focus = ["value", "liquidity", "size", "momentum"]
    excerpt = scenarios[scenarios["factor"].isin(focus)].copy()
    excerpt["factor"] = excerpt["factor"].map(FACTOR_LABELS).fillna(excerpt["factor"])
    columns = [
        "factor",
        "terminal_return",
        "cost_bps",
        "geometric_annual_ret",
        "max_drawdown",
        "sharpe",
    ]
    return excerpt[columns].sort_values(["factor", "terminal_return", "cost_bps"])


def _plot_comparison(wide: pd.DataFrame, outdir: Path) -> None:
    profiles = [
        ("geometric_annual_ret_raw_gross_matched_window", "raw/gross"),
        ("geometric_annual_ret_constrained_gross", "constrained/gross"),
        ("geometric_annual_ret_constrained_net", "constrained/net"),
    ]
    frame = wide.set_index("factor_label")
    chart = pd.DataFrame(
        {label: frame[column] for column, label in profiles if column in frame.columns}
    )
    ax = chart.plot.bar(figsize=(18, 8), width=0.82)
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.set_title("2015–2026 风格因子约束稳健性对照", fontproperties=CJK, fontsize=17)
    ax.set_ylabel("几何年化收益（%）", fontproperties=CJK)
    ax.set_xlabel("")
    ax.set_xticklabels(chart.index, fontproperties=CJK, rotation=35, ha="right")
    ax.legend(prop=CJK)
    ax.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.savefig(outdir / "style_factor_robustness_comparison.png", dpi=180)
    plt.close()


def _metadata_payload(
    *,
    data_metadata: dict[str, Any],
    config: RobustnessConfig,
    baseline_artifacts: Path,
) -> dict[str, Any]:
    return {
        "profile": "style_factor_constrained_robustness.v1",
        "research_posture": "screen_grade_constrained_sensitivity",
        "baseline_artifacts": str(baseline_artifacts),
        "min_listed_days": config.min_listed_days,
        "transaction_cost_bps": config.transaction_cost_bps,
        "delist_terminal_return": config.delist_terminal_return,
        "cost_scenarios_bps": list(config.cost_scenarios_bps),
        "delist_scenarios": list(config.delist_scenarios),
        "execution": {
            "signal_time": "formation_date_close",
            "first_attempt": "next_market_trade_date_close",
            "return_start": "first close-to-close interval after filled close",
            "blocked_orders": "retry_daily_until_filled_or_next_rebalance",
            "long_entry_block": "missing/suspended or close_at_up_limit",
            "long_exit_block": "missing/suspended or close_at_down_limit",
            "short_entry_block": "missing/suspended or close_at_down_limit",
            "short_cover_block": "missing/suspended or close_at_up_limit",
            "missing_holding_return": "zero_until_mark_or_terminal_event",
            "short_leg": "theoretical_bottom-quintile proxy; no borrow inventory or fee data",
        },
        "data": data_metadata,
    }


def _coverage_lines(data: dict[str, Any]) -> list[str]:
    return [
        "## 数据覆盖",
        "",
        f"- daily_clean：{data['daily_clean_start']} ~ {data['daily_clean_end']}，"
        f"{data['daily_clean_rows']:,} 行，{data['daily_clean_symbols']:,} 只证券。",
        f"- PIT 形成日股票池：{data['universe_start']} ~ {data['universe_end']}，"
        f"{data['universe_rebalance_dates']} 个形成日。",
        "- 涨跌停：使用 daily_clean 内由 limit_status/stk_limit overlay 生成的"
        " is_limit_up / is_limit_down。",
        f"- 历史 ST 明细：{data['st_start']} ~ {data['st_end']}。覆盖前日期保持未知，"
        "不使用 daily_clean 中来自 latest instruments 的非 PIT is_st 回填历史。",
    ]


def _methodology_lines(diagnostic_count: int) -> list[str]:
    return [
        "## 执行逻辑",
        "",
        "- 月末收盘形成信号，下一市场交易日收盘尝试调仓，成交仓位从后续"
        "收盘到收盘区间开始计算收益。",
        "- 多头涨停不能买、跌停不能卖；空头代理跌停不能开、涨停不能回补。",
        "- 缺少当日行情视为停牌或不可交易，未完成订单逐日重试，直到成交或被下一次调仓覆盖。",
        "- 持有期间缺失价格继续按零收益冻结资本；样本内退市在退市日映射到压力"
        "情景末端收益，计价后移除仓位。",
        "- 成本按多空两腿实际成交名义金额扣减，不按固定月度费率拍脑袋扣除。",
        "",
        "## 仍未解除的限制",
        "",
        "- 2015–2021 缺少可靠逐日 ST 历史，需要分页摄取 namechange 并重建区间。",
        "- 退市末端收益是压力代理，不是真实退市整理期、现金清算或场外转让收益。",
        "- 空头腿仍是理论 bottom-quintile 代理；margin_secs 只能补充资格上界，"
        "仍不能证明券源、费率、召回和可借数量。",
        "- legacy fundamentals 仍非 revision-safe PIT v2。2026 年回填不能证明历史观测版本。",
        "- universe_by_date 当前是形成日快照，不是逐日股票池。",
        "",
        "## 机器可读证据",
        "",
        f"- 因子诊断：{diagnostic_count} 个因子，见 factor_robustness_diagnostics.csv。",
        "- 全量对照：factor_robustness_comparison.csv。",
        "- 成本与退市情景：factor_robustness_scenarios.csv。",
        "- 运行口径：robustness_meta.json。",
        "",
        "只有 raw 与 constrained 在方向、回撤和成本后收益上都稳定，"
        "且 ST、退市真实收益、借券与 revision-safe PIT v2 的证据补齐后，"
        "才适合讨论升级正式 latest。",
    ]


def _render_report(
    *,
    wide: pd.DataFrame,
    scenarios: pd.DataFrame,
    diagnostics: pd.DataFrame,
    metadata: dict[str, Any],
) -> str:
    table = _report_table(wide)
    scenario_table = _scenario_excerpt(scenarios)
    lines = [
        "# A 股风格因子 2015–2026 约束稳健性附录",
        "",
        "> 状态：screen-grade constrained sensitivity。该附录不替换 2008–2026 "
        "raw 长历史报告，也不发布为正式 latest。",
        "",
        "## 研究问题",
        "",
        "在相同样本窗口内，对照 raw/gross、daily_clean 约束后 gross、"
        "以及加入换手成本后的 constrained/net，检查主要风格结论是否依赖"
        "股票池、上市天数、ST、涨跌停、停牌和退市处理。",
        "",
        *_coverage_lines(metadata["data"]),
        "",
        "## 核心对照",
        "",
        _markdown_table(table, index=False, floatfmt=".2f"),
        "",
        "共同观察日按每个因子 raw 与 constrained 都有实际暴露的日期取交集。"
        "LiquidityFlow、ChipConcentration 和 InstitutionHolding 覆盖较稀疏，"
        "不能把其日数按连续 11 年理解。",
        "",
        "![2015–2026 约束稳健性对照](style_factor_robustness_comparison.png)",
        "",
        "## 成本与退市压力情景",
        "",
        "默认单边成交名义成本为 10 bps，退市末端收益使用 -50% 压力代理；"
        "同时输出 0/10/20/30 bps 和 -30%/-50%/-100% 情景。",
        "",
        _markdown_table(scenario_table, index=False, floatfmt=".2f"),
        "",
        *_methodology_lines(len(diagnostics)),
    ]
    return "\n".join(lines)


def write_robustness_artifacts(
    artifacts: ConstrainedBacktestArtifacts,
    *,
    outdir: Path,
    data_metadata: dict[str, Any],
    config: RobustnessConfig,
    baseline_artifacts: Path,
) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    wide = _comparison_wide(artifacts.comparison)
    metadata = _metadata_payload(
        data_metadata=data_metadata,
        config=config,
        baseline_artifacts=baseline_artifacts,
    )
    artifacts.comparison.to_csv(outdir / "factor_robustness_comparison.csv", index=False)
    wide.to_csv(outdir / "factor_robustness_comparison_wide.csv", index=False)
    artifacts.scenarios.to_csv(outdir / "factor_robustness_scenarios.csv", index=False)
    artifacts.diagnostics.to_csv(outdir / "factor_robustness_diagnostics.csv", index=False)
    for factor, result in artifacts.gross_results.items():
        result["long_short"].to_csv(
            outdir / f"factor_{factor}_constrained_gross_daily.csv",
            index=True,
            header=True,
        )
    for factor, result in artifacts.net_results.items():
        result["long_short"].to_csv(
            outdir / f"factor_{factor}_constrained_net_daily.csv",
            index=True,
            header=True,
        )
    (outdir / "robustness_meta.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _plot_comparison(wide, outdir)
    report = _render_report(
        wide=wide,
        scenarios=artifacts.scenarios,
        diagnostics=artifacts.diagnostics,
        metadata=metadata,
    )
    (outdir / "style_factor_robustness_report.md").write_text(report + "\n", encoding="utf-8")
    return metadata
