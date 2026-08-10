#!/usr/bin/env python3
"""Build the unified benchmark exam table (benchmark_matrix.v1) from raw results.

The exam table aggregates backtest results over four axes: universe, horizon,
regime and cost. A single backtest point estimate cannot satisfy the exam: the
table must cover at least two distinct axes. This matches the ``benchmark_matrix``
check enforced by ``scripts/strategy_evidence_gate.py``.

Input rows format (``benchmark_rows.v1``):

    {"rows": [
      {"universe": "csi300", "horizon": "h5", "regime": "bull", "cost_bps": 20, "sharpe": 0.7},
      {"universe": "csi500", "horizon": "h5", "regime": "bull", "cost_bps": 20, "sharpe": 1.1}
    ]}

Output is a ``benchmark_matrix.v1`` object whose ``cells`` list is directly
compatible with the evidence gate's ``benchmark_matrix`` entry.

Exit codes:
- 0: matrix built and, with ``--check``, spans at least two axes
- 1: input is invalid, rows are inconsistent, or ``--check`` fails
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

AXES = ("universe", "horizon", "regime", "cost_bps")
MATRIX_VERSION = "benchmark_matrix.v1"
ROWS_VERSION = "benchmark_rows.v1"


def _load_rows(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("输入必须是 JSON 对象")
    return payload


def _row_issue(row: dict[str, Any], metric: str) -> str | None:
    for axis in AXES:
        value = row.get(axis)
        if value is None or (isinstance(value, str) and not value.strip()):
            return f"缺少维度 {axis}"
    if not isinstance(row.get(metric), (int, float)) or isinstance(row.get(metric), bool):
        return f"缺少数值指标 {metric}"
    return None


def _validate_rows(payload: dict[str, Any], metric: str) -> list[str]:
    issues: list[str] = []
    if payload.get("schema_version") != ROWS_VERSION:
        issues.append(f"schema_version 必须是 {ROWS_VERSION}")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        issues.append("rows 必须是列表")
        return issues
    if not rows:
        issues.append("rows 不能为空")
        return issues
    seen: set[tuple[Any, ...]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            issues.append(f"第 {index} 行必须是对象")
            continue
        typed_row = cast(dict[str, Any], row)
        issue = _row_issue(typed_row, metric)
        if issue:
            issues.append(f"第 {index} 行 {issue}")
            continue
        key = tuple(typed_row[axis] for axis in AXES)
        if key in seen:
            issues.append(f"第 {index} 行与前面某行在四个维度上重复")
        seen.add(key)
    return issues


def _build_cells(rows: list[dict[str, Any]], metric: str) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for row in rows:
        cell = {axis: row[axis] for axis in AXES}
        cell[metric] = row[metric]
        cells.append(cell)
    return cells


def _span_axes(cells: list[dict[str, Any]], metric: str) -> int:
    return sum(
        1
        for axis in AXES
        if len({cell.get(axis) for cell in cells if cell.get(axis) is not None}) > 1
    )


def _matrix_from_rows(payload: dict[str, Any], metric: str) -> dict[str, Any]:
    rows = payload["rows"]
    cells = _build_cells(rows, metric)
    return {
        "schema_version": MATRIX_VERSION,
        "metric": metric,
        "axes": list(AXES),
        "cells": cells,
    }


def _check_matrix(matrix: dict[str, Any]) -> tuple[bool, str]:
    cells = matrix.get("cells")
    if not isinstance(cells, list) or len(cells) < 2:
        return False, "cells 不足两条，禁止用单点结果当考试表"
    span = _span_axes(cells, str(matrix.get("metric", "sharpe")))
    if span < 2:
        return False, "cells 未覆盖至少两个维度（universe、horizon、regime、cost_bps）"
    return True, f"考试表覆盖 {span} 个维度、{len(cells)} 条结果"


def _render(matrix: dict[str, Any], *, as_json: bool) -> str:
    if as_json:
        return json.dumps(matrix, ensure_ascii=False, indent=2)
    lines = [f"指标：{matrix['metric']}"]
    lines.append(f"维度：{', '.join(matrix['axes'])}")
    lines.append(f"单元格：{len(matrix['cells'])} 条")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--metric", default="sharpe")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not args.input.is_file():
        print(f"缺少输入文件：{args.input}", file=sys.stderr)
        return 1
    payload = _load_rows(args.input)
    issues = _validate_rows(payload, args.metric)
    if issues:
        for issue in issues:
            print(f"[ERROR] {issue}", file=sys.stderr)
        return 1

    matrix = _matrix_from_rows(payload, args.metric)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(matrix, ensure_ascii=False, indent=2) + "\n"
        args.output.write_text(payload, encoding="utf-8")

    if args.check:
        ok, message = _check_matrix(matrix)
        print(f"[{'OK' if ok else 'ERROR'}] {message}")
        return 0 if ok else 1

    print(_render(matrix, as_json=args.as_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
