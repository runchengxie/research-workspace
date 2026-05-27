# 版本矩阵

本页记录已经验证或正在验证的工作区版本组合。这里是人工审计记录；真正锁定版本的仍是 Git 子模块指针。

## 当前检出状态

截至 2026-05-27，本地检出状态如下。`cross-sectional-trees` 和 `market-data-platform` 有未提交改动，所以这组组合只代表当前本地工作状态，发布前需要先处理这些改动。

| 顶层仓库 | market-data-platform | cross-sectional-trees | rqdata-hk-depth-snapshots | quant-execution-engine | 状态 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| `f38ce4c` | `a310a80` + 本地改动 | `10ca23f` + 本地改动 | `bb83c3b` | `85ad0e7` | 本地工作状态 | 当前可用于继续联调；发布前需要清理或提交子模块改动 |

## 已验证组合

| 日期 | 顶层仓库提交 | market-data-platform | cross-sectional-trees | rqdata-hk-depth-snapshots | quant-execution-engine | 验证状态 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-05-27 | `f38ce4c` | `a310a80` | `10ca23f` | `bb83c3b` | `85ad0e7` | 部分验证 | 已验证研究系统导出目标持仓文件，以及执行引擎解析文件并生成离线调仓计划；模拟盘持续联调证据仍需补齐 |

## 更新方法

先生成当前版本矩阵：

```bash
python scripts/print_version_matrix.py
```

然后根据实际验证结果填写：

- 是否只验证了解析或预演流程。
- 是否验证了模拟盘端到端流程。
- 是否涉及实盘；实盘状态只能按人工监督下的真实结果填写。
- 子模块是否存在未提交改动；如存在，请标为本地工作状态，发布前先清理或提交。
