"""Shared helpers for style_factors dataset loaders.

These helpers resolve on-disk parquet layouts and read hive-partitioned
daily datasets without any tushare network traffic.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PARTITION_PREFIX = "trade_date="


def _coerce_date(value: str | pd.Timestamp | None) -> pd.Timestamp | None:
    if value is None:
        return None
    return pd.to_datetime(value)


def _partition_date(path: Path) -> pd.Timestamp | None:
    if not path.name.startswith(PARTITION_PREFIX):
        return None
    raw = path.name.split("=", 1)[1]
    return pd.to_datetime(raw, format="%Y%m%d", errors="coerce")


def _filter_partition_paths(
    parts: list[Path],
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
) -> list[Path]:
    start = _coerce_date(start_date)
    end = _coerce_date(end_date)
    selected: list[Path] = []
    for path in parts:
        date = _partition_date(path)
        if date is None or pd.isna(date):
            selected.append(path)
            continue
        if start is not None and date < start:
            continue
        if end is not None and date > end:
            continue
        selected.append(path)
    return selected


def _read_partitioned_parquet(parts: list[Path], *, label: str) -> pd.DataFrame:
    if not parts:
        raise FileNotFoundError(f"No parquet partitions found for {label}")
    frames = []
    for path in parts:
        df = pd.read_parquet(path)
        if "trade_date" not in df.columns:
            # Hive-partitioned dir without an in-file trade_date column:
            # recover it from the trade_date=YYYYMMDD directory name.
            dt = _partition_date(path)
            if dt is not None and not pd.isna(dt):
                df = df.assign(trade_date=dt)
        if "trade_date" in df.columns:
            df["trade_date"] = pd.to_datetime(df["trade_date"])
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _latest_data_dir(data_root: Path, dataset: str, legacy_sub: str | None = None) -> Path | None:
    """Resolve the ``data`` directory of a ``*_latest`` dataset under a_share.

    Accepts the several on-disk layouts seen on the data platform:
    ``<dataset>/a_share_all_<dataset>_latest/data``,
    ``<dataset>/<dataset>_latest/data``, ``<dataset>/data``, and an explicit
    ``legacy_sub`` path.  A directory qualifies if it contains either parquet
    files or ``trade_date=`` hive partitions.  Returns ``None`` otherwise.
    """
    base = data_root / "assets/tushare/a_share" / dataset
    candidates = []
    if legacy_sub is not None:
        candidates.append(base / legacy_sub)
    candidates.extend(
        [
            base / f"a_share_all_{dataset}_latest" / "data",
            base / f"{dataset}_latest" / "data",
            base / "data",
        ]
    )
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        if sorted(candidate.glob("*.parquet")) or sorted(candidate.glob(f"{PARTITION_PREFIX}*")):
            return candidate
    return None
