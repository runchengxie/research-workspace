"""SW-industry loaders — PIT membership table and the ths_member classification map.

Both loaders require NO tushare network traffic; they consume locally-landed
parquet.  ``load_sw_industry_membership`` is the authoritative PIT input for
NEUTRALIZATION; ``load_ths_member`` is a placeholder map (real industry map not
yet landed on the platform).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ._common import _latest_data_dir


def _resolve_l1_industry(member: pd.DataFrame, dict_dir: Path | None) -> pd.DataFrame:
    """Attach an ``industry_l1`` column to ``member`` using the SW dictionary.

    Resolution order: map ``industry_code`` -> L1 name via ``sw_industry``
    (level=='L1'); fall back to the raw ``industry_name`` already present on the
    member row.  Returns a copy with ``industry_l1`` populated.
    """
    member = member.copy()
    if dict_dir is not None:
        dict_files = sorted(dict_dir.glob("*.parquet")) or sorted(
            dict_dir.glob("trade_date=*/part.parquet")
        )
        if dict_files:
            industry_dict = pd.concat([pd.read_parquet(p) for p in dict_files], ignore_index=True)
            l1 = industry_dict[industry_dict.get("level", "") == "L1"]
            if not l1.empty and {"industry_code", "industry_name"} <= set(l1.columns):
                l1_map = dict(
                    zip(
                        l1["industry_code"].astype(str),
                        l1["industry_name"].astype(str),
                        strict=False,
                    )
                )
                member["industry_l1"] = member["industry_code"].astype(str).map(l1_map)
                if member["industry_l1"].isna().any() and "industry_name" in member.columns:
                    member["industry_l1"] = member["industry_l1"].fillna(
                        member["industry_name"].astype(str)
                    )
                return member
    if "industry_name" in member.columns:
        member["industry_l1"] = member["industry_name"].astype(str)
    return member


def load_sw_industry_membership(data_root: Path) -> pd.DataFrame:
    """Build a PIT (point-in-time) SW industry membership long table.

    Source: locally-landed tushare Shenwan (申万) industry datasets under
    ``assets/tushare/a_share/``:

    - ``sw_industry_member`` — constituent rows ``[index_code, con_code,
      in_date, out_date, is_new, industry_code, industry_name]``.  ``con_code``
      is the tushare ts_code (e.g. ``'000019.SZ'``), identical to the panel
      ``symbol`` format.  ``in_date``/``out_date`` form a PIT validity window;
      ``out_date=None`` means the stock is still in that industry.
    - ``sw_industry`` — the industry dictionary; we keep only ``level=='L1'``
      so each stock maps to a single L1 sector name.

    Returns a long frame ``[symbol, in_date, out_date, industry_l1]`` where
    each row is a valid (symbol, industry) interval.  ``out_date=None`` denotes
    "currently active".  Consumers should asof/interval-merge by ``trade_date``.

    This is the authoritative industry input for NEUTRALIZATION.  It is PIT —
    a stock's L1 sector is the one whose window contains the trade_date, which
    avoids look-ahead and static-map drift.  Do NOT use ``ths_member`` (static)
    for neutralization.  No tushare network traffic.
    """
    member_dir = _latest_data_dir(
        data_root,
        "sw_industry_member",
        legacy_sub="a_share_all_sw_industry_member_latest/data",
    )
    dict_dir = _latest_data_dir(
        data_root,
        "sw_industry",
        legacy_sub="a_share_all_sw_industry_latest/data",
    )
    if member_dir is None:
        print("[load] sw_industry_member: no data found — PIT industry neutralization disabled")
        return pd.DataFrame(columns=pd.Index(["symbol", "in_date", "out_date", "industry_l1"]))

    member_files = sorted(member_dir.glob("*.parquet")) or sorted(
        member_dir.glob("trade_date=*/*.parquet")
    )
    if not member_files:
        print("[load] sw_industry_member: no parquet files")
        return pd.DataFrame(columns=pd.Index(["symbol", "in_date", "out_date", "industry_l1"]))
    member = pd.concat([pd.read_parquet(p) for p in member_files], ignore_index=True)

    if "con_code" not in member.columns:
        print("[load] sw_industry_member: missing con_code column")
        return pd.DataFrame(columns=pd.Index(["symbol", "in_date", "out_date", "industry_l1"]))

    member = _resolve_l1_industry(member, dict_dir)

    member["symbol"] = member["con_code"].astype(str)
    member["in_date"] = pd.to_datetime(member["in_date"], errors="coerce")
    member["out_date"] = pd.to_datetime(member["out_date"], errors="coerce")

    out = member[["symbol", "in_date", "out_date", "industry_l1"]].dropna(
        subset=["symbol", "industry_l1"]
    )
    if out.empty:
        print("[load] sw_industry_member: no usable L1 rows")
        return out
    print(
        f"[load] sw_industry_member(PIT): {len(out)} membership rows, "
        f"{out['symbol'].nunique()} stocks, "
        f"{out['industry_l1'].nunique()} L1 industries"
    )
    return out.reset_index(drop=True)


def load_ths_member(data_root: Path) -> dict[str, str]:
    """Build a ``symbol -> industry`` classification map from ths_member/ths_index.

    NOTE (data gap): the landed ``ths_member`` table only maps constituents to the
    two all-A indices (``700001.TI`` / ``700002.TI``, ``type=BB``).  The 1077
    ths industry indices (``type=I``) have NO constituent table landed, and
    ``sw_industry`` is empty.  So a real per-stock industry map is NOT available
    locally yet.  This loader returns what the data supports — all mapped stocks
    are labelled ``"全A"`` — and exists so the rest of the pipeline can consume a
    symbol->industry dict once market-data-platform lands an industry-constituent
    dataset (e.g. sw_industry_member or a ths industry-member table).  Do NOT treat
    the returned map as a working industry neutralization input.
    """
    member_dir = _latest_data_dir(data_root, "ths_member")
    index_dir = _latest_data_dir(data_root, "ths_index")
    if member_dir is None:
        print("[load] ths_member: no data found — industry neutralization disabled")
        return {}

    member = pd.read_parquet(sorted(member_dir.glob("*.parquet"))[0])
    if "con_code" not in member.columns:
        return {}
    mapping = dict.fromkeys(member["con_code"].astype(str).unique().tolist(), "全A")
    print(
        f"[load] ths_member: {len(mapping)} symbols mapped "
        f"(placeholder '全A'; real industry map not landed)"
    )
    if index_dir is not None:
        idx = pd.read_parquet(sorted(index_dir.glob("*.parquet"))[0])
        n_industry = int((idx["type"] == "I").sum()) if "type" in idx.columns else 0
        if n_industry:
            print(
                f"[load] ths_index: {n_industry} industry indices available "
                f"but no constituent table landed — neutralization pending"
            )
    return mapping
