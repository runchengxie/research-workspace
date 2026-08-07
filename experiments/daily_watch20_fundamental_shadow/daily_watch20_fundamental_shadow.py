#!/usr/bin/env python3
"""Run the revision-safe strict-v2 DailyWatch20 quality/growth shadow."""

from __future__ import annotations

import argparse
import importlib
import inspect
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd
import yaml

from alpha_research.daily_watch20_features import (
    DEFAULT_LABEL_HORIZON_WEIGHTS,
    DailyWatch20FeatureConfig,
    build_daily_watch20_feature_frame,
)
from market_data_platform.providers.tushare_a_share_fundamentals import (
    load_pit_fundamentals_as_of_panel,
)
from strategy_pipeline.daily_watch20_ablation import (
    _attach_industries,
    _ranker_factory,
    _trailing_evaluation_dates,
)
from strategy_pipeline.daily_watch20_candidate_pool import (
    DailyWatch20CandidatePool,
    load_daily_watch20_candidate_pool,
)
from strategy_pipeline.daily_watch20_data import (
    DailyWatch20Assets,
    load_daily_watch20_daily,
    load_daily_watch20_instruments,
    resolve_daily_watch20_assets,
)
from strategy_pipeline.daily_watch20_fundamental_contract import (
    FUNDAMENTAL_EVALUATION_EXPOSURES,
    PIT_MAX_OBSERVATION_AGE_DAYS,
    PIT_SOURCE_FIELDS,
    FundamentalFeaturePanel,
    fundamental_shadow_execution_protocol,
)
from strategy_pipeline.daily_watch20_fundamental_shadow import (
    blocked_fundamental_shadow_receipt,
    build_fundamental_feature_panel_from_pit_panel,
    evaluate_fundamental_shadow_oos,
    fundamental_shadow_feature_sets,
)
from strategy_pipeline.daily_watch20_fundamental_shadow_publish import (
    FundamentalShadowPublishContext,
    freeze_fundamental_shadow_run_snapshot,
    publish_blocked_fundamental_shadow,
    publish_fundamental_shadow,
)
from strategy_pipeline.daily_watch20_market_shadow import (
    StrictV2ShadowScoringConfig,
    score_strict_v2_feature_variants,
)
from strategy_pipeline.daily_watch20_minute import load_daily_watch20_minute_features
from strategy_pipeline.daily_watch20_pipeline import (
    DailyWatch20PipelineConfig,
    _resolve_dates,
    _selection_config,
)

_RUNTIME_MODULES = {
    "alpha_feature_module": "alpha_research.daily_watch20_features",
    "alpha_oos_module": "alpha_research.daily_watch20_oos",
    "alpha_ranker_module": "alpha_research.daily_watch20",
    "alpha_statistics_module": "alpha_research.daily_watch20_statistics",
    "candidate_evaluator_module": "research_apps.daily_watch20.daily_watch20_candidate_oos",
    "candidate_reporting_module": (
        "research_apps.daily_watch20.daily_watch20_candidate_oos_reporting"
    ),
    "portfolio_guard_module": "portfolio_backtester.daily_watch20_oos",
    "portfolio_selection_module": "portfolio_backtester.daily_watch20",
    "market_data_pool_module": "market_data_platform.research_views.daily_watch20_candidate_pool",
    "market_data_pool_v2_module": (
        "market_data_platform.research_views.daily_watch20_candidate_pool_v2"
    ),
    "market_data_daily_loader_module": "market_data_platform.research_views.daily_watch20_data",
    "market_data_parquet_scanning_module": "market_data_platform.parquet_scanning",
    "market_data_runtime_memory_module": "market_data_platform.runtime_memory",
    "pit_facade_module": "market_data_platform.providers.tushare_a_share_fundamentals",
    "pit_loader_module": "market_data_platform.providers.tushare_a_share_fundamentals_pit",
    "pit_support_module": "market_data_platform.providers.tushare_a_share_fundamentals_support",
    "tushare_common_module": "market_data_platform.providers.tushare_common",
    "candidate_pool_module": "strategy_pipeline.daily_watch20_candidate_pool",
    "candidate_pool_v2_module": "strategy_pipeline.daily_watch20_candidate_pool_v2",
    "daily_data_module": "strategy_pipeline.daily_watch20_data",
    "fundamental_contract_module": "strategy_pipeline.daily_watch20_fundamental_contract",
    "fundamental_evidence_module": "strategy_pipeline.daily_watch20_fundamental_evidence",
    "fundamental_features_module": "strategy_pipeline.daily_watch20_fundamental_features",
    "fundamental_facade_module": "strategy_pipeline.daily_watch20_fundamental_shadow",
    "fundamental_publisher_module": ("strategy_pipeline.daily_watch20_fundamental_shadow_publish"),
    "fundamental_stability_module": "strategy_pipeline.daily_watch20_fundamental_stability",
    "market_shadow_module": "strategy_pipeline.daily_watch20_market_shadow",
    "minute_loader_module": "strategy_pipeline.daily_watch20_minute",
    "ranker_factory_module": "strategy_pipeline.daily_watch20_ablation",
    "selection_pipeline_module": "strategy_pipeline.daily_watch20_pipeline",
    "shadow_guard_module": "strategy_pipeline.daily_watch20_shadow_guard",
    "shadow_metrics_module": "strategy_pipeline.daily_watch20_shadow_metrics",
    "shadow_review_module": "strategy_pipeline.daily_watch20_shadow_review",
}

