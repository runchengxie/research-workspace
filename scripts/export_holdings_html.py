#!/usr/bin/env python3
"""将最新持仓导出为独立 HTML 文件。

用法：
    cd strategy-pipeline
    uv run python ../scripts/export_holdings_html.py [--out holdings.html]

默认读取 latest.json 指向的最新 run 的 positions_current_live.csv，
结合 instruments parquet（名称）和 eval_scored.parquet（SW 二级行业）生成 HTML。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

# --- 路径默认值 ---
DEFAULT_RUNS_DIR = Path(__file__).resolve().parent.parent / "strategy-pipeline/artifacts/runs"
DEFAULT_LATEST_JSON = DEFAULT_RUNS_DIR / "latest.json"
DEFAULT_INSTRUMENTS_PARQUET = Path(
    "/home/richard/data/market-data-platform/assets/tushare/a_share/instruments/"
    "a_share_all_instruments_latest.parquet"
)

# --- HTML 模板 ---
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>A 股策略持仓 — {entry_date}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
      "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: #0d1117; color: #c9d1d9; padding: 2rem;
  }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; color: #f0f6fc; }}
  .meta {{ font-size: 0.85rem; color: #8b949e; margin-bottom: 1.5rem; }}
  .meta span {{ margin-right: 1.5rem; }}
  table {{
    width: 100%; border-collapse: collapse; font-size: 0.92rem;
  }}
  th {{
    text-align: left; padding: 8px 12px; border-bottom: 2px solid #30363d;
    color: #8b949e; font-weight: 600; font-size: 0.82rem; text-transform: uppercase;
  }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #21262d; }}
  tr:hover td {{ background: #161b22; }}
  .rank {{ color: #8b949e; width: 3rem; }}
  .symbol {{ font-family: "SF Mono", "Fira Code", monospace; font-weight: 600; color: #58a6ff; }}
  .name {{ font-weight: 500; }}
  .industry {{ color: #7ee787; font-size: 0.85rem; }}
  .weight {{ font-family: "SF Mono", "Fira Code", monospace; color: #d2a8ff; }}
  .footer {{
    margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #21262d;
    font-size: 0.78rem; color: #484f58;
  }}
</style>
</head>
<body>
<div class="container">
  <h1>A 股策略持仓</h1>
  <div class="meta">
    <span>调仓日：{entry_date}</span>
    <span>信号日：{signal_date}</span>
    <span>持仓数：{n_holdings} 只</span>
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th><th>代码</th><th>名称</th><th>行业</th><th>权重</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
  <div class="footer">
    数据来源：strategy-pipeline 实时快照 · 行业分类：申万二级 · 仅供研究参考，不构成投资建议
  </div>
</div>
</body>
</html>"""

ROW_TEMPLATE = """\
      <tr>
        <td class="rank">{rank}</td>
        <td class="symbol">{symbol}</td>
        <td class="name">{name}</td>
        <td class="industry">{industry}</td>
        <td class="weight">{weight}</td>
      </tr>"""


def _resolve_run_dir(latest_json: Path) -> Path:
    """从 latest.json 解析最新 run 目录。"""
    if not latest_json.exists():
        raise SystemExit(f"latest.json 不存在: {latest_json}")
    data = json.loads(latest_json.read_text(encoding="utf-8"))
    run_dir = data.get("run_dir")
    if not run_dir:
        raise SystemExit("latest.json 缺少 run_dir 字段")
    run_path = Path(run_dir)
    if not run_path.exists():
        raise SystemExit(f"run 目录不存在: {run_path}")
    return run_path


def _load_positions(run_dir: Path) -> pd.DataFrame:
    """读取 positions_current_live.csv。"""
    path = run_dir / "positions_current_live.csv"
    if not path.exists():
        raise SystemExit(f"positions 文件不存在: {path}")
    return pd.read_csv(path)


def _load_summary(run_dir: Path) -> dict:
    """读取 summary.json 获取信号日等信息。"""
    path = run_dir / "summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_names(instruments_path: Path) -> dict[str, str]:
    """从 instruments parquet 加载 symbol -> name 映射。"""
    if not instruments_path.exists():
        print(f"[warn] instruments parquet 不存在: {instruments_path}，名称列将留空")
        return {}
    df = pd.read_parquet(instruments_path, columns=["symbol", "name"])
    return dict(zip(df["symbol"], df["name"]))


