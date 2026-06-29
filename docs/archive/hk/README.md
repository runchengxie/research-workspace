# 中国香港市场归档

> status: active
> owner: workspace
> last_verified: 2026-06-29
> source_of_truth: yes
> superseded_by: n/a

本页收口中国香港市场历史数据、研究产物和恢复专用归档入口。当前活跃主线是 A 股数据、研究和执行交接；港股真实资产按冷存储和显式恢复流程维护。

## 当前状态

- 数据平台资产：冻结到独立冷存储；港股 provider 生产面已从活跃 `market-data-platform` 主线删除，活跃 `DATA_PLATFORM_ROOT` 保留 `metadata/frozen_markets/hk.json`。
- 研究产物：历史 run、sweep、report 和导出文件进入研究侧冷存储。
- 代码组合：`hk-freeze-20260613` 已在 `research-workspace`、`market-data-platform`、
  `strategy-pipeline`、`quant-execution-engine` 推送，用作后续港股恢复专用工作区的源版本。
- 私有旧代码：已发布到外部私有、暂停维护、恢复专用仓库
  `git@github.com:runchengxie/hk-quant-legacy-archive.git`，不作为本工作区 submodule、
  CI 目标或运行依赖。
- 港股恢复专用工作区：已发布到外部私有仓库
  `git@github.com:runchengxie/hk-research-workspace-archive.git`，仅 pin 三个子模块到
  `hk-freeze-20260613`。
- 公开展示：工作区内公开演示路线和独立港股研究线已于 2026-06-14 退役；港股材料只保留私有、暂停维护、恢复专用归档。

## 权威入口

| 目的 | 文档 |
| --- | --- |
| 查看旧兼容面、公开演示拆分和清理门禁 | [../../hk-public-split-manifest.yml](../../hk-public-split-manifest.yml) |
| 查看私有旧代码归档和删除门禁 | [../../hk-private-archive-manifest.yml](../../hk-private-archive-manifest.yml) |
| 查看 deprecated 入口删除门禁 | [../../deprecations.md](../../deprecations.md) |
| 查看数据迁移优先级和恢复顺序 | [../../data-transition-playbook.md](../../data-transition-playbook.md) |
| 查看文档生命周期和兼容页 | [../../documentation-lifecycle.md](../../documentation-lifecycle.md) |
| 查看 provider legacy 删除审计证据 | [../../evidence/hk-provider-legacy-removal-20260613.json](../../evidence/hk-provider-legacy-removal-20260613.json) |
| 查看 freeze tag 版本矩阵 | [../../version-matrix.md](../../version-matrix.md) |

以下页面保留为兼容入口，权威清单见上表：

- [../../hk-legacy-surface-inventory.md](../../hk-legacy-surface-inventory.md)
- [../../hk-private-archive.md](../../hk-private-archive.md)

## 记录

| 类型 | 文档 |
| --- | --- |
| 数据平台发布说明 | [records/hk-cold-freeze-20260526.md](records/hk-cold-freeze-20260526.md) |
| 数据平台 session handoff | [records/hk-cold-storage-20260601.md](records/hk-cold-storage-20260601.md) |
| 研究产物发布说明 | [records/hk-research-freeze-20260601.md](records/hk-research-freeze-20260601.md) |
| 研究产物 session handoff | [records/hk-research-cold-storage-20260601.md](records/hk-research-cold-storage-20260601.md) |
| 私有旧代码归档证据 | [../../evidence/hk-private-archive-stage-20260613.json](../../evidence/hk-private-archive-stage-20260613.json) |
| 港股 provider 旧入口删除审计 | [../../evidence/hk-provider-legacy-removal-20260613.json](../../evidence/hk-provider-legacy-removal-20260613.json) |
| 港股恢复专用工作区证据 | [../../evidence/hk-research-workspace-archive-20260613.json](../../evidence/hk-research-workspace-archive-20260613.json) |

恢复前先从对应 session handoff 读取冷存储路径、manifest、校验命令和已知限制。

## 公开拆分门禁

`../../hk-public-split-manifest.yml` 是迁出和删除判断入口。任何影响恢复或兼容的入口在删除前，都需要同时具备恢复证据、消费方审计、替代文档、回滚说明和定点测试。公开演示路线已经退役，因此不再要求公开拆分暂存证据。

## 私有 legacy archive 门禁

`../../hk-private-archive-manifest.yml` 管理真实业务代码的私有归档。公开演示路线已退役后，
它是港股历史业务代码的恢复依据：
只从固定的 Git revision 导出 allowlist 源码，保留 SHA-256 和本地暂存证据。2026-06-13
的后续删除已把港股 provider 生产面移出活跃 `market-data-platform` 和 `strategy-pipeline`
入口；恢复时从 `hk-freeze-20260613` 或私有恢复专用归档取回。LongPort、标准
`targets.json` 多市场解析、FX、风控和 `freeze-hk` / `hydrate-hk` 控制面继续留在活跃仓库。