_WORKSPACE_RUNTIME_REPOS = (
    "alpha-research",
    "market-data-platform",
    "portfolio-backtester",
    "research-apps",
    "strategy-pipeline",
)


@dataclass(frozen=True)
class _RunEnvironment:
    execution_protocol: dict[str, Any]
    pit_asset: Path
    assets: DailyWatch20Assets
    config: DailyWatch20PipelineConfig
    start_date: str
    source_date: str
    output_root: Path
    minute_path: Path
    ths_hot_root: Path


def _manifest_summary(pit_asset: Path) -> dict[str, Any]:
    path = pit_asset / "manifest.yml"
    if not path.is_file():
        return {"asset_dir": str(pit_asset), "manifest_missing": True}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest = payload if isinstance(payload, Mapping) else {}
    return {
        "asset_dir": str(pit_asset),
        "manifest_path": str(path),
        "schema_version": manifest.get("schema_version"),
        "bundle_available_date": manifest.get("bundle_available_date"),
        "observed_vintage_dates": manifest.get("observed_vintage_dates", []),
        "source_observed_vintage_dates": manifest.get("source_observed_vintage_dates", {}),
        "freshness_policy": manifest.get("freshness_policy", {}),
        "query_end_date_is_freshness": False,
        "query_end_date": manifest.get("query_end_date"),
    }


def _publish_blocked(
    exc: Exception,
    *,
    pit_asset: Path,
    output_root: Path,
    source_date: str,
    stage: str,
    frozen_run_snapshot: Mapping[str, Any] | None = None,
) -> Path:
    audit = _manifest_summary(pit_asset) | {
        "provenance_policy": "require_observed",
        "revision_safe": False,
        "freshness_verified": False,
        "failed_stage": stage,
        "exception_type": type(exc).__name__,
        "required_contract": {
            "asset_schema_version": "tushare.a_share.fundamentals.pit.v2",
            "archived_vintage_ladder": True,
            "all_training_and_evaluation_dates_revision_covered": True,
            "max_observation_age_days": 3,
        },
    }
    if frozen_run_snapshot is not None:
        audit["frozen_run_snapshot"] = dict(frozen_run_snapshot)
    receipt = blocked_fundamental_shadow_receipt(reason=str(exc), pit_audit=audit)
    return publish_blocked_fundamental_shadow(
        receipt,
        output_root=output_root,
        source_date=source_date,
    )


