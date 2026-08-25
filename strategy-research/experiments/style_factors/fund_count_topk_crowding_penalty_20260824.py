"""Top-K and controlled fund-count crowding-penalty experiment.

This diagnostic extends the full-market fund-count Final-OOS ablation:

* compare Top-5, Top-20, and Top-30 portfolios;
* keep the technical XGB model fixed;
* compare a model feature arm with an explicit negative crowding penalty;
* residualize fund-count crowding against point-in-time size, 20-day average
  traded amount, and point-in-time SW2021 L3 industry.

The penalty is deliberately applied after the technical model prediction.  A
date-wise percentile score is used so the penalty strength is interpretable:

    selection_score = rank(prediction) - lambda * rank(crowding)

No lambda is selected from Final OOS; 0.25 is the primary pre-declared
strength and 0.50 is a sensitivity check.

This script is research evidence only.  It does not modify production
configuration or write a strategy-pipeline artifact.
"""

from __future__ import annotations

import argparse
import json
import math
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

from alpha_research.modeling import build_model, fit_model
from alpha_research.split import build_sample_weight

import fund_count_final_oos_ablation_20260824 as base


DATA_ROOT = base.DATA_ROOT
DAILY_DIR = base.DAILY_DIR
INDUSTRY_FILE = (
    DATA_ROOT
    / "assets/tushare/a_share/industry_changes/"
    "a_share_all_industry_changes_sw2021_l3_20260708/data/part.parquet"
)
DEFAULT_PANEL = (
    Path(tempfile.gettempdir()) / "fund_count_final_oos_ablation_20260824/raw_panel.parquet"
)
DEFAULT_OUTPUT = Path(tempfile.gettempdir()) / "fund_count_topk_crowding_penalty_20260824"

