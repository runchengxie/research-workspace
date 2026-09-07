# 跨仓库边界清理设计

- 日期：2026-08-30
- 状态：提议中
- 范围：`research-workspace` 上层仓库和受影响的所属仓库
- 相关决策：ADR-0006、ADR-0007、策略边界重构路线图、可维护性重构路线图

## 1. 问题说明

工作区已经完成了多项归属迁移，但少数跨仓库边界仍保留重复的生产逻辑或过渡性归属。剩余问题集中在以下位置：

1. `alpha-research` 和 `portfolio-backtester` 都实现了近似的 `freshness_overlay` 分数调整逻辑。
2. 两个仓库都保留了近似的基准比较辅助函数。
3. 仓库本地的可维护性包装器和部分测试仍然相似，但稳定的扫描算法已经抽取到现有的 `research-code-quality` 包。
4. StyleReplica 仍处于混合归属的过渡状态。ADR-0007 定义了目标拆分，现有代码在迁移完成前有意保留部分兼容能力。
5. `strategy-research/src/style_factors/` 包含超出文档化所属边界的可复用运行能力，包括组合回放准备、执行诊断、数据加载、信号和回测辅助函数，以及承担了较多逻辑的 `portfolio_backtester_adapter.py`。
6. 上层仓库当前跟踪 8 个子模块，其中包括 `strategy-research`，但 `ARCHITECTURE.md` 仍描述 7 个子模块和更早的非子模块状态。

主要风险是语义漂移：两个仓库可能分别演进同一条金融规则的不同实现，而各自的测试套件仍然通过。

## 2. 目标

本系列改动将：

- 为每条可复用的金融领域规则确定唯一所属仓库。
- 删除已经确认的跨仓库业务逻辑重复。
- 在移除会造成不必要破坏时保留兼容入口，并确保兼容入口不违反依赖方向。
- 以小步方式完成 ADR-0007 中最有价值的 StyleReplica 拆分。
- 让 `strategy-research` 聚焦研究编排、证据、实验、报告，以及必要的轻量适配器。
- 继续使用 `research-contracts` 和 `research-code-quality`，不另造替代共享层。
- 仅在所属仓库合并改动后，更新上层仓库的架构文档和 gitlink。
- 增加回归覆盖，降低重复代码和归属漂移再次出现的概率。

## 3. 非目标

本系列不会：

- 为了消除少量样板代码而新增 `common-utils` 共享仓库。
- 将研究算法放入 `research-contracts`。该仓库负责轻量产物、schema、哈希和血缘契约，不负责研究逻辑。
- 替换已经负责稳定跨仓库可维护性扫描算法的 `research-code-quality`。
- 机械地将所有研究实验迁移到领域仓库。
- 要求所有受影响的仓库同时合并。
- 在安全门面可用时，于消费者迁移前删除兼容 API。
- 为了消除一个重复文件，引入 `portfolio-backtester -> alpha-research` 运行时依赖。
- 将代码搬迁与交易语义修改绑定。发现已有不一致时，应单独记录和处理。
- 仅因某个可维护性问题规模较大，就顺带重构无关问题。

## 4. 设计原则

### 4.1 领域归属优先于调用便利

可复用逻辑归属于负责其语义的仓库，即使另一个仓库调用起来更方便。

### 4.2 保持依赖方向

归属清理不能让依赖图变差。通用组合基础设施必须能够在不导入 alpha 实现包的情况下使用。当组合流程需要 alpha 生成的分数时，应由上游完成分数变换，再通过公开契约把结果或产物传给组合层。

### 4.3 实验可以组合，可复用能力需要迁移

`strategy-research` 可以保留实验特定的胶水代码和一次性探索代码。某项能力被多个实验复用，或表达稳定的数据、alpha、组合规则后，应迁移到对应的所属仓库，研究代码调用所属仓库 API。

### 4.4 兼容入口只能是门面

迁移期间，旧导入路径只有在能够委托给所属仓库实现且不违反依赖方向时才能保留。兼容模块不能继续保存算法副本。