def _preflight_pit(pit_asset: Path, *, source_date: str) -> None:
    panel = load_pit_fundamentals_as_of_panel(
        asset_dir=pit_asset,
        as_of_dates=[source_date],
        provenance_policy="require_observed",
        fields=["roa"],
    )
    if panel.audit.get("production_eligible") is not True:
        raise ValueError("PIT source-date vintage is not revision-safe and fresh")
    observations = panel.audit.get("observation_by_as_of_date")
    observation = observations.get(source_date) if isinstance(observations, Mapping) else None
    if not isinstance(observation, Mapping):
        raise ValueError("PIT source-date audit lacks an exact observation state")
    try:
        configured_age = int(observation.get("max_observation_age_days"))
        observed_age = int(observation.get("observation_age_days"))
    except (TypeError, ValueError) as exc:
        raise ValueError("PIT source-date freshness ages must be explicit integers") from exc
    if configured_age != PIT_MAX_OBSERVATION_AGE_DAYS:
        raise ValueError("PIT source-date max observation age is not the frozen three days")
    if not 0 <= observed_age <= PIT_MAX_OBSERVATION_AGE_DAYS:
        raise ValueError("PIT source-date observation age exceeds the frozen three days")


def _source_path(value: Any) -> Path:
    path = inspect.getsourcefile(value)
    if path is None:
        raise RuntimeError(f"cannot resolve runtime source for {value!r}")
    return Path(path).resolve()


def _loaded_workspace_runtime_code_paths(workspace_root: Path) -> dict[str, Path]:
    """Bind the bounded transitive closure already imported from workspace sources."""

    source_roots = tuple(
        (workspace_root / repository / "src").resolve() for repository in _WORKSPACE_RUNTIME_REPOS
    )
    paths: dict[str, Path] = {}
    for module_name, module in sorted(sys.modules.items()):
        try:
            source = inspect.getsourcefile(module)
        except (TypeError, OSError):
            source = None
        if source is None:
            continue
        path = Path(source).resolve()
        if not path.is_file():
            continue
        if any(path.is_relative_to(root) for root in source_roots):
            paths[f"loaded_module::{module_name}"] = path
    return paths


def _fundamental_runtime_code_paths() -> dict[str, Path]:
    repo_root = Path(__file__).resolve().parents[2]
    workspace_root = repo_root.parent
    runtime = {
        alias: _source_path(importlib.import_module(module_name))
        for alias, module_name in _RUNTIME_MODULES.items()
    }
    loaded_runtime = _loaded_workspace_runtime_code_paths(workspace_root)
    return {
        **loaded_runtime,
        **runtime,
        "runner": Path(__file__).resolve(),
        "strategy_uv_lock": repo_root / "uv.lock",
        "strategy_pyproject": repo_root / "pyproject.toml",
        "alpha_uv_lock": workspace_root / "alpha-research/uv.lock",
        "market_data_uv_lock": workspace_root / "market-data-platform/uv.lock",
        "portfolio_uv_lock": workspace_root / "portfolio-backtester/uv.lock",
        "research_apps_uv_lock": workspace_root / "research-apps/uv.lock",
    }


def _freeze_run_snapshot(
    *,
    assets: DailyWatch20Assets,
    pit_asset: Path,
    minute_path: Path,
    ths_hot_root: Path,
) -> dict[str, Any]:
    input_paths = {
        "pit_asset_tree": pit_asset,
        "daily_clean_tree": assets.daily_clean,
        "current_contract": assets.current_contract,
        "instruments": assets.instruments,
        "trade_calendar": assets.trade_cal,
        "minute_feature": minute_path,
        "ths_hot_tree": ths_hot_root,
    }
    minute_receipt = minute_path.with_suffix(".receipt.json")
    if minute_receipt.is_file():
        input_paths["minute_feature_receipt"] = minute_receipt
    if assets.minute_coverage is not None:
        input_paths["minute_source_coverage"] = assets.minute_coverage
    return freeze_fundamental_shadow_run_snapshot(
        code_paths=_fundamental_runtime_code_paths(),
        input_paths=input_paths,
        package_names=(
            "alpha-research",
            "duckdb",
            "market-data-platform",
            "numpy",
            "pandas",
            "portfolio-backtester",
            "research-apps",
            "strategy-pipeline",
            "xgboost",
        ),
    )


