# 港股公开 demo clean-room export

> status: superseded
> owner: workspace
> last_verified: 2026-06-04
> source_of_truth: no
> superseded_by: archive/hk/README.md

本页保留给旧链接和导出命令速查。当前权威入口是
[中国香港市场归档](archive/hk/README.md)，迁出、归档、保留和禁止公开的 surface 由
[hk-public-split-manifest.yml](hk-public-split-manifest.yml) 记录。

公开展示库仍是工作区外的 clean-room export：

```text
https://github.com/runchengxie/hk-cross-sectional-strategy-demo
license: MIT
maintenance: paused
```

发布必须由维护者在检查 staged tree 后显式执行。本工作区脚本不会创建远端仓库或 push，
也不会把 demo 加入 submodule、CI、release matrix、version matrix 或日常检查。

## Staging model

`demo/hk-public-demo-template-v1/` 只放 synthetic fixture、public-safe demo 代码、独立 docs、
archive placeholder、最小 CI 和质量配置。不要把真实港股业务实现原样搬入 demo。

## 导出和复核

导出：

```bash
python scripts/export_hk_public_demo.py --out /tmp/hk-cross-sectional-strategy-demo
```

审查任意 staged tree：

```bash
python scripts/export_hk_public_demo.py --scan-only /tmp/hk-cross-sectional-strategy-demo
```

发布前至少确认：

- `export-manifest.json` 存在，且 `scan.status` 为 `passed`。
- `offline_smoke.status`、`quality_checks.status` 和 `split_manifest.validation.status` 均为 `passed`。
- `python scripts/run_quality_checks.py --profile secrets --demo-stage <staging-dir>` 通过。
- staged tree 只包含 allowlist 文件、synthetic sample 输出和 `export-manifest.json`。
- staged tree 不包含 `.git`、真实行情、provider cache、Parquet、pickle、压缩包、私有输出、
  本地绝对路径、超大文件、broker/provider runtime import 或 workspace import。

## 边界

- 不包含真实行情、RQData / TuShare 数据、provider cache、凭证或历史收益宣传。
- 不包含券商 adapter，不声称可用于真实交易。
- 不作为 workspace submodule、包依赖、必跑 CI 项或 release gate。
- 不作为删除 restore-sensitive 港股代码的充分条件；删除仍按 split manifest gate 和后续变更执行。