### 4.5 搬迁前先用一致性测试固定金融语义

删除有活跃消费者的重复实现前，先用代表性数据表、边界情况和相关结果元数据固定当前行为。随后让消费者迁移到所属仓库 API，或接收上游已经转换的产物。只有在一致性得到证明后才能删除重复实现。

### 4.6 PR 保持独立可审查

每个 PR 聚焦一个归属边界或一项配套工作。跨仓库依赖要在 PR 说明中明确记录，避免把多个变化隐藏在一次大改动中。

## 5. 目标归属矩阵

| 能力 | 所属仓库 | 允许的消费者或门面 | 说明 |
| --- | --- | --- | --- |
| 因子、分数、信号语义 | `alpha-research` | `strategy-app`、`strategy-research`、通过公开 API 调用的流水线 | 包括影响 alpha 排名或分数的 freshness 语义 |
| 策略身份和冻结的策略特定规则 | `strategy-app` | 流水线和研究流程 | 包括 StyleReplica A80/B20 身份、主题配额和策略版本契约 |
| 通用目标或持仓构造、换手、缓冲、替换、重叠、权重和回放周期 | `portfolio-backtester` | `strategy-app`、`strategy-research`、`strategy-pipeline` | 策略特定参数作为输入，不在通用层硬编码策略身份 |
| 组合执行模拟和执行诊断 | `portfolio-backtester` | 研究和流水线调用方 | 与券商无关 |
| 实盘经纪、审批、订单状态、对账和恢复 | `quant-execution-engine` | `strategy-pipeline` | 研究仓库不得形成另一套实盘执行运行时 |
| 已发布市场资产和稳定数据访问契约 | `market-data-platform` | 所有研究和策略消费者 | 实验特定的数据转换仍可留在研究层 |
| 策略论点、生命周期、证据、研究决策和实验编排 | `strategy-research` | 上层仓库导航和研究流程 | 不再实现可复用的 alpha、组合或数据能力 |
| 运行编排、运行时目录、外部调用、准入和发布 | `strategy-pipeline` | 运行入口 | 不重复实现所属仓库契约 |
| 产物封装、schema、哈希和血缘契约 | `research-contracts`（位于 `research-workspace`） | 生产者和消费者仓库 | 不包含算法 |
| 稳定的跨仓库可维护性扫描 | `research-code-quality` | 仓库本地治理包装器 | 本地预算和仓库特定字段保留在本地 |

## 6. 改动组 A：freshness overlay 归属

### 当前状态

`alpha-research` 和 `portfolio-backtester` 包含近似的 `freshness_overlay.py` 实现。该函数使用新鲜度和成交量排名信息调整分数，重复实现会直接造成分数语义漂移风险。

`portfolio-backtester` 当前没有将 `alpha-research` 声明为运行时依赖。本次清理不得为了共享实现而增加反向依赖。

### 目标状态

`alpha-research` 负责规范的 freshness 分数变换，`portfolio-backtester` 消费已经完成 alpha 变换的分数。

迁移步骤：

1. 在 `alpha-research` 中用专项测试固定当前行为，覆盖禁用模式、空表、缺少列、lambda 边界、排名、输出列保留和元数据。
2. 在 `alpha-research` 中提供或确认稳定的公开入口。
3. 审计 `portfolio-backtester` 中重复模块的所有调用位置。
4. 如果组合层副本没有被使用，删除它并增加边界回归测试。
5. 如果存在活跃调用，将分数调整移到上游 alpha 或策略调用方，再把调整后的分数传给组合 API。
6. 如果保留组合层兼容实现会导致算法复制或新增反向依赖，则不得保留该实现。

如果证据表明存在真正属于组合层的 freshness 概念，应使用不同名称和契约，不能悄悄复制 alpha 分数变换。

## 7. 改动组 B：当前由 strategy-research 实现的组合能力

### 当前状态

