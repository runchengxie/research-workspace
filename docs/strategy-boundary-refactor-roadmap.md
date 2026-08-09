# 策略边界重构路线图

> status: active
> owner: workspace
> last_verified: 2026-08-09
> source_of_truth: yes
> superseded_by: n/a

本页记录 [ADR-0006](adr/0006-strategy-knowledge-and-runtime-boundaries.md) 尚未完成的实施工作。它只描述后续拆分顺序和验收标准，不把规划中的迁移写成已经完成的事实。

## 当前基线

已经完成：

- 原 `research-apps` 仓库和 Python 包已经分别改名为 `strategy-app` 与 `strategy_app`。
- `strategy-research` 已登记七个策略或策略族，并成为策略身份、生命周期和证据导航的权威位置。
- 根工作区已经采用新的子模块名称，并增加三层边界和回归测试。

尚未完成：

- `strategy-pipeline` 的依赖、导入、锁文件和活动文档仍指向旧的 `research-apps` 0.1.0 与 `research_apps` 命名空间。
- `strategy-pipeline` 仍有约 104,986 行 Python 物理行，其中 `src` 约 58,316 行、测试约 36,097 行、脚本约 10,572 行。改名和目录登记没有减少这部分代码。
- 兼容层登记表确认仍有 39 个被 pipeline 内部调用或所有权测试引用的策略 owner facade，尚未完成调用方改向。
- DailyWatch20、热点板块、D11-H5、红利与成长 ETF 动量、次日开盘到最高价仍有策略计算或研究编排留在 pipeline。
- `strategy-research` 与 pipeline 之间仍存在重复研究脚本和研究说明。次日开盘到最高价当前至少有九个同名脚本分布在两处。
- pipeline 的跨仓库 contract 说明、综合指标文档和全量输出参考仍需按 owner 拆分。
- 顶层 `src/style_factors` 是否继续作为工作区薄包，还是进入 alpha 或 portfolio owner，尚未形成最终决策。

以上行数是 2026-08-09 的盘点基线，不是目标配额。后续以删除错误归属、重复实现和兼容层为目标，不能通过移动测试或压缩格式制造体量下降。

## 目标状态

```text
strategy-research
  人类可读策略规格、生命周期和证据入口
          |
          v
strategy-app
  策略特有纯计算和冻结合同
          |
          v
strategy-pipeline
  外部调用、运行目录、操作控制、发布门禁和 targets.json
```

数据资产归 `market-data-platform`，特征、标签、模型和通用统计归 `alpha-research`，组合构造、成本、换手、容量和回放归 `portfolio-backtester`，交易执行归 `quant-execution-engine`。`strategy-app` 中出现两个策略可复用的能力时，应直接迁入对应 owner 仓。

## 实施阶段

| 阶段 | 状态 | 主要工作 | 完成标准 |
| --- | --- | --- | --- |
| R0 仓库改名 | 已完成 | `research-apps` 改为 `strategy-app`，移除旧 Python 包兼容层 | 新 wheel 只包含 `strategy_app`，历史回执 schema 保持不变 |
| R1 策略目录 | 已完成 | 建立七个策略族的权威目录、生命周期字段和 ADR-0006 | 人可从 `strategy-research` 找到策略、代码、证据和迁移债务 |
| R2 pipeline 改名切换 | 已完成 | 更新依赖、Git pin、导入、类型配置、wheel smoke、活动文档和测试名称 | clean clone 只安装 `strategy-app` 0.2.x，活动代码不再导入 `research_apps` |
| R3 调用方改向 | 进行中 | 将 pipeline 内调用逐族改为 owner API，并在同一批次删除对应 facade | 非空冻 facade 31 个中已删 30 个，剩 16 个（15 个字节钉死冻结 + 1 个持有 owner 无等价真实逻辑的非重导出模块 `daily_watch20_fundamental_shadow`），不新增替代兼容层 |
| R4 通用能力归位 | 待开始 | 按数据、alpha、组合、执行职责迁移通用代码，策略特有组合进入 `strategy-app` | pipeline 不再维护模型、通用统计、组合会计、成本或执行回放 |
| R5 重复内容清理 | 待开始 | 删除重复研究脚本和当前说明，保留权威说明、必要的不可变历史证据和跳转 | 每个活动脚本或说明只有一个维护位置，历史哈希与回执仍可验证 |
| R6 控制面收口 | 待开始 | 收紧 import/source 边界、刷新体量基线、gitlink、版本清单和发布证据 | pipeline 只剩控制面职责，全工作区严格门禁通过 |

## R2：先完成 pipeline 改名切换

这是下一次恢复工作时的第一个 PR，因为后续调用方迁移都依赖新包名。

1. 将 `strategy-pipeline/pyproject.toml` 和 `uv.lock` 的依赖切换到 `strategy-app` 已合并提交。
2. 将活动源码和测试导入从 `research_apps` 改为 `strategy_app`。
3. 更新 wheel smoke、namespace boundary、README、AGENTS 和当前维护文档。
4. 保留历史 ADR、版本快照、冻结回执中的旧仓库名，以及 `research_apps.hotsector.deepseek_v4_paired_replay.v1` schema。
5. 不发布 `research_apps` 兼容包，也不在 pipeline 内嵌 fallback。

