# 港股公开 demo clean-room export

港股公开展示库使用独立 clean-room export，不从历史仓库直接推送 Git 历史，也不作为
workspace submodule。当前 staging 目标是：

```text
https://github.com/runchengxie/hk-cross-sectional-strategy-demo
license: MIT
maintenance: paused
```

发布必须由维护者在检查 staged tree 后显式执行。本工作区脚本不会创建远端仓库或 push。
本工作区只把该仓库作为外部作品集 reference 链接，不把它加入 required submodule。
它也不参与顶层 CI、release matrix、version matrix 或日常 `run_submodule_checks.py` profile。

## Staging model

`demo/hk-public-demo-template-v1/` 是未来独立公开仓库的 staging tree。它只放 synthetic
fixture、public-safe demo 代码、独立 docs、archive placeholder、最小 CI 和质量配置。
不要把真实港股业务实现原样搬入 demo。

迁出、归档、保留和禁止公开的 surface 由
[`hk-public-split-manifest.yml`](hk-public-split-manifest.yml) 记录。manifest 使用
`keep_in_main`、`move_to_public_demo`、`archive_in_public_demo`、`delete_after_split` 和
`private_do_not_export` 分类；删除主项目兼容入口仍需要后续变更和 gate evidence。
Deprecated 入口的具体 removal milestone 和测试要求见
[`deprecations.md`](deprecations.md)。

## 导出

```bash
python scripts/export_hk_public_demo.py --out /tmp/hk-cross-sectional-strategy-demo
```

版本化 allowlist 位于 `demo/hk-public-demo-allowlist-v1.txt`。模板只包含 synthetic fixture、
离线 workflow、样例输出生成器、架构说明、免责声明、MIT license 和最小 CI。

导出器会：

1. 仅复制 allowlist 文件，不复制 `.git`。
2. 运行 synthetic workflow，生成 `samples/summary.json` 与 `samples/targets.json`。
3. 运行标准库 `unittest` smoke。
4. 运行 demo-local quality check，确认 active demo 代码不 import workspace package，并带有
   Ruff / Pyright 配置。
5. 扫描凭证、`.env*`、provider cache、Parquet、私有输出、本地绝对路径、压缩包、超大文件、
   broker/provider runtime import 和 workspace import。
6. 写入 `export-manifest.json`，记录 source revision、纳入文件、生成文件、split manifest、
   扫描、quality 和 smoke 结果。

审查任意 staged tree：

```bash
python scripts/export_hk_public_demo.py --scan-only /tmp/hk-cross-sectional-strategy-demo
```

## 发布前 review

维护者 push 到公开仓库前必须确认：

- `export-manifest.json` 存在，且 `scan.status` 为 `passed`。
- `offline_smoke.status` 为 `passed`，并包含 demo workflow 与 `unittest` 结果。
- `quality_checks.status` 为 `passed`。
- `split_manifest.validation.status` 为 `passed`，且包含 public demo staging 相关 record。
- `python scripts/export_hk_public_demo.py --scan-only <staging-dir>` 通过。
- `python scripts/run_quality_checks.py --profile secrets --demo-stage <staging-dir>` 通过。
- staged tree 只包含 allowlist 文件、synthetic sample 输出和 `export-manifest.json`。
- staged tree 不包含 `.git`、真实行情、provider cache、Parquet、pickle、压缩包、私有输出、
  本地绝对路径或超大文件。
- 人工敏感词复核已完成，至少覆盖：

```text
token
secret
password
api_key
access_key
rqdata
tushare
longport
ibkr
alpaca
/home/
Users/
parquet
pickle
zst
tar
zip
```

公开仓库创建、首次 push、是否立即 GitHub archive，以及后续是否保留 paused-maintenance 状态，
都由维护者在 GitHub 侧手动完成；工作区脚本不自动操作远端。

2026-06-01 的最新离线复核 staging 位于：

```text
/tmp/hk-cross-sectional-strategy-demo-verify-20260601-maintenance
export-manifest.json: scan=passed, offline_smoke=passed
```

## 边界

- 不包含真实行情、RQData / TuShare 数据、provider cache、凭证或历史收益宣传。
- 不包含券商 adapter，不声称可用于真实交易。
- 不与 A 股主项目双向同步需求；它是暂停维护的作品集展示和历史 reference。
- 不作为 workspace submodule、包依赖、必跑 CI 项或 release gate。
- 不作为删除 restore-sensitive 港股代码的充分条件；删除仍按 split manifest gate 和后续变更执行。
