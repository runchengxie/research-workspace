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
from .robustness_quality import data_quality_frame


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
    ax.set_title("2008–2026 风格因子约束稳健性对照", fontproperties=CJK, fontsize=17)
    ax.set_ylabel("几何年化收益（%）", fontproperties=CJK)
    ax.set_xlabel("")
    ax.set_xticklabels(chart.index, fontproperties=CJK, rotation=35, ha="right")
    ax.legend(prop=CJK)
    ax.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.savefig(outdir / "style_factor_robustness_comparison.png", dpi=180)
    plt.close()


def _plot_drawdown(wide: pd.DataFrame, outdir: Path) -> None:
    profiles = [
        ("max_drawdown_raw_gross_matched_window", "raw/gross"),
        ("max_drawdown_constrained_net", "constrained/net (10 bps)"),
    ]
    frame = wide.set_index("factor_label")
    chart = pd.DataFrame(
        {label: frame[column] for column, label in profiles if column in frame.columns}
    )
    ax = chart.plot.bar(figsize=(18, 8), width=0.76, color=["#5B8FF9", "#E8684A"])
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.set_title("2008–2026 最大回撤对照", fontproperties=CJK, fontsize=17)
    ax.set_ylabel("最大回撤（%）", fontproperties=CJK)
    ax.set_xlabel("")
    ax.set_xticklabels(chart.index, fontproperties=CJK, rotation=35, ha="right")
    ax.legend(prop=CJK)
    ax.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.savefig(outdir / "style_factor_robustness_drawdown.png", dpi=180)
    plt.close()


def _plot_margin_comparison(comparison: pd.DataFrame, outdir: Path) -> None:
    if comparison.empty:
        return
    frame = comparison.pivot(
        index="factor", columns="profile", values="geometric_annual_ret"
    ).reindex([factor for factor in FACTOR_ORDER if factor in set(comparison["factor"])])
    frame.index = [FACTOR_LABELS.get(str(value), str(value)) for value in frame.index]
    frame = frame.rename(
        columns={
            "constrained_net_matched_reported_activity_window": "constrained/net",
            "reported_borrow_activity_proxy_net": "reported-activity short proxy",
        }
    )
    ax = frame.plot.bar(figsize=(18, 8), width=0.76, color=["#5AD8A6", "#F6BD16"])
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.set_title("2015–2026 已报告借券活动代理敏感性", fontproperties=CJK, fontsize=17)
    ax.set_ylabel("几何年化收益（%）", fontproperties=CJK)
    ax.set_xlabel("")
    ax.set_xticklabels(frame.index, fontproperties=CJK, rotation=35, ha="right")
    ax.legend(prop=CJK)
    ax.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.savefig(outdir / "style_factor_margin_qualification_sensitivity.png", dpi=180)
    plt.close()


def _metadata_payload(
    *,
    data_metadata: dict[str, Any],
    config: RobustnessConfig,
    baseline_artifacts: Path,
) -> dict[str, Any]:
    return {
        "profile": "style_factor_constrained_robustness.v2",
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
            "short_leg": "theoretical bottom-quintile proxy; no borrow inventory or fee data",
            "short_activity_sensitivity": (
                "qualification intersect reported margin_detail/slb_sec_detail activity; "
                "still no borrow inventory, fee or recall history"
            ),
        },
        "data": data_metadata,
    }


