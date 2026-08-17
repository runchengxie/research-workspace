# research-contracts

`research-contracts` 是 `research-workspace` 与下游产品仓库共享的轻量契约包。它只包含
artifact envelope、schema、SHA-256、lineage 和文件清单校验，不包含研究算法、数据访问或运行时
凭证。

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
- 各仓库不得复制或重写 envelope schema、SHA-256 和 lineage 校验逻辑。需要扩展契约时，
  修改本包并更新锁定提交。

## 使用示例

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