# 废弃入口登记

本页记录废弃兼容入口的删除状态。登记记录本身不授权删除；删除前必须满足 [`deprecations.yml`](deprecations.yml) 中的证据要求，并通过 [`hk-public-split-manifest.yml`](hk-public-split-manifest.yml) 中的拆分门禁。

## 当前记录

| 入口 | 负责仓库 | 替代入口 | 状态 | 目标里程碑 |
| --- | --- | --- | --- | --- |
| `hkdata` | `market-data-platform` | `marketdata` | removed | completed 2026-06-13 |
| `src/hk_data_platform/*` | `market-data-platform` | `market_data_platform` public modules | removed | completed 2026-06-13 |
| `rqdata-hk-depth` | `market-data-platform` | `marketdata rqdata hk-depth -- ...` | removed | completed 2026-06-13 |
| `rqdata-tick` | `market-data-platform` | `marketdata rqdata hk-depth -- ...` | removed | completed 2026-06-13 |
| `rqdata-hk-assets` | `market-data-platform` | `marketdata rqdata hk-assets -- ...` | removed | completed 2026-06-13 |
| `cstree alloc-hk` | `cross-sectional-trees` | `cstree alloc` plus `cstree export-targets` | removed | CLI removed 2026-06-13; `alloc_hk` module follow-up tracked in split manifest |
| HK historical configs | `cross-sectional-trees` | `configs/presets/hk.yml` plus archive evidence | follow-up required | after archive manifest remains current |

## 删除门禁

只有下列证据齐全后，才能把废弃入口标记为可进入删除评审：

- 下游或仓库内使用审计；
- 替代入口文档；
- 回滚路径；
- 负责仓库中的 focused tests；
- restore-sensitive 入口需要恢复证据。

实际删除必须在负责仓库内做 focused verification，并把结果写回本页和 YAML 清单。

私有 legacy archive staging 不授权删除。删除评审前，运行 `python scripts/hk_archive_gate.py --check --format json`，并保留 [archive/hk/README.md](archive/hk/README.md) 链接到的私有 staging、restore drill、consumer audit、source tag 和 zero-usage release window 证据。