`strategy-research/src/style_factors/portfolio_backtester_adapter.py` 同时包含对 `portfolio-backtester` 的轻量调用，以及目标表标准化、调仓或入场或退出周期构造、延迟成交归因和执行回执汇总等通用组合或执行逻辑。

同一包还包含可复用的回测或执行模块和数据加载器，其长期归属与工作区文档中的模型仍不完全明确。

### 目标状态

通用组合契约和诊断迁移到 `portfolio-backtester`。`strategy-research` 只保留研究特定的转换和实验编排。

迁移步骤：

1. 新增 API 前，先搜索 `portfolio-backtester` 中已有的公开等价能力。
2. 仅为没有公开等价能力的通用部分增加所属仓库 API 和测试。
3. 让 `strategy-research` 迁移到这些 API。
4. 将 `portfolio_backtester_adapter.py` 收缩为 schema 转换和轻量委托。
5. 按归属类别盘点 `style_factors` 模块：仅研究、候选 alpha、候选组合、候选数据访问。
6. 本系列只迁移清晰可复用的能力。一次性实验代码保留原处，并明确记录剩余抽取债务。

适配器可以依赖 `portfolio-backtester` 的公开 API，不能为了省去正式的所属仓库 API 而访问私有下划线模块。

## 8. 改动组 C：完成 StyleReplica ADR-0007

ADR-0007 仍是治理依据，本系列不替换它。

目标拆分：

- `alpha-research`：因子、分数、信号、研究标签和诊断。
- `strategy-app`：StyleReplica 身份和冻结的策略特定规则。
- `portfolio-backtester`：通用的候选到持仓构造和回放。
- `strategy-pipeline`：仅负责编排。
- `market-data-platform`：已发布的数据契约。
- `quant-execution-engine`：实盘执行职责。

实施采用小步迁移：

1. 使用夹具和一致性测试冻结现有公开结果。
2. 将策略身份参数迁移或委托到现有的 `strategy-app/style_replica/policy.py` 契约。
3. 将通用缓冲、替换、重叠、加权和校验行为迁移或委托到 `portfolio-backtester` API。
4. 在消费者迁移期间保留 `alpha_research.style_replica` 兼容入口作为轻量门面，但前提是不会造成禁止的依赖环。
5. 如果轻量跨仓库门面会造成依赖环，先迁移调用方，再弃用或删除旧的复合入口，不保留第二套实现。
6. 增加边界测试，禁止在 alpha 兼容层新增策略规则或最终持仓构造逻辑。

迁移只允许减少混合职责，兼容包不能新增混合职责。

## 9. 改动组 D：低风险的非领域重复

### 基准比较辅助函数

`alpha-research` 和 `portfolio-backtester` 中的重复基准比较辅助函数，风险低于金融规则重复，将在语义归属工作稳定后处理。

审计先确认这些函数属于运行时 API、仓库本地工具，还是历史遗留副本。优先采用最小改动，形成一份受维护的行为，不新增仓库，也不建立不合适的依赖边。

### 可维护性工具

稳定扫描算法已经集中在 `research-code-quality`。当前各仓库的 `maintainability_metrics.py` 有意保留本地递进预算、本地指标字段和本地 CLI 格式。

因此，本系列不会机械合并这些包装器，只会：

- 确认剩余跨仓库相同逻辑已经委托给 `research-code-quality`。
- 只有在不影响独立仓库检查时，才删除或减少真正冗余的包装器或测试代码。
- 将仓库特定的预算和治理值留在本地。

如果审计确认当前拆分合适，这一项可以不产生代码 PR。

## 10. 上层仓库改动

所属仓库 PR 合并后：

1. 在专门的 `research-workspace` 集成 PR 中更新受影响的子模块 gitlink。
2. 修正 `ARCHITECTURE.md`，描述当前 8 个子模块和 `strategy-research` 的角色。
3. 确保 `.gitmodules`、架构文档、归属文档、CODEOWNERS、扫描器排除项和 `research-contracts` 依赖文档保持一致。
4. 针对本次修复的重复或边界漂移类型，增加轻量跨仓库回归检查。
5. 更新相关路线图和 ADR 状态说明，不改写历史决策。

