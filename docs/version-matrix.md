# Version Matrix

本文件记录已验证或待验证的 workspace commit 组合。它是人工审计记录，不替代 Git submodule 指针。

## Current Checkout

截至 2026-05-27，本地 checkout 状态如下。`cross-sectional-trees` 和 `market-data-platform` 当前存在未提交改动，因此该组合只能视为本地工作态，不能直接标记为 release-ready。

| workspace | market-data-platform | cross-sectional-trees | rqdata-hk-depth-snapshots | quant-execution-engine | 状态 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| `f38ce4c` | `a310a80` + local changes | `10ca23f` + local changes | `bb83c3b` | `85ad0e7` | local working checkout | 当前可用于继续联调；发布前需要清理或提交 submodule 改动 |

## Verified Combinations

| 日期 | workspace commit | market-data-platform | cross-sectional-trees | rqdata-hk-depth-snapshots | quant-execution-engine | 验证状态 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-05-27 | `f38ce4c` | `a310a80` | `10ca23f` | `bb83c3b` | `85ad0e7` | partial | README / workflow 文档已声明研究到执行交接和离线计划验证；paper broker 持续联调证据仍需补齐 |

## Update Procedure

更新本文件时建议先生成当前矩阵：

```bash
python scripts/print_version_matrix.py
```

然后根据实际验证结果填写：

- 是否只验证了 parser / dry-run。
- 是否验证了 paper broker 端到端流程。
- 是否涉及 live，只能写人工监督下的真实状态，不能用顶层脚本默认化。
- submodule 是否 dirty；dirty checkout 不应作为 release-ready 组合。
