# 中国香港市场私有 legacy 归档

> status: superseded
> owner: workspace
> last_verified: 2026-06-10
> source_of_truth: no
> superseded_by: archive/hk/README.md

本页保留给旧链接和操作速查。当前权威入口是
[中国香港市场归档](archive/hk/README.md)，真实业务代码的私有归档清单由
[hk-private-archive-manifest.yml](hk-private-archive-manifest.yml) 管理。

## 当前边界

- 私有候选仓库仍是 `hk-quant-legacy-archive`，必须保持 private、paused-maintenance、restore-only。
- 私有归档可以保留清单约束下的 provider 业务代码、历史配置和测试。
- 公开 demo 只承接 synthetic / public-safe clean-room 示例。
- 两条路径都不承接凭证、行情文件、provider cache、研究 run、券商 adapter 或交易审计日志。
- 私有 staging、restore drill 或 consumer audit 通过，都不自动授权删除活跃仓库中的 restore-sensitive 代码。

## 操作入口

只读检查：

```bash
python scripts/hk_archive_gate.py --check --format json
```

在工作区外 staging：

```bash
python scripts/export_hk_legacy_archive.py \
  --out /tmp/hk-quant-legacy-archive-stage

python scripts/hk_archive_gate.py \
  --check \
  --export-manifest /tmp/hk-quant-legacy-archive-stage/archive-export-manifest.json \
  --format json
```

exporter 只从 manifest 中 pin 的 Git revision 导出 allowlist 文件并生成 SHA-256；它不复制
`.git`，不创建远端仓库，不修改 submodule，不删除源文件。

## 删除门禁

删除或迁出兼容入口前，先从 [archive/hk/README.md](archive/hk/README.md) 进入当前 gate，
并确认下列证据齐全：

- restore evidence；
- consumer audit；
- replacement docs；
- rollback notes；
- owning repo focused tests；
- private staging 证据；
- zero-usage release window。

LongPort、标准 `targets.json` 多市场解析、FX、dry-run、风控、审计，以及
`marketdata migration freeze-hk` / `hydrate-hk` 控制面继续保留在活跃仓库。
