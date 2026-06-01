## Why

A 股已经成为默认研究入口，但当前分支仍有一个数据平台维护性门禁回归，执行引擎的
Pyright 迁移也尚未达到 hard gate 条件。与此同时，港股长期暂停维护需要继续收缩活跃面，
但不能破坏冷存储恢复、历史复现或多市场执行能力。

## What Changes

- 修复 `market-data-platform` 的 maintainability baseline regression，不通过抬高 baseline
  接受新增债务。优先拆分 A 股 refresh / fundamentals 编排中的长函数和长参数列表，并把
  长测试主体抽成 fixture/helper。
- 为 `quant-execution-engine` 清理当前可复现的 Pyright error；在 error 清零并完成 focused
  回归后，将工作区 delegated `type` profile 从 mypy 切换到 Pyright，同时在过渡期保留
  mypy advisory。
- 保持 A 股 readiness 的分层口径：当前只确认 `baseline_reproducible`；生产 PIT 资产、
  长窗口策略证据和真实券商报单分别继续作为独立门禁。
- 对港股代码执行按 surface 分类的 sunset：保留 restore-critical 平台能力、显式 legacy
  preset 和多市场执行共享代码；只有完成消费者审计、归档清单和回滚证据后，才迁出历史
  wrapper、实验配置和 research-only provenance。
- 保留独立港股公开 demo 的 clean-room export 模式：只发布 synthetic fixture、离线
  workflow、最小 CI 和免责声明，不复制 Git 历史、真实数据、凭证、券商 adapter 或收益宣传。
- 不在本 change 中新增真实 A 股券商 adapter，也不声称现有 CN `targets.json` dry-run 已经
  满足实盘条件。

## Capabilities

### New Capabilities

- `data-platform-maintainability-ratchet`: 数据平台维护性 baseline 的恢复规则、拆分目标和
  验收命令。
- `qexec-pyright-migration`: 执行引擎从 mypy hard gate 迁移到 Pyright hard gate 的前置
  清债、切换条件和过渡期回滚规则。
- `a-share-primary-readiness`: A 股默认主线后续生产化缺口的分层状态、证据门禁和不得夸大
  的执行边界。
- `hk-legacy-sunset`: 港股 legacy surface 的保留、迁出、公开 demo 和回滚要求。

### Modified Capabilities

None. The current OpenSpec project has no base capability specs checked in.

## Impact

- `market-data-platform`: A 股 refresh / fundamentals helper 结构、相关测试和
  `scripts/dev/maintainability_metrics.py --check-baseline` 结果。
- `quant-execution-engine`: optional broker SDK 归一化边界、Pyright 配置与测试文档。
- Superproject: `scripts/submodule_checks.json`、质量治理文档、release checklist、doctor /
  delegated profile tests，以及 A 股 readiness 和港股 sunset 文档。
- `cross-sectional-trees`: 仅在 surface 审计确认可迁出时调整港股 legacy 导航、配置和最小
  smoke；A 股研究继续只读消费平台发布资产。
- Public demo: 继续作为工作区外部、暂停维护的 clean-room 作品集仓库，不加入 required
  submodule。
