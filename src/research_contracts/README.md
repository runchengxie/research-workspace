# research-contracts

`research-contracts` 是 `research-workspace` 与下游产品仓库共享的轻量契约包。它只包含
artifact envelope、schema、SHA-256、lineage、研究时钟、运行清单和文件清单校验，不包含研究算法、
数据访问或运行时凭证。

## 发布方式

本包不发布到包索引。它作为 `research-workspace` 仓库的 Git 子目录随仓库一起版本化，消费方
从 Git 安装并锁定不可变提交：

```text
research-contracts @ git+https://github.com/runchengxie/research-workspace.git@<commit>#subdirectory=src/research_contracts
```

使用 `uv` 时在 `pyproject.toml` 中声明为 git source：

```toml
dependencies = ["research-contracts>=0.1.0"]

[tool.uv.sources]
research-contracts = { git = "https://github.com/runchengxie/research-workspace.git", rev = "<commit>", subdirectory = "src/research_contracts" }
```

每次合约变更先合并到 `research-workspace` 的 `main`，消费方再升级锁定到新的不可变提交。
`<commit>` 必须是 `main` 上可达的提交，不能指向功能分支的临时提交。

## 消费范围

`research-contracts` 由 artifact producer 和顶层工作区消费：

- 顶层工作区使用 `smoke_contracts.py` 校验 `docs/artifact-contracts.yml` 与
  `docs/contracts.md` 的一致性。
- 生产方（`alpha-research`、`portfolio-backtester`、`strategy-pipeline`）安装本包后，
  通过 `research_contracts` 公开 API 写入 `research.artifact-envelope.v2`。
- 研究编排方可以使用 `research.clock.v1` 固化一次运行的信息可见、信号、决策、执行窗口和估值时点，
  并使用 `research.backtest-run.v1` 只引用数据、信号、组合结果和证据 artifact，而不复制业务大表。
- 各仓库不得复制或重写 envelope、研究时钟、根运行清单、SHA-256 和 lineage 校验逻辑。需要扩展契约时，
  修改本包并更新锁定提交。

## 研究时钟

`ResearchClock` 只维护跨仓库需要共享的因果顺序，不负责解析交易日历，也不决定成交算法。
所有时间戳必须带时区。普通诊断可以缺少执行窗口；声明为 `execution_aware` 的运行必须提供
`earliest_order_at`、`execution_window_start_at` 和 `execution_window_end_at`。

```python
from research_contracts import ResearchClock

clock = ResearchClock.from_mapping(
    {
        "schema_version": "research.clock.v1",
        "timezone": "Asia/Shanghai",
        "information_cutoff_at": "2026-09-02T15:00:00+08:00",
        "signal_at": "2026-09-02T15:01:00+08:00",
        "decision_at": "2026-09-02T15:02:00+08:00",
        "earliest_order_at": "2026-09-03T09:15:00+08:00",
        "execution_window_start_at": "2026-09-03T09:30:00+08:00",
        "execution_window_end_at": "2026-09-03T10:00:00+08:00",
        "valuation_at": "2026-09-03T15:00:00+08:00",
        "timing_policy_id": "a-share.close-next-open.v1",
        "trading_calendar_ref": "sse-szse-20260902",
    }
)
```

## 根运行清单

`ResearchRunManifest` 是一次研究的根 lineage。它只保存稳定引用和 SHA-256，不重新定义数据、信号、
组合或会计结果。`evidence_tier` 第一版只允许 `diagnostic` 与 `execution_aware`。后者会要求完整
`ResearchClock` 执行窗口。

`research.backtest-run.v1` 目前只发布 schema 与校验器。等 `strategy-pipeline` 的真实 producer 和
`portfolio-backtester` 的 canonical bundle 落地后，再把该 artifact 加入 `docs/artifact-contracts.yml`，
避免在 registry 中登记不存在的 producer entrypoint。

## Artifact Envelope 使用示例

```python
from research_contracts import (
    ArtifactEnvelopeV2,
    ProducerIdentity,
    LineageInput,
    attach_artifact_envelope_v2,
    file_sha256,
)

envelope = ArtifactEnvelopeV2(
    artifact_id="signals-20260713-demo",
    artifact_type="signals.parquet",
    run_id="run-20260713-demo",
    created_at=datetime.now(timezone.utc),
    producer=ProducerIdentity(
        repository="alpha-research",
        version="0.4.0",
        commit="0123456789abcdef",
        backend="native",
    ),
    configuration_sha256=config_hash,
    content_sha256=file_sha256(parquet_path),
    lineage=(LineageInput("research_features.parquet", feature_hash),),
)
payload = attach_artifact_envelope_v2(legacy_metadata, envelope)
```