def _research_frame(
    assets: DailyWatch20Assets,
    config: DailyWatch20PipelineConfig,
    *,
    start_date: str,
    source_date: str,
    minute_path: Path,
    evaluation_date_count: int,
) -> tuple[pd.DataFrame, pd.DatetimeIndex, DailyWatch20FeatureConfig]:
    daily = load_daily_watch20_daily(
        assets,
        start_date=start_date,
        end_date=source_date,
        memory_limit=config.memory_limit,
        threads=config.threads,
    )
    minute = load_daily_watch20_minute_features(minute_path)
    feature_config = _fundamental_feature_config()
    frame = build_daily_watch20_feature_frame(daily, minute, config=feature_config)
    frame, industry_available = _attach_industries(frame, load_daily_watch20_instruments(assets))
    if not industry_available:
        raise RuntimeError("fundamental shadow requires instrument industries")
    evaluation_dates = _trailing_evaluation_dates(
        frame,
        as_of_date=source_date,
        count=evaluation_date_count,
    )
    return (
        _trim_training_frame(frame, evaluation_dates, config.train_window_dates),
        evaluation_dates,
        feature_config,
    )


def _fundamental_feature_config() -> DailyWatch20FeatureConfig:
    return DailyWatch20FeatureConfig(
        forward_days=5,
        minute_lag_trade_days=0,
        label_horizon_weights=DEFAULT_LABEL_HORIZON_WEIGHTS,
        include_market_shadow_features=True,
    )


def _trim_training_frame(
    frame: pd.DataFrame,
    evaluation_dates: pd.DatetimeIndex,
    train_window_dates: int | None,
) -> pd.DataFrame:
    dates = pd.DatetimeIndex(pd.to_datetime(frame["trade_date"]).unique()).sort_values()
    first_index = int(dates.searchsorted(evaluation_dates[0]))
    history = int(train_window_dates or first_index)
    start_index = max(0, first_index - history - 10)
    selected = dates[start_index : int(dates.searchsorted(evaluation_dates[-1])) + 1]
    return cast(pd.DataFrame, frame.loc[frame["trade_date"].isin(selected)]).copy()


def _load_strict_v2_pools(
    baseline_scores: pd.DataFrame,
    evaluation_dates: pd.DatetimeIndex,
    *,
    assets: DailyWatch20Assets,
    ths_hot_root: Path | None,
    minimum_symbols: int,
    snapshot_minimum_symbols: int,
) -> tuple[dict[str, DailyWatch20CandidatePool], list[dict[str, Any]]]:
    pools: dict[str, DailyWatch20CandidatePool] = {}
    statuses: list[dict[str, Any]] = []
    score_dates = pd.to_datetime(baseline_scores["trade_date"])
    for date in evaluation_dates:
        key = date.strftime("%Y%m%d")
        try:
            pool = load_daily_watch20_candidate_pool(
                assets.data_root,
                source_date=key,
                mode="ths_hot_strict_v2",
                ths_hot_root=ths_hot_root,
                ths_hot_min_symbols=minimum_symbols,
                ths_hot_snapshot_min_symbols=snapshot_minimum_symbols,
            )
            rows = baseline_scores.loc[score_dates.eq(date)]
            pool_symbols = pool.frame["symbol"].astype(str)
            intersection = int(rows["symbol"].astype(str).isin(pool_symbols).sum())
            if intersection < 20:
                raise RuntimeError(f"strict-v2 model intersection is below Top20: {intersection}")
            pools[key] = pool
            statuses.append({"source_date": key, "status": "available"})
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            statuses.append(
                {
                    "source_date": key,
                    "status": "failed",
                    "code": "strict_v2_pool_failure",
                    "message": str(exc),
                }
            )
    return pools, statuses