TOP_KS = (5, 20, 30)
PENALTY_LAMBDAS = (0.25, 0.50)
COST_BPS_GRID = (10.0, 20.0, 30.0)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(pd.Timestamp(value))
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    return value


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _attach_adv20_amount(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Attach formation-date 20-trading-day average amount.

    ``amount`` in the daily-clean asset is in thousand CNY.  The unit does
    not affect the log/rank controls, but is retained in the metadata.
    """

    out = panel.copy()
    adv20 = pd.Series(np.nan, index=out.index, dtype=float)
    files = {path.stem: path for path in DAILY_DIR.glob("*.parquet")}
    missing_symbols: list[str] = []
    for symbol, indices in out.groupby("symbol", sort=False).groups.items():
        path = files.get(str(symbol))
        if path is None:
            missing_symbols.append(str(symbol))
            continue
        daily = pd.read_parquet(path, columns=["trade_date", "amount"])
        if daily.empty:
            missing_symbols.append(str(symbol))
            continue
        daily["trade_date"] = base._parse_date_series(daily["trade_date"])
        daily = daily.dropna(subset=["trade_date"]).drop_duplicates("trade_date")
        daily = daily.sort_values("trade_date")
        amount = pd.to_numeric(daily["amount"], errors="coerce")
        daily["adv20_amount"] = amount.rolling(20, min_periods=10).mean()
        lookup = daily.set_index("trade_date")["adv20_amount"]
        dates = pd.to_datetime(out.loc[indices, "trade_date"])
        adv20.loc[indices] = dates.map(lookup).to_numpy(dtype=float)

    out["adv20_amount"] = adv20
    return out, {
        "daily_amount_unit": "thousand_cny",
        "window": 20,
        "min_periods": 10,
        "coverage": float(adv20.notna().mean()),
        "missing_symbol_count": len(missing_symbols),
        "missing_symbols_sample": missing_symbols[:20],
    }


def _load_industry() -> pd.DataFrame:
    if not INDUSTRY_FILE.exists():
        raise FileNotFoundError(f"PIT industry asset not found: {INDUSTRY_FILE}")
    industry = pd.read_parquet(INDUSTRY_FILE)
    required = {"symbol", "effective_date", "end_date", "industry_name"}
    missing = required - set(industry.columns)
    if missing:
        raise ValueError(f"Industry asset missing columns: {sorted(missing)}")
    industry["symbol"] = industry["symbol"].astype(str).str.strip()
    industry["effective_date"] = (
        pd.to_datetime(industry["effective_date"], errors="coerce")
        .dt.normalize()
        .astype("datetime64[ns]")
    )
    industry["end_date"] = (
        pd.to_datetime(industry["end_date"], errors="coerce")
        .dt.normalize()
        .astype("datetime64[ns]")
    )
    industry = industry.dropna(subset=["symbol", "effective_date", "industry_name"])
    industry = industry.sort_values(["symbol", "effective_date"])
    industry = industry.drop_duplicates(["symbol", "effective_date"], keep="last")
    return industry[["symbol", "effective_date", "end_date", "industry_name"]].copy()


def _attach_pit_industry(
    panel: pd.DataFrame, industry: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """As-of attach the SW2021 L3 industry interval to each panel row."""

    out = panel.copy()
    labels = pd.Series(pd.NA, index=out.index, dtype="string")
    for symbol, indices in out.groupby("symbol", sort=False).groups.items():
        right = industry.loc[industry["symbol"].eq(str(symbol))].copy()
        if right.empty:
            continue
        left = out.loc[indices, ["trade_date"]].copy()
        left["trade_date"] = pd.to_datetime(left["trade_date"]).astype(
            "datetime64[ns]"
        )
        left["_row_index"] = left.index
        left = left.sort_values("trade_date")
        right = right.sort_values("effective_date")
        merged = pd.merge_asof(
            left,
            right,
            left_on="trade_date",
            right_on="effective_date",
            direction="backward",
            allow_exact_matches=True,
        )
        valid = merged["effective_date"].notna() & (
            merged["end_date"].isna() | (merged["trade_date"] <= merged["end_date"])
        )
        labels.loc[merged.loc[valid, "_row_index"].astype(int)] = merged.loc[
            valid, "industry_name"
        ].astype(str).to_numpy()

    out["industry_l3"] = labels
    return out, {
        "industry_file": str(INDUSTRY_FILE),
        "industry_rows": int(len(industry)),
        "industry_symbols": int(industry["symbol"].nunique()),
        "industry_levels": int(industry["industry_name"].nunique()),
        "panel_coverage": float(labels.notna().mean()),
    }


def _fill_control_medians(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in ("circ_mv", "adv20_amount"):
        out[column] = pd.to_numeric(out[column], errors="coerce")
        by_date = out.groupby("trade_date")[column].transform("median")
        global_median = float(out[column].median()) if out[column].notna().any() else 0.0
        out[column] = out[column].fillna(by_date).fillna(global_median)
    out["industry_l3"] = out["industry_l3"].astype("string").fillna("__UNKNOWN__")
    return out


def _residualize_crowding(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Remove size, liquidity and industry effects from log fund count."""

    out = _fill_control_medians(panel)
    residual = pd.Series(np.nan, index=out.index, dtype=float)
    fallback_dates = 0
    design_rows = 0
    for _date, indices in out.groupby("trade_date", sort=True).groups.items():
        group = out.loc[indices]
        y = np.log1p(
            pd.to_numeric(group["fund_count_holding_stock"], errors="coerce")
            .clip(lower=0.0)
        )
        size = np.log1p(group["circ_mv"].clip(lower=0.0))
        liquidity = np.log1p(group["adv20_amount"].clip(lower=0.0))
        valid = y.notna() & size.notna() & liquidity.notna()
        if int(valid.sum()) < 20:
            residual.loc[indices] = y - y.median()
            fallback_dates += 1
            continue

        # Percentile controls make the cross-sectional regression less
        # sensitive to the very long right tails of market cap and amount.
        controls = pd.DataFrame(
            {
                "size_rank": size.rank(method="average", pct=True),
                "liquidity_rank": liquidity.rank(method="average", pct=True),
            },
            index=group.index,
        )
        industry_dummies = pd.get_dummies(
            group["industry_l3"].astype(str), dtype=float
        )
        if industry_dummies.shape[1] > 1:
            industry_dummies = industry_dummies.iloc[:, 1:]
        x = pd.concat([controls, industry_dummies], axis=1)
        x = x.loc[valid]
        y_valid = y.loc[valid]
        design = np.column_stack([np.ones(len(x)), x.to_numpy(dtype=float)])
        try:
            beta = np.linalg.lstsq(design, y_valid.to_numpy(dtype=float), rcond=None)[0]
            fitted = design @ beta
            residual.loc[x.index] = y_valid.to_numpy(dtype=float) - fitted
            design_rows += len(x)
        except np.linalg.LinAlgError:
            residual.loc[indices] = y - y.median()
            fallback_dates += 1

    out["fund_count_crowding_raw"] = np.log1p(
        pd.to_numeric(out["fund_count_holding_stock"], errors="coerce").clip(lower=0.0)
    )
    out["fund_count_crowding_residual"] = residual
    return out, {
        "residual_target": "log1p(fund_count_holding_stock)",
        "controls": ["cross_sectional_size_rank", "cross_sectional_adv20_amount_rank", "industry_l3_fixed_effect"],
        "control_missing_fill": "date_median_then_global_median; unknown industry category",
        "fallback_dates": fallback_dates,
        "residual_design_rows": design_rows,
        "residual_coverage": float(residual.notna().mean()),
    }


def _percentile(values: pd.Series) -> pd.Series:
    if values.nunique(dropna=True) <= 1:
        return pd.Series(0.5, index=values.index, dtype=float)
    return values.rank(method="average", pct=True).astype(float)


def _fit_predictions(
    panel: pd.DataFrame,
    *,
    features: list[str],
    train_dates: list[pd.Timestamp],
    oos_dates: list[pd.Timestamp],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    work = panel.dropna(subset=[*features, "tr_close", "future_return"]).copy()
    train = work.loc[work["trade_date"].isin(train_dates)].copy()
    test = work.loc[work["trade_date"].isin(oos_dates)].copy()
    if train.empty or test.empty:
        raise RuntimeError("Empty train/test frame for prediction arm.")
    model = build_model(base.MODEL_TYPE, base.MODEL_PARAMS)
    weights = build_sample_weight(train, "date_equal")
    fit_model(
        model,
        base.MODEL_TYPE,
        train,
        features=features,
        target_col="future_return",
        sample_weight=weights,
    )
    test["pred"] = model.predict(test[features])
    y_true = test["future_return"].to_numpy(dtype=float)
    y_pred = test["pred"].to_numpy(dtype=float)
    return test, {
        "features": features,
        "feature_count": len(features),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def _max_drawdown(returns: pd.Series) -> float:
    nav = (1.0 + returns.fillna(0.0)).cumprod()
    return float((nav / nav.cummax() - 1.0).min()) if not nav.empty else float("nan")


def _score_periods(
    scored: pd.DataFrame,
    *,
    score_col: str,
    arm: str,
    top_k: int,
    oos_dates: list[pd.Timestamp],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    periods: list[dict[str, Any]] = []
    previous_names: set[str] | None = None
    oos_index = {date: i for i, date in enumerate(oos_dates)}
    for date in oos_dates:
        group = scored.loc[scored["trade_date"].eq(date)].copy()
        group = group.dropna(subset=[score_col, "future_return"])
        if group.empty:
            continue
        group = group.sort_values([score_col, "symbol"], kind="mergesort")
        buckets = pd.qcut(
            np.arange(len(group)),
            q=base.N_QUANTILES,
            labels=False,
            duplicates="drop",
        )
        group["_bucket"] = buckets
        bucket_return = group.groupby("_bucket", observed=True)["future_return"].mean()
        q1 = float(bucket_return.iloc[0])
        q5 = float(bucket_return.iloc[-1])
        rank_ic = base._safe_spearman(group[score_col], group["future_return"])
        tradable = group.loc[group["is_tradable"]].copy()
        if len(tradable) < top_k:
            tradable = group
        selected = tradable.sort_values(
            [score_col, "symbol"], ascending=[False, True]
        ).head(top_k)
        names = set(selected["symbol"])
        turnover = (
            1.0
            if previous_names is None
            else 1.0 - len(names.intersection(previous_names)) / max(top_k, 1)
        )
        previous_names = names
        amount = pd.to_numeric(selected["amount"], errors="coerce")
        capacity = amount * 1000.0 * 0.05 / (1_000_000.0 / top_k)
        periods.append(
            {
                "arm": arm,
                "top_k": top_k,
                "trade_date": date,
                "phase_index": oos_index[date],
                "n_obs": int(len(group)),
                "n_tradable": int(len(tradable)),
                "rank_ic": rank_ic,
                "q1_return": q1,
                "q5_return": q5,
                "q5_q1": q5 - q1,
                "top_k_gross_return": float(selected["future_return"].mean()),
                "top_k_positive": float(selected["future_return"].mean() > 0),
                "top_k_name_turnover": turnover,
                "top_k_median_amount_cny": float(amount.median() * 1000.0),
                "top_k_min_capacity_multiple": float(capacity.min()),
                "top_k_symbols": ",".join(sorted(names)),
            }
        )

    detail = pd.DataFrame(periods)
    if detail.empty:
        return detail, {"periods": 0, "arm": arm, "top_k": top_k}
    metrics: dict[str, Any] = {
        "arm": arm,
        "top_k": top_k,
        "periods": int(len(detail)),
        "rank_ic_mean": float(detail["rank_ic"].mean()),
        "rank_ic_median": float(detail["rank_ic"].median()),
        "rank_ic_positive_ratio": float((detail["rank_ic"] > 0).mean()),
        "q5_q1_mean": float(detail["q5_q1"].mean()),
        "q5_q1_positive_ratio": float((detail["q5_q1"] > 0).mean()),
        "top_k_gross_mean": float(detail["top_k_gross_return"].mean()),
        "top_k_positive_ratio": float(detail["top_k_positive"].mean()),
        "top_k_name_turnover_mean": float(detail["top_k_name_turnover"].mean()),
        "top_k_median_amount_cny": float(detail["top_k_median_amount_cny"].median()),
        "top_k_min_capacity_multiple_p10": float(
            detail["top_k_min_capacity_multiple"].quantile(0.10)
        ),
    }
    rank_std = detail["rank_ic"].std(ddof=1)
    metrics["rank_ic_ir"] = (
        float(metrics["rank_ic_mean"] / rank_std * math.sqrt(len(detail)))
        if rank_std > 0
        else float("nan")
    )
    net_by_cost: dict[str, dict[str, float]] = {}
    for cost_bps in COST_BPS_GRID:
        fee = detail["top_k_name_turnover"] * 2.0 * cost_bps / 10000.0
        fee = fee.copy()
        fee.iloc[0] = cost_bps / 10000.0
        net = detail["top_k_gross_return"] - fee
        mean = float(net.mean())
        std = float(net.std(ddof=1))
        total = float((1.0 + net).prod() - 1.0)
        net_by_cost[str(int(cost_bps))] = {
            "mean_period_return": mean,
            "total_return": total,
            "annualized_return": float((1.0 + total) ** (12.0 / len(net)) - 1.0)
            if 1.0 + total > 0
            else float("nan"),
            "annualized_vol": std * math.sqrt(12.0),
            "sharpe": mean / std * math.sqrt(12.0) if std > 0 else float("nan"),
            "max_drawdown": _max_drawdown(net),
            "avg_cost_drag": float(fee.mean()),
        }
        detail[f"net_return_{int(cost_bps)}bp"] = net
    metrics["cost_grid"] = net_by_cost
    return detail, metrics


def _add_phase(detail: pd.DataFrame) -> pd.DataFrame:
    if detail.empty:
        return detail
    out = detail.copy()
    n = int(out["phase_index"].max()) + 1
    labels = np.array_split(np.arange(n), 3)
    phase_map = {
        int(index): name for name, indices in zip(("early", "mid", "recent"), labels) for index in indices
    }
    out["phase"] = out["phase_index"].map(phase_map)
    return out


def _metrics_frame(metrics: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for row in metrics:
        rows.append(
            {
                "arm": row["arm"],
                "top_k": row["top_k"],
                "periods": row["periods"],
                "rank_ic_mean": row["rank_ic_mean"],
                "rank_ic_ir": row["rank_ic_ir"],
                "q5_q1_mean": row["q5_q1_mean"],
                "top_k_gross_mean": row["top_k_gross_mean"],
                "top_k_name_turnover_mean": row["top_k_name_turnover_mean"],
                "top_k_median_amount_cny": row["top_k_median_amount_cny"],
                "top_k_min_capacity_multiple_p10": row[
                    "top_k_min_capacity_multiple_p10"
                ],
                "r2": row.get("r2"),
                **{
                    f"return_{cost}bp": row["cost_grid"][cost]["total_return"]
                    for cost in ("10", "20", "30")
                },
                **{
                    f"sharpe_{cost}bp": row["cost_grid"][cost]["sharpe"]
                    for cost in ("10", "20", "30")
                },
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel-path", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if not args.panel_path.exists():
        raise FileNotFoundError(
            f"Base raw panel not found: {args.panel_path}. Run the prior ablation first."
        )
    raw_panel = pd.read_parquet(args.panel_path)
    raw_panel, adv_meta = _attach_adv20_amount(raw_panel)
    industry = _load_industry()
    raw_panel, industry_meta = _attach_pit_industry(raw_panel, industry)
    raw_panel, residual_meta = _residualize_crowding(raw_panel)
    raw_panel.to_parquet(args.output_dir / "controlled_raw_panel.parquet", index=False)

    transformed, transform_meta = base._prepare_model_panel(raw_panel)
    complete_dates = base._complete_model_dates(transformed, base.TECH_FEATURES)
    oos_len = max(1, int(math.floor(len(complete_dates) * base.OOS_SIZE)))
    oos_dates = complete_dates[-oos_len:]
    train_dates = complete_dates[:-oos_len]

    common = {
        "complete_dates": len(complete_dates),
        "complete_start": str(complete_dates[0].date()),
        "complete_end": str(complete_dates[-1].date()),
        "oos_len": oos_len,
        "oos_start": str(oos_dates[0].date()),
        "oos_end": str(oos_dates[-1].date()),
        "train_len": len(train_dates),
        "train_end": str(train_dates[-1].date()),
    }

    baseline_test, baseline_meta = _fit_predictions(
        transformed,
        features=base.TECH_FEATURES,
        train_dates=train_dates,
        oos_dates=oos_dates,
    )
    fund_test, fund_model_meta = _fit_predictions(
        transformed,
        features=base.TECH_FEATURES + ["fund_count_holding_stock"],
        train_dates=train_dates,
        oos_dates=oos_dates,
    )

    scored_arms: dict[str, pd.DataFrame] = {
        "baseline": baseline_test,
        "model_plus_fund_count": fund_test,
    }
    for lambda_value in PENALTY_LAMBDAS:
        score_frame = baseline_test.copy()
        score_frame["_pred_rank"] = score_frame.groupby("trade_date")["pred"].transform(_percentile)
        score_frame["_raw_crowding_rank"] = score_frame.groupby("trade_date")[
            "fund_count_crowding_raw"
        ].transform(_percentile)
        score_frame["_residual_crowding_rank"] = score_frame.groupby("trade_date")[
            "fund_count_crowding_residual"
        ].transform(_percentile)
        score_frame["score_raw_penalty"] = score_frame["_pred_rank"] - lambda_value * score_frame[
            "_raw_crowding_rank"
        ]
        score_frame["score_residual_penalty"] = score_frame["_pred_rank"] - lambda_value * score_frame[
            "_residual_crowding_rank"
        ]
        scored_arms[f"penalty_raw_{lambda_value:g}"] = score_frame.copy()
        scored_arms[f"penalty_residual_{lambda_value:g}"] = score_frame.copy()

    all_metrics: list[dict[str, Any]] = []
    details: list[pd.DataFrame] = []
    for arm, frame in scored_arms.items():
        if arm == "baseline" or arm == "model_plus_fund_count":
            score_col = "pred"
        elif arm.startswith("penalty_raw_"):
            score_col = "score_raw_penalty"
        else:
            score_col = "score_residual_penalty"
        for top_k in TOP_KS:
            detail, metrics = _score_periods(
                frame,
                score_col=score_col,
                arm=arm,
                top_k=top_k,
                oos_dates=oos_dates,
            )
            metrics["score_col"] = score_col
            metrics["r2"] = (
                baseline_meta["r2"]
                if arm != "model_plus_fund_count"
                else fund_model_meta["r2"]
            )
            all_metrics.append(metrics)
            details.append(detail)

    metrics_frame = _metrics_frame(all_metrics)
    metrics_frame.to_csv(args.output_dir / "metrics.csv", index=False)
    periods = _add_phase(pd.concat(details, ignore_index=True))
    periods.to_csv(args.output_dir / "periods.csv", index=False)

    quality = {
        "panel_path": str(args.panel_path),
        "panel_rows": len(raw_panel),
        "panel_symbols": int(raw_panel["symbol"].nunique()),
        "panel_dates": int(raw_panel["trade_date"].nunique()),
        "fund_missing_share": {
            col: float(raw_panel[col].isna().mean()) for col in base.FUND_FEATURES
        },
        "adv20": adv_meta,
        "industry": industry_meta,
        "residualization": residual_meta,
        "top_ks": TOP_KS,
        "penalty_lambdas": PENALTY_LAMBDAS,
        "cost_bps_grid": COST_BPS_GRID,
    }
    _write_json(quality, args.output_dir / "quality.json")
    summary = {
        "runner": str(Path(__file__)),
        "common_split": common,
        "baseline_model": baseline_meta,
        "fund_model": fund_model_meta,
        "transform": transform_meta,
        "quality": quality,
        "metrics": all_metrics,
        "outputs": {
            "metrics": str(args.output_dir / "metrics.csv"),
            "periods": str(args.output_dir / "periods.csv"),
            "quality": str(args.output_dir / "quality.json"),
        },
    }
    _write_json(summary, args.output_dir / "summary.json")
    print(f"[done] outputs={args.output_dir}", flush=True)
    print(metrics_frame.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