def _load_industries(run_dir: Path) -> dict[str, str]:
    """从 eval_scored.parquet 取每只股票最新的 SW 二级行业。"""
    path = run_dir / "eval_scored.parquet"
    if not path.exists():
        print(f"[warn] eval_scored.parquet 不存在: {path}，行业列将留空")
        return {}
    df = pd.read_parquet(path, columns=["symbol", "trade_date", "second_industry_name"])
    if df.empty:
        return {}
    df = df.dropna(subset=["second_industry_name"])
    if df.empty:
        return {}
    # 每只股票取最新 trade_date 的行业
    idx = df.groupby("symbol")["trade_date"].idxmax()
    latest = df.loc[idx]
    return dict(zip(latest["symbol"], latest["second_industry_name"]))


def _parse_yyyymmdd(series: pd.Series) -> pd.Series:
    """将 YYYYMMDD 整数列解析为 datetime。"""
    s = series.astype(str).str.strip()
    return pd.to_datetime(s, format="%Y%m%d", errors="coerce")


def _select_holdings(df: pd.DataFrame) -> pd.DataFrame:
    """筛选最新 entry_date 的持仓，按 rank 排序。"""
    if "entry_date" not in df.columns:
        raise SystemExit("positions CSV 缺少 entry_date 列")
    df["_entry_dt"] = _parse_yyyymmdd(df["entry_date"])
    latest_entry = df["_entry_dt"].max()
    sel = df[df["_entry_dt"] == latest_entry].copy()
    if sel.empty:
        raise SystemExit("未找到有效持仓")
    if "rank" in sel.columns:
        sel = sel.sort_values("rank")
    sel = sel.reset_index(drop=True)
    return sel


def _format_weight(w: float) -> str:
    try:
        pct = float(w) * 100
        return f"{pct:.2f}%"
    except (TypeError, ValueError):
        return "—"


def _parse_date(val) -> str:
    """将日期值转为 YYYY-MM-DD 字符串。支持 YYYYMMDD 整数和字符串。"""
    if val is None:
        return "—"
    try:
        s = str(int(val))
        return pd.Timestamp(s).strftime("%Y-%m-%d")
    except Exception:
        pass
    try:
        return pd.Timestamp(str(val)).strftime("%Y-%m-%d")
    except Exception:
        return str(val)


def build_html(
    positions: pd.DataFrame,
    names: dict[str, str],
    industries: dict[str, str],
    signal_date: str,
    entry_date: str,
) -> str:
    rows_html: list[str] = []
    for _, row in positions.iterrows():
        symbol = str(row.get("symbol", ""))
        rank = int(row["rank"]) if pd.notna(row.get("rank")) else "—"
        name = names.get(symbol, "—")
        industry = industries.get(symbol, "—")
        weight = _format_weight(row.get("weight"))
        rows_html.append(
            ROW_TEMPLATE.format(
                rank=rank,
                symbol=symbol,
                name=name,
                industry=industry,
                weight=weight,
            )
        )

    return HTML_TEMPLATE.format(
        entry_date=entry_date,
        signal_date=signal_date,
        n_holdings=len(positions),
        rows="\n".join(rows_html),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="将最新持仓导出为 HTML")
    parser.add_argument(
        "--out", default=None, help="输出 HTML 文件路径（默认：打印到 stdout）"
    )
    parser.add_argument(
        "--latest-json", default=str(DEFAULT_LATEST_JSON),
        help="latest.json 路径",
    )
    parser.add_argument(
        "--instruments", default=str(DEFAULT_INSTRUMENTS_PARQUET),
        help="instruments parquet 路径",
    )
    args = parser.parse_args()

    latest_json = Path(args.latest_json)
    instruments_path = Path(args.instruments)

    run_dir = _resolve_run_dir(latest_json)
    print(f"[info] run dir: {run_dir}", flush=True)

    positions = _load_positions(run_dir)
    print(f"[info] positions 行数: {len(positions)}", flush=True)

    summary = _load_summary(run_dir)
    # 提取 signal_asof 日期 (从 summary 的 data.end_date 推断或 positions 列)
    signal_date = _parse_date(
        positions["signal_asof"].iloc[0]
        if "signal_asof" in positions.columns and pd.notna(positions["signal_asof"].iloc[0])
        else summary.get("data", {}).get("end_date", "—")
    )

    holdings = _select_holdings(positions)
    entry_date = _parse_date(holdings["_entry_dt"].iloc[0])
    print(f"[info] entry_date={entry_date}, holdings={len(holdings)}", flush=True)

    names = _load_names(instruments_path)
    print(f"[info] 名称映射: {len(names)} 条", flush=True)

    industries = _load_industries(run_dir)
    print(f"[info] 行业映射: {len(industries)} 条", flush=True)

    html = build_html(holdings, names, industries, signal_date, entry_date)

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        print(f"[done] 已写入 {out_path}")
    else:
        print(html)


if __name__ == "__main__":
    main()