def _score(
    frame: pd.DataFrame,
    evaluation_dates: pd.DatetimeIndex,
    *,
    config: DailyWatch20PipelineConfig,
    feature_config: DailyWatch20FeatureConfig,
    rolling_folds: int,
) -> Any:
    selection = _selection_config(news_heat_enabled=False)
    passthrough = tuple(
        dict.fromkeys(
            (
                "first_industry_name",
                *(factor.column for factor in selection.guard_factors),
                *FUNDAMENTAL_EVALUATION_EXPOSURES,
            )
        )
    )
    return score_strict_v2_feature_variants(
        frame,
        evaluation_dates,
        StrictV2ShadowScoringConfig(
            feature_sets=fundamental_shadow_feature_sets(),
            ranker_factory=_ranker_factory(config, DEFAULT_LABEL_HORIZON_WEIGHTS, 0),
            label_col=feature_config.label_col,
            return_col=feature_config.forward_return_col,
            rolling_folds=rolling_folds,
            passthrough_columns=passthrough,
            embargo_trade_days=5,
        ),
    )


def _validate_canonical_args(args: argparse.Namespace) -> dict[str, Any]:
    protocol = fundamental_shadow_execution_protocol()
    actual = {
        "requested_evaluation_dates": args.evaluation_dates,
        "rolling_folds": args.rolling_folds,
        "train_window_dates": args.train_window_dates,
        "decay_halflife_dates": float(args.decay_halflife_dates),
        "history_calendar_days": args.history_calendar_days,
        "threads": args.threads,
        "single_side_cost_bps": float(args.single_side_cost_bps),
        "target_weight_churn_stress_bps": tuple(
            float(value) for value in args.target_weight_churn_stress_bps
        ),
        "ths_hot_min_symbols": args.ths_hot_min_symbols,
        "ths_hot_snapshot_min_symbols": args.ths_hot_snapshot_min_symbols,
    }
    for field, value in actual.items():
        if value != protocol[field]:
            raise ValueError(f"fundamental shadow CLI is not canonical: {field}")
    return protocol


def _load_feature_panel(
    frame: pd.DataFrame,
    *,
    pit_asset: Path,
) -> FundamentalFeaturePanel:
    as_of_dates = list(pd.DatetimeIndex(frame["trade_date"].unique()).strftime("%Y%m%d"))
    pit_panel = load_pit_fundamentals_as_of_panel(
        asset_dir=pit_asset,
        as_of_dates=as_of_dates,
        provenance_policy="require_observed",
        fields=PIT_SOURCE_FIELDS,
        symbols=frame["symbol"].astype(str).unique().tolist(),
    )
    return build_fundamental_feature_panel_from_pit_panel(frame, pit_panel)


def _prepare_run_environment(args: argparse.Namespace) -> _RunEnvironment:
    execution_protocol = _validate_canonical_args(args)
    pit_asset = Path(args.pit_asset).expanduser().resolve()
    assets = resolve_daily_watch20_assets(args.data_root)
    config = DailyWatch20PipelineConfig(
        data_root=assets.data_root,
        source_date=args.source_date,
        history_calendar_days=args.history_calendar_days,
        train_window_dates=args.train_window_dates,
        decay_halflife_dates=args.decay_halflife_dates,
        candidate_pool_mode="all_market",
        memory_limit=args.memory_limit,
        threads=args.threads,
    )
    if dict(config.model_params) != execution_protocol["model_params"]:
        raise ValueError("fundamental shadow model_params are not canonical")
    start_date, source_date, _ = _resolve_dates(assets, config)
    output_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root
        else assets.data_root / "strategy_outputs" / "watchlist20"
    )
    minute_path = (
        Path(args.minute_path).expanduser().resolve()
        if args.minute_path
        else output_root / "features" / "minute_daily_v1.parquet"
    )
    ths_hot_root = (
        Path(args.ths_hot_root).expanduser().resolve()
        if args.ths_hot_root
        else (
            assets.data_root / "assets/tushare/a_share/ths_hot/a_share_all_ths_hot_latest"
        ).resolve()
    )
    return _RunEnvironment(
        execution_protocol=execution_protocol,
        pit_asset=pit_asset,
        assets=assets,
        config=config,
        start_date=start_date,
        source_date=source_date,
        output_root=output_root,
        minute_path=minute_path,
        ths_hot_root=ths_hot_root,
    )


