# Documentation lifecycle

> status: active
> owner: workspace
> last_verified: 2026-06-04
> source_of_truth: yes
> superseded_by: n/a

本页定义顶层文档的生命周期字段和归档判断。它只约束 `research-workspace`
这一层；子仓库仍在自己的 `docs/README.md`、`AGENTS.md` 和测试中维护更细的文档规则。

## Status block

入口文档、归档记录和兼容页应在标题后放一个短状态块：

```text
> status: active | reference | archived | superseded
> owner: workspace | market-data-platform | cross-sectional-trees | quant-execution-engine
> last_verified: YYYY-MM-DD
> source_of_truth: yes | no
> superseded_by: n/a | <relative path>
```

含义：

| 字段 | 用途 |
| --- | --- |
| `status` | `active` 是当前操作入口，`reference` 是稳定参考，`archived` 是历史记录，`superseded` 是兼容跳转页。 |
| `owner` | 谁负责业务含义和后续更新；跨仓库页面写 `workspace`。 |
| `last_verified` | 最近一次检查链接、contract 名称和市场称谓的日期。 |
| `source_of_truth` | 是否是当前权威入口。兼容页和历史记录通常写 `no`。 |
| `superseded_by` | 被替代时写当前入口；未替代写 `n/a`。 |

## Active inventory

当前顶层 active / reference 入口应保持很薄：

| 主题 | 当前入口 | 生命周期 |
| --- | --- | --- |
| 新机器初始化 | [bootstrap.md](bootstrap.md) | active |
| 跨仓库工作流 | [platform-workflow.md](platform-workflow.md) | active |
| 文件 contract | [contracts.md](contracts.md) | reference |
| A 股迁移和港股恢复顺序 | [data-transition-playbook.md](data-transition-playbook.md) | active |
| 中国香港市场归档路由 | [archive/hk/README.md](archive/hk/README.md) | active archive entry |
| 版本组合 | [version-matrix.md](version-matrix.md) | reference |
| 发布检查 | [release-checklist.md](release-checklist.md) | active |
| 工作区维护 | [workspace-maintenance.md](workspace-maintenance.md) | active |
| 治理清单 | [maintainability-governance.md](maintainability-governance.md), [quality-governance.md](quality-governance.md), [deprecations.md](deprecations.md) | reference |

## Archive inventory

一次性记录默认进入 [archive/](archive/)：

| 类型 | 当前入口 |
| --- | --- |
| 中国香港市场冷存储、restore、public/private split 和 cleanup gate | [archive/hk/README.md](archive/hk/README.md) |
| 冻结 release note、session handoff 和历史复核记录 | `archive/hk/records/` |
| 证据 JSON | `evidence/`，由对应脚本或 manifest 引用 |

## Compatibility stubs

以下页面保留是为了旧链接、测试和人工查找不断裂，但不是新的权威入口：

| 旧入口 | 当前权威入口 |
| --- | --- |
| [hk-legacy-surface-inventory.md](hk-legacy-surface-inventory.md) | [archive/hk/README.md](archive/hk/README.md), [hk-public-split-manifest.yml](hk-public-split-manifest.yml) |
| [hk-private-archive.md](hk-private-archive.md) | [archive/hk/README.md](archive/hk/README.md), [hk-private-archive-manifest.yml](hk-private-archive-manifest.yml) |
| [hk-public-demo-export.md](hk-public-demo-export.md) | [archive/hk/README.md](archive/hk/README.md), [hk-public-split-manifest.yml](hk-public-split-manifest.yml) |
| [a-share-production-readiness.md](a-share-production-readiness.md) | [data-transition-playbook.md](data-transition-playbook.md#a-股-readiness-分层) |

## Routing rules

- 新人 30 分钟内需要读的当前路径留在 active docs。
- 跨仓库 contract、release gate 和 doctor 依赖的页面保留为 active 或 reference。
- 一次性 handoff、freeze note、release note、历史复查和恢复演练进入 archive records。
- Manifest 已记录的 inventory 不在 Markdown 里重复维护长表；Markdown 只解释边界并链接 manifest。
- 超过 300 行且需要人工持续维护的文档，应拆分、生成，或降级到 archive。
- 旧称 `metadata/current_assets/cn_current.json` 只能作为历史兼容 alias 说明；当前 A 股 canonical contract 是 `metadata/current_assets/a_share_current.json`。
