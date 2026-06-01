## Context

上一轮治理已经完成 A 股默认入口切换、TuShare 基本面 raw-to-PIT 代码骨架、A 股 readiness
分层、港股冷存储流程和港股公开 demo exporter。当前剩余问题不是重新设计迁移路线，而是把
新增维护债压回 baseline，并继续收敛下一阶段的 active surface。

`market-data-platform` 当前本地可复现：

```text
functions_over_100: 71 > 69
functions_with_10_plus_args: 49 > 48
```

新增 A 股代码中，`build_a_share_current_refresh_plan`、`download_raw_fundamentals` 和
`build_a_share_industry_changes` 是优先拆分目标；`tests/test_backup_data.py` 也有可抽取的
长测试 fixture。CI 失败应通过结构性拆分修复，而不是写入更高 baseline。

`quant-execution-engine` 当前 mypy 通过，Pyright advisory 为 `8 errors, 11 warnings`。
error 集中在 optional IBKR / LongPort SDK 动态对象归一化边界；warning 来自延迟导出列表和
PyYAML source visibility。Pyright 可以成为统一 hard gate，但必须先修复 error 并记录
warning policy。

顶层 evidence 已明确：`baseline_reproducible` 通过，`complete_pit_research_data`、
`production_strategy_evidence` 和 `broker_trading_enabled` 仍未通过。本机当前还缺失港股
冷存储外部目录，因此不能把已有 restore drill 证据等同于本机立即可 hydrate。

## Goals / Non-Goals

**Goals:**

- 恢复数据平台 maintainability ratchet，并保留现有 A 股 refresh / fundamentals 行为。
- 清理执行引擎 Pyright error，按阶段把工作区 hard type gate 统一到 Pyright。
- 把 A 股主线剩余缺口继续表达为可检查的 readiness 层级。
- 继续缩小港股 active lane，同时保留恢复能力、历史 provenance 和多市场共享代码。
- 保持港股公开 demo 是工作区外部、暂停维护、无真实数据的 clean-room export。

**Non-Goals:**

- 本 change 不执行大规模 TuShare 下载，不发布生产 PIT 资产，不生成长期策略结论。
- 本 change 不新增真实 A 股券商 adapter，不申请账户权限，不执行真实报单。
- 本 change 不批量删除 `market-data-platform` 的港股 restore-critical 实现。
- 本 change 不把港股公开 demo 加为 submodule，也不自动创建或 push GitHub 远端。

## Decisions

### 1. 通过拆分恢复 baseline，不提高 baseline

将 refresh plan 的路径计算、stage 构建和 payload 组装拆成窄 helper。将 fundamentals
下载器的运行参数收敛为 options/context 对象，并把单个 query unit 的重试、状态落盘和
manifest 汇总拆开。将行业历史列映射收敛为配置对象。测试中的大型输入构造抽成 fixture /
helper。

备选方案是执行 `--write-baseline` 接受回归。该方案会让 ratchet 失去约束意义，因此不采纳。

### 2. Pyright 迁移分两阶段进行

第一阶段只修复 Pyright error：在 optional SDK 边界增加窄化 helper、明确的 iterable /
float / enum / datetime 归一化和必要的 Protocol。warning 必须逐项分类；只有确实属于延迟
导出或 optional dependency source visibility 的 warning 才保留为记录项。

第二阶段在 Pyright 无 error、focused tests 和默认测试通过后，将顶层
`quant-execution-engine.profiles.type` 切为 Pyright，并增加 `mypy_advisory`。过渡期至少
保留一个发布周期，便于比较发现质量。

备选方案是立即替换 mypy。当前 Pyright 命令仍返回失败，因此会直接破坏 hard gate，不采纳。

### 3. A 股 readiness 继续按四层汇报

保持：

1. `baseline_reproducible`
2. `complete_pit_research_data`
3. `production_strategy_evidence`
4. `broker_trading_enabled`

每层只由对应 evidence 推进。`metadata/current_assets/a_share_current.json` 继续是 canonical
入口；历史 `cn_current.json` 只能作为兼容 alias。CN `targets.json` 文件契约和
`local-dry-run` 只能满足基线交接，不允许推导真实券商能力。

备选方案是将默认入口切换视为迁移完成。该方案混淆可复现 baseline、策略证据和实盘能力，
不采纳。

### 4. 港股 sunset 按 surface 分类，不按目录批量删除

继续使用 `shared_active`、`frozen_compatibility`、`archived_provenance` 和
`retire_after_audit` 分类。多市场执行能力、freeze / hydrate、显式 `hk` preset 和必要 smoke
保留；旧 wrapper、实验配置和历史说明只有在消费者审计、source tag、archive manifest 和
恢复证据齐备后才迁出 active lane。

港股公开 demo 继续从 allowlist 模板单向导出。它用于作品集展示，不成为当前主项目的同步
目标。

备选方案是把港股实现立即拆成独立公开库并从主项目删除。该方案容易泄露授权数据或策略
细节，也会损坏恢复与回滚路径，因此不采纳。

## Risks / Trade-offs

- [Risk] options/context 重构可能改变 CLI 输出或 manifest 字段。  
  → Mitigation: 保留现有 schema version，补 plan、manifest、restart 和失败报告 focused tests。
- [Risk] 为了让 Pyright 通过而滥用 `Any`、`cast` 或全局 ignore。  
  → Mitigation: ignore 只允许位于明确 optional SDK 边界，并要求 focused test 覆盖归一化行为。
- [Risk] 港股删除范围过大，导致无法 hydrate 或复现历史结果。  
  → Mitigation: 删除前必须核对 inventory、外部冷存储可用性、restore drill 和消费者审计。
- [Risk] 港股 demo 被误认为生产策略或收益展示。  
  → Mitigation: 仅使用 synthetic fixture，保留 paused-maintenance、no-live-trading 和
  not-investment-advice 声明。
- [Risk] A 股默认入口被误写成生产可交易状态。  
  → Mitigation: readiness 报告和 release checklist 必须分别记录 PIT、策略证据和券商门禁。

## Migration Plan

1. 在数据平台完成 helper/options 重构，运行 maintainability check 和 focused tests；仅在原
   baseline 通过后合并。
2. 在执行引擎修复 8 个 Pyright error，运行 Ruff、mypy、Pyright、默认 pytest 和 CN contract
   focused tests。
3. 更新顶层 delegated profile：`type` 改为 Pyright，新增 `mypy_advisory`，同步文档和 manifest
   tests。
4. 复核 A 股 readiness evidence：保持 PIT、长窗口和真实券商状态为 pending，除非有新的真实
   产物和操作证据。
5. 复核港股 surface inventory；只迁出已满足审计条件的 provenance / wrapper。重新运行 demo
   clean-room export scan 和 offline smoke。
6. 若 Pyright hard gate 在过渡期产生不可控噪声，回滚 delegated `type` profile 到 mypy，
   保留已完成的边界类型修复，再重新评估。

## Open Questions

- mypy advisory 过渡期采用一个发布周期还是固定日期窗口，需要在实施时确定。
- 本机缺失的港股冷存储目录何时恢复，需要在进一步迁出 restore-sensitive surface 前确认。
- 港股公开 demo 的远端首次发布仍需维护者人工复核 staged tree 后显式执行。