验收时对活动路径执行旧名称扫描。允许命中历史证据，禁止命中运行时代码、当前依赖和当前操作文档。

## R3 与 R4：按垂直切片迁移

每个切片都按同一依赖顺序推进：

```text
owner 仓补齐公开 API
        -> strategy-app 改用 owner API
        -> strategy-pipeline 调用方改向
        -> 同批删除旧实现和 facade
        -> 根工作区更新 gitlink 与版本证据
```

建议切片顺序如下：

| 顺序 | 切片 | 目标归属 | 主要遗留 |
| --- | --- | --- | --- |
| 1 | 已有 owner facade | `alpha-research`、`market-data-platform`、`portfolio-backtester`、`strategy-app` | 先处理无冻结哈希约束的调用方，建立删除范式 |
| 2 | DailyWatch20 | `strategy-app` 加现有 data、alpha、portfolio API | 候选池、F-lite、slow-volume、基本面 shadow 的内部调用和 facade |
| 3 | 热点板块 | `strategy-app` 加 `portfolio-backtester`，外部候选继续文件耦合 | challenger、Numeric v2、低换手、AI shadow、DeepSeek 稳定性模块 |
| 4 | 次日开盘到最高价 | 模型进 `alpha-research`，回放与成本进 `portfolio-backtester`，策略组合进 `strategy-app` | pipeline 研究子系统和两处重复脚本 |
| 5 | D11-H5 | 模型与信号进 `alpha-research`，目标构造与袖套回放进 `portfolio-backtester` | pipeline 中的模型、目标计算和 shadow runner 混合 |
| 6 | 红利与成长 ETF 动量 | 通用回测进 `portfolio-backtester`，策略配置与报告组合进 `strategy-app` | pipeline 的数据获取、审计、配置和报告模块 |
| 7 | StyleReplica | 形成顶层 `style_factors` 的保留或迁移 ADR | 当前只有待决 owner，没有立即搬迁授权 |

迁移一个切片时同时迁移测试。pipeline 只保留 runner、provider adapter、操作员门禁、运行目录、原子发布与 `targets.json` 生成测试。

## R5：脚本、文档和 contract 去重

- `strategy-research` 保存策略说明、研究结论、实验入口和证据导航，不成为生产进程依赖。
- `strategy-app` 保存策略特有的可执行协议和冻结实验合同。
- owner 仓保存通用算法及其 API 文档。
- pipeline 只保存 provider 调用、运行和发布操作说明。
- 跨仓库稳定字段由生产方维护，顶层 `research_contracts` 与 `docs/contracts.md` 维护发现入口和组合校验。
- 已被回执或 provenance 哈希绑定的内容不改写。需要升级时发布新的版本化 manifest，旧版本进入历史证据。

优先拆分 pipeline 的 `docs/metrics.md`、`docs/reference/outputs/full-reference.md` 和 `docs/concepts/benchmark-protocol.md`。删除重复文件前必须完成引用扫描、替代链接、聚焦测试和回滚说明。

## R6：最终收口标准

以下条件全部满足后，ADR-0006 的实施才算完成：

- `strategy-pipeline` 的活动依赖和源码中不存在旧包名。
- 策略 owner facade 组的活动记录和文件都已移除。
- catalog 中没有把 `strategy-pipeline` 列为策略计算 owner，只作为 `control_plane_owner`。
- pipeline 没有通用数据、alpha、统计、组合、成本和执行实现。
- 重复研究脚本与当前说明已经清理，冻结历史证据仍可按原哈希验证。
- pipeline 的 Python 行数、巨型文件、长函数和复杂度预算随真实删除同步下调。
- 六个子模块和根工作区的 lint、类型、单测、wheel smoke、严格契约冒烟与 workspace doctor 全部通过。
- 每个 owner PR、pipeline PR 和根 gitlink PR 都已经合并，临时远端分支、本地分支和 worktree 已清理。

## 约束与非目标

- 不以一次大搬家完成全部迁移，每轮只处理一个可回滚的垂直切片。
- 不通过新的 re-export、别名包或 `PYTHONPATH` fallback 延长兼容期。
- 不为统一当前名称而改写历史 ADR、冻结证据、回执 schema 或旧版本矩阵。
- 不把外部策略仓库强行变成子模块。外部实现继续通过版本化文件接入，并在策略目录登记身份。
- 不以达到某个任意行数为完成标准。控制面职责纯度、单一所有权和重复实现清零优先于数字。

## 下次继续的起点

下一次从 R2 开始：在 `strategy-pipeline` 的新 worktree 中只完成 `strategy-app` 依赖和命名空间切换，合并并清理后再开始第一个 owner 垂直切片。每次恢复前先重新扫描活动旧名称、facade 消费者和远端 `main`，不要沿用本页的静态计数代替代码事实。
