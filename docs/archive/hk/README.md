# 中国香港市场归档

本页收口中国香港市场历史数据、研究产物和公开 demo 的归档入口。当前活跃主线是 A 股数据、研究和执行交接；港股真实资产按冷存储和显式恢复流程维护。

## 当前状态

- 数据平台资产：冻结到独立冷存储，活跃 `DATA_PLATFORM_ROOT` 保留 `metadata/frozen_markets/hk.json`。
- 研究产物：历史 run、sweep、report 和导出文件进入研究侧冷存储。
- 私有 legacy 代码：使用外部 private、paused-maintenance、restore-only 候选仓库治理，不作为本工作区 submodule、CI 目标或运行依赖。
- 公开展示：仅通过外部 paused-maintenance 的 synthetic demo 仓库，不作为本工作区 submodule、CI 目标或 release matrix 成员。

## 稳定入口

| 目的 | 文档 |
| --- | --- |
| 查看保留的 legacy surface 和 sunset 边界 | [../../hk-legacy-surface-inventory.md](../../hk-legacy-surface-inventory.md) |
| 查看 public split manifest 和 cleanup gate | [../../hk-public-split-manifest.yml](../../hk-public-split-manifest.yml) |
| 查看 private legacy archive staging 和 removal gate | [../../hk-private-archive.md](../../hk-private-archive.md) |
| 查看 private archive manifest | [../../hk-private-archive-manifest.yml](../../hk-private-archive-manifest.yml) |
| 查看 deprecated 入口 removal gate | [../../deprecations.md](../../deprecations.md) |
| 导出外部 clean-room 港股公开 demo | [../../hk-public-demo-export.md](../../hk-public-demo-export.md) |
| 查看数据迁移优先级和恢复顺序 | [../../data-transition-playbook.md](../../data-transition-playbook.md) |

## 冷存储记录

| 类型 | 文档 |
| --- | --- |
| 数据平台 release note | [release-notes/hk-cold-freeze-20260526.md](release-notes/hk-cold-freeze-20260526.md) |
| 数据平台 session handoff | [session-handoffs/hk-cold-storage-20260601.md](session-handoffs/hk-cold-storage-20260601.md) |
| 研究产物 release note | [release-notes/hk-research-freeze-20260601.md](release-notes/hk-research-freeze-20260601.md) |
| 研究产物 session handoff | [session-handoffs/hk-research-cold-storage-20260601.md](session-handoffs/hk-research-cold-storage-20260601.md) |

恢复前先从对应 session handoff 读取冷存储路径、manifest、校验命令和已知限制。

## Public split gate

`../../hk-public-split-manifest.yml` 是迁出和删除判断入口。任何 restore-sensitive 或
compatibility surface 在删除前都需要同时具备 restore evidence、consumer audit、replacement
docs、rollback notes、focused tests，以及需要公开 demo 承接时的 public split evidence。

公开 demo staging 只承接 synthetic fixture 和 public-safe demo 逻辑。真实行情、provider cache、
券商 adapter、交易审计日志、本地路径和私有研究输出不进入公开 demo。

## Private legacy archive gate

`../../hk-private-archive-manifest.yml` 管理真实业务代码的私有归档候选。它和 public demo 分离：
只从 pin 的 Git revision 导出 allowlist 源码，保留 SHA-256 和本地 staging 证据，不自动创建远端、
不修改 submodule、不删除源文件。LongPort、标准 `targets.json` 多市场解析、FX、风控和
`freeze-hk` / `hydrate-hk` 控制面继续留在活跃仓库。