def _coverage_lines(data: dict[str, Any]) -> list[str]:
    return [
        "## 数据覆盖",
        "",
        f"- daily_clean：{data['daily_clean_start']} ~ {data['daily_clean_end']}，"
        f"{data['daily_clean_rows']:,} 行，{data['daily_clean_symbols']:,} 只证券。",
        "- 2008–2014 联结完整率：daily_basic "
        f"{data['early_daily_basic_join_rate']:.4%}、adj_factor "
        f"{data['early_adj_factor_join_rate']:.4%}、limit_status "
        f"{data['early_limit_status_join_rate']:.4%}。",
        "- 2014/2015 复权桥：按 raw close × adj_factor 统一尺度，"
        f"P99 绝对收益误差 {data['adjustment_bridge_p99_abs_error_pct']:.4f} 个百分点，"
        f">0.10 个百分点 {data['adjustment_bridge_errors_over_0_10_pct']} 只。",
        f"- PIT 形成日股票池：{data['universe_start']} ~ {data['universe_end']}，"
        f"{data['universe_rebalance_dates']} 个形成日；与日行情联结率 "
        f"{data['universe_daily_join_rate']:.4%}。",
        "- 涨跌停：2008–2014 使用已验 hash 的 stk_limit bridge，2015+ 使用"
        " daily_clean 内的 limit flags。",
        f"- 历史 ST：namechange 区间重建后只在形成日展开，共 {data['st_rows']:,} 行；"
        "属于 reconstructed PIT，不是 revision-safe 历史；st 变更事件只作旁证，"
        f"共 {data['provider_st_event_rows']:,} 条。",
        f"- 显式停牌：suspend_d 共 {data['suspend_event_rows']:,} 条事件，"
        f"其中 {data['suspend_events_on_price_rows']:,} 条与价格行重合并进入不可交易标记；"
        f"其余 {data['suspend_events_without_price_rows']:,} 条由缺失价格不可交易逻辑覆盖。",
        f"- PIT v2：vintage={data['pit_vintage']}，报告期查询从"
        f" {data['pit_query_start_date']} 起；历史形成日仅可称 reconstructed PIT；"
        f" revision-safe 起点为 {data['revision_safe_from']}。",
        f"- 融券资格：{data['margin_start']} ~ {data['margin_end']}，仅作为做空资格上界。",
        f"- 已报告借券活动代理：{data['reported_borrow_activity_start']} ~ "
        f"{data['reported_borrow_activity_end']}，由 margin_secs 资格与"
        " margin_detail/slb_sec_detail 正活动取交集。",
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
        "- 历史 ST 已由 namechange 重建，但仍是 2026 年回填的 reconstructed PIT。",
        "- 退市末端收益是压力代理，不是真实退市整理期、现金清算或场外转让收益。",
        "- 空头腿仍是理论 bottom-quintile 代理；margin_detail/slb_sec_detail 只证明"
        "市场中出现过已报告活动，仍不能证明研究组合当日券源、费率、召回和可借数量。",
        "- PIT v2 已接入 ROE、ROA、杠杆、经营现金流、净利润及 Growth 所需的"
        " netprofit_yoy/or_yoy；历史财务版本仍非 revision-safe。",
        "- universe_by_date 当前是形成日快照，不是逐日股票池。",
        "",
        "## 机器可读证据",
        "",
        f"- 因子诊断：{diagnostic_count} 个因子，见 factor_robustness_diagnostics.csv。",
        "- 全量对照：factor_robustness_comparison.csv。",
        "- 成本与退市情景：factor_robustness_scenarios.csv。",
        "- 运行口径：robustness_meta.json。",
        "",
        "promotion_gate.csv / promotion_decision.json 给出预先声明门槛的逐因子证据。",
    ]


def _overview_lines(
    *,
    wide: pd.DataFrame,
    metadata: dict[str, Any],
    gate_decision: dict[str, Any],
    data_quality: pd.DataFrame,
) -> list[str]:
    table = _report_table(wide)
    return [
        "# A 股风格因子 2008–2026 全历史约束稳健性附录",
        "",
        "> 状态：screen-grade constrained sensitivity。晋级结论："
        f"{gate_decision['decision']}。"
        "只有 promotion gate 全部通过才允许更新三份主报告和正式 latest。",
        "",
        "## 研究问题",
        "",
        "在相同样本窗口内，对照 raw/gross、daily_clean 约束后 gross、"
        "以及加入换手成本后的 constrained/net，检查主要风格结论是否依赖"
        "股票池、上市天数、ST、涨跌停、停牌和退市处理。",
        "",
        *_coverage_lines(metadata["data"]),
        "",
        "## 数据质量门槛",
        "",
        _markdown_table(data_quality, index=False, floatfmt=".6f"),
        "",
        *_interpretation_guardrail_lines(),
        "",
        "## 核心对照",
        "",
        _markdown_table(table, index=False, floatfmt=".2f"),
        "",
        "共同观察日按每个因子 raw 与 constrained 都有实际暴露的日期取交集。"
        "LiquidityFlow、ChipConcentration 和 InstitutionHolding 覆盖较稀疏，"
        "不能把其日数按连续 11 年理解。",
        "",
        "![2008–2026 约束稳健性对照](style_factor_robustness_comparison.png)",
        "",
        "![2008–2026 最大回撤对照](style_factor_robustness_drawdown.png)",
        "",
    ]


def _interpretation_guardrail_lines() -> list[str]:
    return [
        "### 门槛解读边界",
        "",
        "- `factor_pass` 仅表示覆盖率、方向一致性、相对回撤和成本方向门槛"
        "全部通过。收益方向可以稳定为负，因此不代表正收益、统计显著或可直接交易。",
        "- 数据质量门槛通过仅表示本次校验范围内未发现完整性或拼接异常。"
        "这不等于因子可投资，也不能证明空头腿当日具备真实可借库存、可接受费率和可实施数量。",
    ]