def _run(args: argparse.Namespace) -> Path:
    env = _prepare_run_environment(args)
    try:
        _preflight_pit(env.pit_asset, source_date=env.source_date)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        return _publish_blocked(
            exc,
            pit_asset=env.pit_asset,
            output_root=env.output_root,
            source_date=env.source_date,
            stage="pit_preflight",
        )
    frozen_run_snapshot = _freeze_run_snapshot(
        assets=env.assets,
        pit_asset=env.pit_asset,
        minute_path=env.minute_path,
        ths_hot_root=env.ths_hot_root,
    )
    frame, evaluation_dates, feature_config = _research_frame(
        env.assets,
        env.config,
        start_date=env.start_date,
        source_date=env.source_date,
        minute_path=env.minute_path,
        evaluation_date_count=args.evaluation_dates,
    )
    try:
        feature_panel = _load_feature_panel(frame, pit_asset=env.pit_asset)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        return _publish_blocked(
            exc,
            pit_asset=env.pit_asset,
            output_root=env.output_root,
            source_date=env.source_date,
            stage="pit_vintage_ladder",
            frozen_run_snapshot=frozen_run_snapshot,
        )
    scores = _score(
        feature_panel.frame,
        evaluation_dates,
        config=env.config,
        feature_config=feature_config,
        rolling_folds=args.rolling_folds,
    )
    pools, statuses = _load_strict_v2_pools(
        scores.scored_by_variant["Q0"],
        evaluation_dates,
        assets=env.assets,
        ths_hot_root=env.ths_hot_root,
        minimum_symbols=args.ths_hot_min_symbols,
        snapshot_minimum_symbols=args.ths_hot_snapshot_min_symbols,
    )
    result = evaluate_fundamental_shadow_oos(
        scores.scored_by_variant,
        feature_panel,
        pools,
        evaluation_dates,
        statuses,
        label_col=feature_config.label_col,
        selection_config=_selection_config(news_heat_enabled=False),
        execution_protocol=env.execution_protocol,
        target_weight_churn_stress_bps=tuple(args.target_weight_churn_stress_bps),
        single_side_cost_bps=args.single_side_cost_bps,
    )
    return publish_fundamental_shadow(
        result,
        FundamentalShadowPublishContext(
            output_root=env.output_root,
            source_date=env.source_date,
            evaluation_dates=evaluation_dates,
            pools=pools,
            pool_statuses=statuses,
            refits_by_variant=scores.refits_by_variant,
            pit_asset=env.pit_asset,
            current_contract=env.assets.current_contract,
            daily_clean=env.assets.daily_clean,
            minute_path=env.minute_path,
            rolling_folds=args.rolling_folds,
            label_profile="production_50_30_20",
            label_horizon_weights=DEFAULT_LABEL_HORIZON_WEIGHTS,
            frozen_run_snapshot=frozen_run_snapshot,
            execution_protocol=env.execution_protocol,
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pit-asset", required=True)
    parser.add_argument("--data-root")
    parser.add_argument("--output-root")
    parser.add_argument("--minute-path")
    parser.add_argument("--source-date")
    parser.add_argument("--ths-hot-root")
    parser.add_argument("--ths-hot-min-symbols", type=int, default=20)
    parser.add_argument("--ths-hot-snapshot-min-symbols", type=int, default=80)
    parser.add_argument("--evaluation-dates", type=int, default=252)
    parser.add_argument("--rolling-folds", type=int, default=3)
    parser.add_argument("--single-side-cost-bps", type=float, default=10.0)
    parser.add_argument(
        "--target-weight-churn-stress-bps", nargs="+", type=float, default=[10, 20, 30, 50]
    )
    parser.add_argument("--history-calendar-days", type=int, default=1_100)
    parser.add_argument("--train-window-dates", type=int, default=504)
    parser.add_argument("--decay-halflife-dates", type=float, default=126.0)
    parser.add_argument("--memory-limit", default="12GB")
    parser.add_argument("--threads", type=int, default=3)
    return parser


def main() -> int:
    run_dir = _run(_parser().parse_args())
    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
