# 港股兼容面清单

> status: superseded
> owner: workspace
> last_verified: 2026-06-10
> source_of_truth: no
> superseded_by: archive/hk/README.md

本页保留给旧链接。当前权威入口是 [中国香港市场归档](archive/hk/README.md)；
repo-local surface、public safety、consumer audit、replacement path 和 removal condition
由 [hk-public-split-manifest.yml](hk-public-split-manifest.yml) 记录。

相关机器可读清单：

| 清单 | 用途 |
| --- | --- |
| [hk-public-split-manifest.yml](hk-public-split-manifest.yml) | public demo 路线退役记录、归档、删除门禁和 restore-sensitive surface |
| [hk-private-archive-manifest.yml](hk-private-archive-manifest.yml) | 私有 paused-maintenance legacy archive staging 和删除门禁 |
| [deprecations.md](deprecations.md) | deprecated 入口 owner、replacement、milestone 和删除门禁 |

## 快速分类

| 分类 | 含义 | 当前处理 |
| --- | --- | --- |
| `shared_active` | 多市场 contract、执行或恢复能力仍需要 | 保留并继续跑 focused tests |
| `frozen_compatibility` | 港股复现或明确跟踪需求仍可能调用 | 保留入口，标记 deprecated，不扩展 A 股主线 |
| `archived_provenance` | 只用于解释历史研究和 release | 通过归档记录或 manifest 追溯 |
| `retire_after_audit` | 已有替代入口，但仍需下游使用审计 | 审计和回滚证据完成后在 follow-up change 删除 |

## 删除门禁

当前没有 restore-sensitive 或 compatibility surface 在本轮直接删除。后续若删除
`hkdata`、`hk_data_platform.*`、`rqdata-hk-*`、`cstree alloc-hk` 或港股历史配置，需要先在
`hk-public-split-manifest.yml` 中把对应记录推进到 deletion gate `ready`，并补齐：

- restore evidence；
- downstream consumer audit；
- replacement docs；
- rollback notes；
- owning repo focused tests；
- public demo 路线已退役，不再新增 public split evidence 要求。

港股 run / sweep / report / live / benchmark / export 产物已经迁出活跃研究线；仓库中仍保留的
港股配置、历史笔记和工具入口只作为 `archived_provenance` 或 `frozen_compatibility`
兼容面存在。