def _gate_and_sensitivity_lines(
    *,
    scenarios: pd.DataFrame,
    gate_results: pd.DataFrame,
    gate_decision: dict[str, Any],
) -> list[str]:
    scenario_table = _scenario_excerpt(scenarios)
    return [
        "## 成本与退市压力情景",
        "",
        "默认单边成交名义成本为 10 bps，退市末端收益使用 -50% 压力代理；"
        "同时输出 0/10/20/30 bps 和 -30%/-50%/-100% 情景。",
        "",
        _markdown_table(scenario_table, index=False, floatfmt=".2f"),
        "",
        "## 正式 latest 晋级门槛",
        "",
        "10 个核心因子须全部通过：共同样本覆盖不低于最大样本的 80%，三种主口径"
        "方向一致，constrained/net 最大回撤相对 raw 恶化不超过 10 个百分点，"
        "并且方向在 10/30 bps 成本下均不翻转。",
        "",
        _markdown_table(
            gate_results[
                [
                    "factor",
                    "coverage_ratio",
                    "direction_pass",
                    "drawdown_pass",
                    "cost_pass",
                    "factor_pass",
                    "failure_reason",
                ]
            ],
            index=False,
            floatfmt=".2f",
        ),
        "",
        f"结论：{gate_decision['core_factors_passed']}/{len(gate_results)} 个核心因子通过，"
        f"因此动作是 `{gate_decision['official_latest_action']}`。",
        "",
        "## 已报告借券活动代理敏感性",
        "",
        "2015 年后的 margin_secs 先限定资格，再要求 formation date 的 margin_detail"
        " 融券余量/卖出量或 slb_sec_detail 出借数量为正。该口径比单纯资格更严格，"
        "仍不能证明组合当日可借库存、借券费、召回概率和可借数量。",
        "",
        "![2015–2026 已报告借券活动代理敏感性](style_factor_margin_qualification_sensitivity.png)",
        "",
    ]


def _render_report(
    *,
    wide: pd.DataFrame,
    scenarios: pd.DataFrame,
    diagnostics: pd.DataFrame,
    metadata: dict[str, Any],
    gate_results: pd.DataFrame,
    gate_decision: dict[str, Any],
    data_quality: pd.DataFrame,
) -> str:
    lines = _overview_lines(
        wide=wide,
        metadata=metadata,
        gate_decision=gate_decision,
        data_quality=data_quality,
    )
    lines.extend(
        _gate_and_sensitivity_lines(
            scenarios=scenarios,
            gate_results=gate_results,
            gate_decision=gate_decision,
        )
    )
    lines.extend(_methodology_lines(len(diagnostics)))
    return "\n".join(lines)


def write_robustness_artifacts(
    artifacts: ConstrainedBacktestArtifacts,
    *,
    outdir: Path,
    data_metadata: dict[str, Any],
    config: RobustnessConfig,
    baseline_artifacts: Path,
    gate_results: pd.DataFrame,
    gate_decision: dict[str, Any],
) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    wide = _comparison_wide(artifacts.comparison)
    metadata = _metadata_payload(
        data_metadata=data_metadata,
        config=config,
        baseline_artifacts=baseline_artifacts,
    )
    metadata["promotion_gate"] = gate_decision
    data_quality = data_quality_frame(data_metadata)
    artifacts.comparison.to_csv(outdir / "factor_robustness_comparison.csv", index=False)
    wide.to_csv(outdir / "factor_robustness_comparison_wide.csv", index=False)
    artifacts.scenarios.to_csv(outdir / "factor_robustness_scenarios.csv", index=False)
    artifacts.diagnostics.to_csv(outdir / "factor_robustness_diagnostics.csv", index=False)
    artifacts.margin_diagnostics.to_csv(
        outdir / "factor_margin_qualification_diagnostics.csv", index=False
    )
    artifacts.margin_comparison.to_csv(
        outdir / "factor_margin_qualification_comparison.csv", index=False
    )
    gate_results.to_csv(outdir / "promotion_gate.csv", index=False)
    data_quality.to_csv(outdir / "data_quality_checks.csv", index=False)
    (outdir / "promotion_decision.json").write_text(
        json.dumps(gate_decision, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
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
    for factor, result in artifacts.margin_net_results.items():
        result["long_short"].to_csv(
            outdir / f"factor_{factor}_margin_qualified_net_daily.csv",
            index=True,
            header=True,
        )
    (outdir / "robustness_meta.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _plot_comparison(wide, outdir)
    _plot_drawdown(wide, outdir)
    _plot_margin_comparison(artifacts.margin_comparison, outdir)
    report = _render_report(
        wide=wide,
        scenarios=artifacts.scenarios,
        diagnostics=artifacts.diagnostics,
        metadata=metadata,
        gate_results=gate_results,
        gate_decision=gate_decision,
        data_quality=data_quality,
    )
    (outdir / "style_factor_robustness_report.md").write_text(report + "\n", encoding="utf-8")
    return metadata
