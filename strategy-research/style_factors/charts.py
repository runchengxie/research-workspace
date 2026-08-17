"""Chart generation — factor NAV, comparison, correlation, yearly breakdown."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch, Rectangle

from . import BG, CJK, FACTOR_COLORS, FACTOR_LABELS, FG, LG
from portfolio_backtester.style_factors_backtest import compute_factor_correlations

YEARLY_CHART_SCHEMA_VERSION = "research.style-factor-yearly-chart.v1"


@dataclass(frozen=True)
class YearlyChartArtifacts:
    png: Path
    svg: Path
    matrix_csv: Path
    metadata_json: Path


def _active_names(factor_results: dict) -> list[str]:
    return [name for name in FACTOR_LABELS if name in factor_results]


def plot_factor_nav(factor_results: dict, outdir: Path) -> None:
    """Multi-panel factor NAV charts."""
    names = _active_names(factor_results)
    if not names:
        return

    n = len(names)
    cols = 3
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(18, 5 * rows))
    axes = np.asarray(axes).reshape(-1)

    for i, name in enumerate(names):
        ax = axes[i]
        ls = factor_results[name]["long_short"].dropna()
        if ls.empty:
            ax.set_visible(False)
            continue
        cum = (1 + ls).cumprod()

        ax.fill_between(cum.index, cum, 1, where=(cum >= 1), color="#ff6b6b", alpha=0.3)
        ax.fill_between(cum.index, cum, 1, where=(cum < 1), color="#00d4aa", alpha=0.3)
        ax.plot(cum.index, cum, color=FACTOR_COLORS[name], linewidth=1.2)

        ann = ((cum.iloc[-1]) ** (252 / len(cum)) - 1) * 100
        ax.set_title(f"{FACTOR_LABELS[name]}（年化 {ann:.1f}%）", fontproperties=CJK, fontsize=11)
        ax.axhline(1, color="#555", linewidth=0.5, linestyle="--")
        ax.set_ylabel("净值", fontproperties=CJK)

    # Hide unused subplots
    for j in range(n, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(
        f"A 股 {n} 个风格因子多空净值曲线",
        fontproperties=CJK,
        fontsize=14,
        y=0.99,
    )
    fig.tight_layout()
    fig.savefig(outdir / "style_factor_nav.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print(f"[chart] factor NAV → {outdir / 'style_factor_nav.png'}")


def plot_cumulative_comparison(factor_results: dict, outdir: Path) -> None:
    """Single chart: all factor long-short cumulative returns overlaid.

    A logarithmic NAV axis keeps both large winners and near-zero losers visible
    on the same chart.  With a linear axis, the long-history liquidity proxy
    compresses most other factors into an unreadable band around one.
    """
    fig, ax = plt.subplots(figsize=(16, 7))

    plotted = False
    for name in _active_names(factor_results):
        ls = factor_results[name]["long_short"].dropna()
        if ls.empty:
            continue
        cum = (1 + ls).cumprod()
        ann = ((cum.iloc[-1]) ** (252 / len(cum)) - 1) * 100
        ax.plot(
            cum.index,
            cum,
            color=FACTOR_COLORS[name],
            linewidth=1.4,
            label=f"{FACTOR_LABELS[name]}（年化 {ann:.1f}%）",
        )
        plotted = True

    if not plotted:
        plt.close(fig)
        return

    ax.set_yscale("log")
    ax.axhline(1, color="#555", linewidth=0.5, linestyle="--")
    ax.grid(axis="y", which="both", color=LG, linewidth=0.4, alpha=0.35)
    ax.legend(loc="upper left", prop=CJK, framealpha=0.5, facecolor=BG, edgecolor=LG)
    ax.set_ylabel("净值（对数刻度）", fontproperties=CJK)
    ax.set_title(
        "A 股风格因子多空收益对比（对数净值）",
        fontproperties=CJK,
        fontsize=13,
    )
    fig.tight_layout()
    fig.savefig(
        outdir / "style_factor_comparison.png",
        dpi=150,
        facecolor=BG,
        bbox_inches="tight",
    )
    plt.close(fig)
    print(f"[chart] comparison → {outdir / 'style_factor_comparison.png'}")


def plot_correlation_heatmap(factor_results: dict, outdir: Path) -> None:
    """Factor return correlation heatmap."""
    corr = compute_factor_correlations(factor_results)
    if corr.empty:
        return

    size = max(8.0, len(corr) * 0.72)
    fig, ax = plt.subplots(figsize=(size, size * 0.9))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)

    labels = [FACTOR_LABELS.get(c, c) for c in corr.columns]
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, fontproperties=CJK, fontsize=9, rotation=45, ha="right")
    ax.set_yticklabels(labels, fontproperties=CJK, fontsize=9)

    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(
                j,
                i,
                f"{corr.iloc[i, j]:.2f}",
                ha="center",
                va="center",
                fontsize=max(5.5, 10 - len(corr) * 0.2),
                fontweight="bold",
                color="white" if abs(corr.iloc[i, j]) > 0.5 else "#333",
            )

    ax.set_title("因子收益相关性", fontproperties=CJK, fontsize=12)
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    fig.savefig(outdir / "style_factor_corr.png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print(f"[chart] correlation → {outdir / 'style_factor_corr.png'}")


def _yearly_return_matrix(yearly: pd.DataFrame) -> pd.DataFrame:
    """Return a factor-by-year matrix in the stable report factor order."""
    if yearly.empty:
        return pd.DataFrame()
    required = {"year", "factor"}
    missing = sorted(required - set(yearly.columns))
    if missing:
        raise ValueError(f"逐年因子数据缺少字段：{missing}")
    return_column = "period_return" if "period_return" in yearly.columns else "annual_ret"
    if return_column not in yearly.columns:
        raise ValueError("逐年因子数据缺少 period_return 或 annual_ret")
    duplicates = yearly.duplicated(["year", "factor"], keep=False)
    if bool(duplicates.any()):
        sample = yearly.loc[duplicates, ["year", "factor"]].head(3).to_dict("records")
        raise ValueError(f"逐年因子数据包含重复的年份与因子：{sample}")
    pivot = yearly.pivot(index="year", columns="factor", values=return_column).sort_index()
    factor_names = [name for name in FACTOR_LABELS if name in pivot.columns]
    return pivot.reindex(columns=factor_names).T


def _partial_years(yearly: pd.DataFrame) -> set[int]:
    if "is_partial_year" in yearly.columns:
        partial = yearly.loc[yearly["is_partial_year"].fillna(False).astype(bool), "year"]
        return {int(year) for year in partial}
    years = pd.to_numeric(yearly["year"], errors="coerce").dropna()
    if years.empty:
        return set()
    latest_year = int(years.max())
    return {latest_year} if latest_year == datetime.now(UTC).year else set()


def _year_tick_labels(years: list[int], partial_years: set[int]) -> list[str]:
    return [f"{year}\n年初至今" if int(year) in partial_years else str(year) for year in years]


def _plot_yearly_return_heatmap(
    ax: plt.Axes,
    fig: plt.Figure,
    return_matrix: pd.DataFrame,
    *,
    partial_years: set[int],
) -> float:
    """Render the factor-by-year return matrix with missing periods masked."""
    years = list(return_matrix.columns)
    factor_names = list(return_matrix.index)
    values = return_matrix.to_numpy(dtype=float)
    finite_abs = np.abs(values[np.isfinite(values)])
    color_limit = max(10.0, float(np.percentile(finite_abs, 95))) if finite_abs.size else 10.0
    cmap = plt.get_cmap("RdBu_r").with_extremes(bad="#292c42")
    image = ax.imshow(
        np.ma.masked_invalid(values),
        cmap=cmap,
        vmin=-color_limit,
        vmax=color_limit,
        aspect="auto",
    )
    ax.set_xticks(np.arange(len(years)))
    ax.set_xticklabels(
        _year_tick_labels(years, partial_years),
        fontproperties=CJK,
        fontsize=8,
    )
    ax.set_yticks(np.arange(len(factor_names)))
    ax.set_yticklabels(
        [FACTOR_LABELS[name] for name in factor_names],
        fontproperties=CJK,
        fontsize=9,
    )
    for row_index, row in enumerate(values):
        for column_index, value in enumerate(row):
            if not np.isfinite(value):
                ax.add_patch(
                    Rectangle(
                        (column_index - 0.5, row_index - 0.5),
                        1,
                        1,
                        facecolor="#292c42",
                        edgecolor="#666b82",
                        hatch="////",
                        linewidth=0.35,
                    )
                )
                continue
            ax.text(
                column_index,
                row_index,
                f"{value:+.0f}",
                ha="center",
                va="center",
                fontsize=6.5,
                color="white" if abs(value) >= color_limit * 0.55 else "#222",
            )
    ax.set_xticks(np.arange(-0.5, len(years), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(factor_names), 1), minor=True)
    ax.grid(which="minor", color="#4a4e64", linewidth=0.3)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.legend(
        handles=[Patch(facecolor="#292c42", edgecolor="#666b82", hatch="////", label="无数据")],
        loc="upper left",
        bbox_to_anchor=(0, 1.06),
        prop=CJK,
        frameon=False,
    )
    ax.set_title("逐年风格因子期间收益热力图", fontproperties=CJK, fontsize=14, pad=18)
    colorbar = fig.colorbar(image, ax=ax, shrink=0.85, pad=0.015)
    colorbar.set_label("收益（%）", fontproperties=CJK)
    return color_limit


def _plot_best_yearly_factors(
    ax: plt.Axes,
    yearly: pd.DataFrame,
    years: list[int],
    return_column: str,
    *,
    partial_years: set[int],
) -> None:
    """Render the strongest available factor for each calendar year."""
    x = np.arange(len(years))
    best_returns: list[float] = []
    best_labels: list[str] = []
    for year in years:
        row = yearly[yearly["year"] == year]
        row = row.loc[pd.to_numeric(row[return_column], errors="coerce").notna()]
        if row.empty:
            best_returns.append(float("nan"))
            best_labels.append("")
            continue
        best = row.nlargest(1, return_column).iloc[0]
        best_returns.append(float(best[return_column]))
        best_labels.append(FACTOR_LABELS.get(best["factor"], ""))

    colors = ["#c86f62" if value < 0 else "#47a6a0" for value in best_returns]
    ax.bar(x, best_returns, color=colors, alpha=0.8)
    for index, (factor_label, value) in enumerate(zip(best_labels, best_returns, strict=True)):
        if not np.isfinite(value):
            ax.text(
                index,
                0,
                "无数据",
                ha="center",
                va="bottom",
                fontproperties=CJK,
                fontsize=8,
                color="#999",
            )
            continue
        ax.text(
            index,
            value + (1 if value >= 0 else -3),
            f"{factor_label}\n{value:+.1f}%",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontproperties=CJK,
            fontsize=8,
            color=FG,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(
        _year_tick_labels(years, partial_years),
        fontproperties=CJK,
        fontsize=8,
    )
    ax.axhline(0, color="#777b8f", linewidth=0.7)
    ax.grid(axis="y", color="#44485e", linewidth=0.45, alpha=0.55)
    ax.set_ylabel("收益（%）", fontproperties=CJK)
    ax.set_title("每年最强因子", fontproperties=CJK, fontsize=14)


def _write_yearly_chart_contract(
    *,
    yearly: pd.DataFrame,
    return_matrix: pd.DataFrame,
    outdir: Path,
    color_limit: float,
    partial_years: set[int],
) -> tuple[Path, Path]:
    matrix_path = outdir / "style_factor_yearly_matrix.csv"
    metadata_path = outdir / "style_factor_yearly.meta.json"
    matrix = return_matrix.rename_axis("factor").reset_index()
    matrix.insert(1, "factor_label", matrix["factor"].map(FACTOR_LABELS))
    matrix.to_csv(matrix_path, index=False)
    finite = return_matrix.to_numpy(dtype=float)
    metadata = {
        "schema_version": YEARLY_CHART_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "question": "各风格因子逐年收益如何变化，每年表现最强的因子是什么？",
        "return_unit": "percent",
        "return_column": ("period_return" if "period_return" in yearly.columns else "annual_ret"),
        "year_min": int(min(return_matrix.columns)),
        "year_max": int(max(return_matrix.columns)),
        "partial_years": sorted(partial_years),
        "factor_count": len(return_matrix.index),
        "missing_cells": int(np.isnan(finite).sum()),
        "color_scale": {
            "kind": "symmetric_diverging",
            "limit_percent": round(color_limit, 6),
            "limit_method": "max(10, finite absolute return p95)",
        },
        "outputs": {
            "png": "style_factor_yearly.png",
            "svg": "style_factor_yearly.svg",
            "matrix_csv": matrix_path.name,
        },
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return matrix_path, metadata_path


def plot_yearly_barchart(yearly: pd.DataFrame, outdir: Path) -> YearlyChartArtifacts | None:
    """Yearly return heatmap plus the strongest factor for each year."""
    if yearly.empty:
        return None

    outdir.mkdir(parents=True, exist_ok=True)
    return_column = "period_return" if "period_return" in yearly.columns else "annual_ret"
    return_matrix = _yearly_return_matrix(yearly)
    if return_matrix.empty:
        return None
    years = list(return_matrix.columns)
    partial_years = _partial_years(yearly)

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(18, 13),
        gridspec_kw={"height_ratios": [2.2, 1]},
    )
    color_limit = _plot_yearly_return_heatmap(
        axes[0],
        fig,
        return_matrix,
        partial_years=partial_years,
    )
    _plot_best_yearly_factors(
        axes[1],
        yearly,
        years,
        return_column,
        partial_years=partial_years,
    )

    fig.tight_layout()
    png_path = outdir / "style_factor_yearly.png"
    svg_path = outdir / "style_factor_yearly.svg"
    fig.savefig(png_path, dpi=180, facecolor=BG, bbox_inches="tight")
    fig.savefig(svg_path, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    matrix_path, metadata_path = _write_yearly_chart_contract(
        yearly=yearly,
        return_matrix=return_matrix,
        outdir=outdir,
        color_limit=color_limit,
        partial_years=partial_years,
    )
    print(f"[chart] yearly → {png_path} / {svg_path}")
    return YearlyChartArtifacts(
        png=png_path,
        svg=svg_path,
        matrix_csv=matrix_path,
        metadata_json=metadata_path,
    )
