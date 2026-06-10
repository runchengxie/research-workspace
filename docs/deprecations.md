# 废弃入口登记

本页记录仍留在活跃仓库中的废弃兼容入口。登记记录本身不授权删除；删除前必须满足 [`deprecations.yml`](deprecations.yml) 中的证据要求，并通过 [`hk-public-split-manifest.yml`](hk-public-split-manifest.yml) 中的拆分门禁。

## 当前记录

| 入口 | 负责仓库 | 替代入口 | 状态 | 目标里程碑 |
| --- | --- | --- | --- | --- |
| `hkdata` | `market-data-platform` | `marketdata` | blocked pending audit | two releases after zero usage |
| `src/hk_data_platform/*` | `market-data-platform` | `market_data_platform` public modules | blocked pending audit | two releases after clean import audit |
| `rqdata-hk-depth` | `market-data-platform` | `marketdata rqdata hk-depth -- ...` | blocked pending audit | two releases after migration guide |
| `rqdata-tick` | `market-data-platform` | `marketdata rqdata hk-depth -- ...` | blocked pending audit | two releases after migration guide |
| `rqdata-hk-assets` | `market-data-platform` | `marketdata rqdata hk-assets -- ...` | blocked pending audit | two releases after migration guide |
| `cstree alloc-hk` | `cross-sectional-trees` | `cstree alloc` plus `cstree export-targets` | blocked pending audit | after restore drill and consumer audit |
| HK historical configs | `cross-sectional-trees` | `configs/presets/hk.yml` plus archive evidence | follow-up required | after archive manifest remains current |

## 删除门禁

只有下列证据齐全后，才能把废弃入口标记为可进入删除评审：

- 下游或仓库内使用审计；
- 替代入口文档；
- 回滚路径；
- 负责仓库中的 focused tests；
- restore-sensitive 入口需要恢复证据。

实际删除必须放在后续变更中完成，并在负责仓库内做 focused verification。

私有 legacy archive staging 不授权删除。删除评审前，运行 `python scripts/hk_archive_gate.py --check --format json`，并保留 [archive/hk/README.md](archive/hk/README.md) 链接到的私有 staging、restore drill、consumer audit、source tag 和 zero-usage release window 证据。
