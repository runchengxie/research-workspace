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
| `cstree alloc-hk` | `cross-sectional-trees` | `cstree alloc` plus `cstree export-targets` | removed | CLI and `alloc_hk` modules removed 2026-06-13 |
| HK historical experiment configs | `cross-sectional-trees` | `docs/archive/research/hk/configs/experiments` plus explicit restore presets | removed | active experiment configs archived 2026-06-13 |

## 删除门禁

只有下列证据齐全后，才能把废弃入口标记为可进入删除评审：

- 下游或仓库内使用审计；
- 替代入口文档；
- 回滚路径；
- 负责仓库中的 focused tests；
- restore-sensitive 入口需要恢复证据。

实际删除必须在负责仓库内做 focused verification，并把结果写回本页和 YAML 清单。2026-06-13 的策略研究清理已把 `cstree alloc-hk`、`alloc_hk` 模块、HK research implementation modules 和活跃 HK experiment configs 移出活跃区；保留的 HK preset / field profile 只作为显式恢复或历史解释入口。

私有 legacy archive staging 不授权删除。删除评审前，运行 `python scripts/hk_archive_gate.py --check --format json`，并保留 [archive/hk/README.md](archive/hk/README.md) 链接到的私有 staging、restore drill、consumer audit、source tag 和 zero-usage release window 证据。
