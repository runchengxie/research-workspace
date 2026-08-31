"""Build a read-only inventory of data paths and their lifecycle semantics."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_CANONICAL: dict[str, tuple[list[str], str, str]] = {
    "raw": (["raw"], "已统一", "按原始数据保留策略管理，不做通用清理"),
    "staging": (["staging"], "已统一", "终态 receipt、替代版本和锁状态决定后续动作"),
    "published": (["published"], "已统一", "先校验，再通过 current 或发布契约提供给消费者"),
    "current": (["current"], "已统一", "保护稳定入口，不直接删除或改写"),
    "rollback": (["rollback"], "已统一", "保护可回滚版本，按回滚策略复核"),
    "archive": (["archive"], "已统一", "按归档 manifest 和 retention 决定是否继续保留"),
    "cache": (["cache"], "已统一", "确认可重建且无运行占用后再清理"),
    "reports": (["reports"], "已统一", "按报告引用和 retention 审查历史版本"),
    "runs": (["runs"], "已统一", "按运行状态和 receipt 保留"),
    "experiments": (["experiments"], "已统一", "固定时点研究快照，不能按普通缓存处理"),
}

_MIXED: dict[str, tuple[list[str], str, str]] = {
    "assets": (
        ["raw", "published", "current", "rollback"],
        "兼容保留",
        "按供应商、派生资产和 alias 分层迁移",
    ),
    "metadata": (
        ["current", "rollback", "archive", "receipts"],
        "拆分待审",
        "按契约、凭证和归档元数据分别归类",
    ),
    "metadata/minute_candidate": (
        ["staging", "receipts"],
        "拆分待审",
        "按候选资产、检查结果和运行凭证分别归类",
    ),
    "metadata/industry-changes-backups": (
        ["archive"],
        "拆分待审",
        "确认有替代清单后再缩短保留期",
    ),
    "strategy_inputs": (
        ["published", "features"],
        "拆分待审",
        "按生产方和消费者确认输入还是研究特征",
    ),
    "strategy_outputs": (
        ["runs", "features", "snapshots", "reports", "receipts"],
        "拆分待审",
        "不能整体改名，保留 latest 和兼容 symlink",
    ),
    "research": (
        ["experiments", "features", "reports", "receipts"],
        "拆分待审",
        "按 notebook、结果、报告和凭证分别归类",
    ),
    "artifacts": (
        ["runs", "reports", "snapshots", "cache", "receipts"],
        "拆分待审",
        "父目录是历史总称，按子目录核对 manifest",
    ),
}


def classify_path(path: str) -> dict[str, Any]:
    """Return the canonical classification for a relative data path."""

    normalized = path.strip("/").replace("\\", "/")
    if normalized in _CANONICAL:
        terms, status, action = _CANONICAL[normalized]
    elif normalized in _MIXED:
        terms, status, action = _MIXED[normalized]
    elif normalized == "current_assets" or normalized.endswith("/current_assets"):
        terms, status, action = ["current"], "兼容保留", "这是当前读取契约，不能直接改名或删除"
    elif normalized == "archive" or normalized.endswith("/archive"):
        terms, status, action = ["archive"], "归档保留", "保留归档凭证，按 retention 复核"
    elif normalized == "latest" or normalized.endswith("/latest"):
        terms, status, action = ["current"], "兼容保留", "保护 latest alias，消费者迁移前不得删除"
    else:
        terms, status, action = ["待分类"], "拆分待审", "补充 manifest、owner 和消费者后再决定迁移"
    return {"canonical_terms": terms, "status": status, "action": action}


def _kind(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "other"


def _summary(path: Path) -> tuple[int, int]:
    if path.is_symlink() or path.is_file():
        return (1, path.stat().st_size) if path.is_file() else (0, 0)
    files = 0
    bytes_total = 0
    for root, directories, names in os.walk(path, followlinks=False):
        directories[:] = [name for name in directories if not (Path(root) / name).is_symlink()]
        for name in names:
            candidate = Path(root) / name
            if candidate.is_symlink() or not candidate.is_file():
                continue
            files += 1
            bytes_total += candidate.stat().st_size
    return files, bytes_total


def _entry(path: Path, relative: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": relative,
        "object_kind": _kind(path),
        **classify_path(relative),
        "file_count": 0,
        "byte_count": 0,
    }
    if path.is_symlink():
        result["target"] = os.readlink(path)
    else:
        result["file_count"], result["byte_count"] = _summary(path)
    return result


def scan_data_root(root: Path) -> dict[str, Any]:
    """Scan direct data-root entries without following symlinks."""

    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"data root is not a directory: {root}")
    children = sorted(root.iterdir(), key=lambda item: item.name)
    entries = [_entry(child, child.name) for child in children]
    return {
        "schema_version": "research_workspace.data_path_audit.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "root": str(root),
        "read_only_scan": True,
        "entries": entries,
    }


def write_inventory(output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_inventory(args.output, scan_data_root(args.data_root))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