## 11. 计划中的 PR 顺序

预计顺序如下：

1. `research-workspace` 设计 PR：仅包含本设计文档。
2. `alpha-research` PR A1：规范 freshness 所属 API 和行为测试。
3. `portfolio-backtester` PR A2：审计并删除重复 freshness 实现，或移除活跃调用并要求上游传入已调整分数。不得增加 `portfolio-backtester -> alpha-research` 依赖。
4. `portfolio-backtester` PR B1：提供 `strategy-research` 需要的通用持仓周期或执行诊断 API。
5. `strategy-research` PR B2：收缩组合适配器，删除已迁移能力，并记录剩余抽取债务。
6. `strategy-app`、`alpha-research`、`portfolio-backtester` 的 StyleReplica PR C1 至 Cn：按 ADR-0007 分小步迁移，依赖方向允许时使用兼容门面和一致性测试。
7. 可选工具 PR D1 至 Dn：在领域语义稳定后再处理基准比较和剩余治理重复，且只有审计确认仍存在真实重复时才创建。
8. `research-workspace` 集成 PR：更新 gitlink、`ARCHITECTURE.md`、治理检查和路线图状态。

编号仅用于表达顺序。若边界过大而难以安全审查，可以拆成更多小 PR。

## 12. 兼容和依赖策略

依赖仓库的默认分支不能依赖另一个仓库尚未合并的分支才能正常使用。

因此：

- 需要新增公开 API 时，先合并提供方 PR，再合并消费者 PR。
- 只有在不复制逻辑且不产生禁止依赖环时，兼容门面才能保留旧导入路径。
- 如果无法安全委托，先迁移消费者，再在后续 PR 中删除或弃用旧的复合 API。
- 上层仓库只有在所属仓库默认分支已经包含目标提交后，才能更新 gitlink。
- 兼容入口的删除要等仓库搜索确认没有剩余消费者。

## 13. 测试策略

每次归属迁移使用三层测试：

1. 所属仓库单元测试：覆盖规范行为和边界情况。
2. 消费者一致性测试：证明委托或上游转换保留现有结果。
3. 边界测试：防止已迁出的实现或禁止的依赖方向重新出现。

金融逻辑的一致性测试要同时比较主要输出和有意义的元数据或诊断结果。测试使用固定夹具，不依赖会变化的外部数据。

上层仓库集成 PR 还要针对最终 gitlink 集合运行现有的 workspace doctor、治理检查和可维护性门禁。

## 14. 回滚策略

本系列采用提供方优先的 API 和安全的兼容门面，因此每次消费者迁移都可以独立回滚。

如果在删除重复实现前发现一致性不匹配：

- 调查期间，在迁移分支临时保留旧实现。
- 将不匹配记录为语义缺陷或有意差异。
- 在删除重复实现的清理改动合并前，由所属仓库解决该问题。

合并后的目标状态不能为了满足兼容而长期保留两套规范的金融实现。

## 15. 完成条件

满足以下条件后，本次清理完成：

- 当前重复的 freshness 分数变换只保留一份规范实现。
- freshness 清理没有让 `portfolio-backtester` 反向依赖 `alpha-research`。
- 如果组合所属仓库已有相应 API，`strategy-research` 不再负责通用的组合周期构造或执行归因能力。
- ADR-0007 中的混合职责明显减少，保留的兼容表面都是轻量委托。
- 受影响的消费者不再依赖其他仓库的私有或内部模块路径。
- `ARCHITECTURE.md` 与 8 个子模块的实际状态一致。
- 最终上层仓库 gitlink 指向已合并的所属仓库提交。
- 专项边界和重复测试能够阻止已修复的漂移模式再次出现。
- `research-contracts` 和 `research-code-quality` 的边界保持不变。
- 所有有意延后的抽取债务都有明确记录、负责人和触发删除或迁移的条件。
