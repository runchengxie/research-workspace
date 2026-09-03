# 研究生命周期与工作区瘦身治理

> status: active
> owner: workspace、strategy-research
> last_verified: 2026-09-02
> source_of_truth: yes
> superseded_by: n/a

本页定义 `research-workspace` 随研究数量增长时的长期整理规则。重点是让活跃研究、通用基础设施和历史知识保持清楚边界。

本页补充现有文档生命周期、维护债治理、研究判断治理和 ADR-0006，不替代这些入口。

## 1. 三类研究资产

### Living Infrastructure

被多个研究问题复用、具有稳定接口的能力：

- PIT 数据视图和数据发布：`market-data-platform`
- 特征、标签、模型、CV、ranking、统计评价：`alpha-research`
- 组合、成本、容量、暴露和执行回放：`portfolio-backtester`
- 策略特有且已经稳定的纯计算：`strategy-app`
- 编排、发布和运行控制：`strategy-pipeline`

这些资产应持续维护、测试和版本化。

### Active Research

正在回答明确问题的研究资产，包括：

- thesis / hypothesis
- experiment spec
- 研究配置
- 薄 runner 或研究 glue
- evidence navigation
- decision / claim / counterexample

权威位置主要是 `strategy-research/research/`。

### Historical Knowledge

已经完成、被证伪、被替代或暂时停止的研究。它们的价值是防止未来重复踩坑和错误重做，不要求继续占据活跃入口。

应保留：

- 研究问题和假设。
- 关键配置与数据口径。
- 数据版本、代码版本和观察时间。
- 核心结果摘要。
- 失败或停止原因。
- 证据和决策引用。
- 必要的最小复现入口。

大型模型、缓存、临时表和可重新生成的运行产物继续放在仓库外或 ignored artifact 目录，不因归档而永久提交到 Git。

## 2. 研究策略保持薄

策略研究目录应该主要描述：

```text
question
hypothesis
target
feature selection
model selection
evaluation spec
portfolio spec
evidence
decision
```

它不应该长期拥有第二套：

```text
PIT data loader
generic feature engine
generic label builder
generic CV / purge / embargo
generic model wrapper
generic ranking framework
generic portfolio accounting
generic metrics
```

这些能力一旦稳定或复用，应回到职责仓。

## 3. Capability Extraction Rule

满足以下任一条件时，应评估把实验内能力抽到 owner 仓：

1. 两条及以上独立研究线需要同一实现。
2. 能力已经形成稳定输入输出契约，并且不再依赖某个策略的业务假设。
3. 实验代码开始复制现有 owner 仓的职责。
4. 为了复现实验，其他研究不得不通过路径导入该实验内部代码。
5. 同类 bug fix 需要在多个实验目录重复修改。

### 抽取后的处理

抽取完成后：

- active experiment 只保留调用 owner API 的薄层。
- 重复实现删除，不保留长期双轨。
- 如历史复现依赖旧实现，使用 commit SHA、归档证据或冻结 artifact 说明，避免旧实现继续活跃维护。
- owner 仓必须拥有相应测试和公开契约。

## 4. 研究生命周期

策略正式生命周期继续由 `strategy-research/catalog.json` 管理。本页不增加新的策略 lifecycle value。

研究实验本身在治理上可以经历：

```text
idea
  ↓
active exploration
  ↓
validated / rejected / paused
  ↓
strategy lifecycle or archive
```

其中 `paused` 是研究管理状态，不写入策略 catalog 的 lifecycle 字段。

### Validated

研究问题得到足够证据，可以：

- 继续进入策略生命周期评审。
- 抽取通用能力。
- 形成后续更窄的新研究问题。

### Rejected

关键假设被证伪。保留负结果和证据，停止在同一验证窗口继续增加自由度。

### Paused

当前缺数据、依赖或研究优先级不足。必须记录恢复条件，避免 `以后再看` 无限占据 active 导航。

## 5. Research GC

默认每季度进行一次，也可以在一个大型研究族完成阶段性决策后触发。

Research GC 是人工或 agent 辅助评审，不是按文件年龄自动删除的 cron job。金融研究已经够容易误删信号了，没必要让定时任务也加入投资委员会。

### 每次 GC 至少检查

- 长期无活动且没有明确恢复条件的 experiment。
- 已 rejected 但仍出现在 active 导航中的研究。
- 已 superseded 的 README、配置和 runner。
- 两处及以上重复实现的 feature、label、CV、ranking、model wrapper、metric 或 portfolio logic。
- 已抽取到 owner 仓后仍保留的实验内实现。
- 无法追溯 PIT、数据版本、代码版本或证据来源的研究资产。
- 已经没有消费者的 compatibility facade 或 wrapper。
- 大型文档是否应该拆分、生成或归档。

### 每个项目只能得到以下处置之一

| 处置 | 含义 |
| --- | --- |
| `retain` | 仍是活跃且边界正确的研究或基础设施 |
| `extract` | 通用能力迁移到 owner 仓，实验层变薄 |
| `archive` | 保留历史知识，退出活跃入口 |
| `supersede` | 保留兼容导航，明确新的权威入口 |
| `delete` | 没有独立历史价值且可由其他权威资产完全替代 |

GC 记录应说明理由和相关 PR / evidence，并说明具体清理内容。

## 6. Archive 与 Delete 的区别

### 应 Archive

- 研究得到明确负结果。
- 历史结果未来可能帮助解释策略或市场 regime。
- 有独特数据口径、实验设计或失败经验。
- 决策、论文式研究或重要策略演进需要追溯。

### 可以 Delete

- 自动生成且可可靠重建的文件。
- 已抽取后完全重复的实现。
- 没有消费者、没有历史证据价值的临时 wrapper。
- 内容已被权威文档完整吸收，且旧路径不需要兼容。

删除前遵守现有 documentation lifecycle、deprecation 和 restore-sensitive 规则。

## 7. Evidence Retention

归档研究至少保留一个可以回答以下问题的入口：

```text
当时问了什么？
为什么值得问？
用了什么数据和版本？
什么是 OOS？
核心结果是什么？
什么结果推翻或支持了假设？
为什么停止、继续或升级？
以后怎样避免重复做同一个失败实验？
```

证据引用继续使用现有 `research_spec`、evidence bundle、claim、counterexample 和 research case 体系，不再建立第二套研究数据库。

## 8. 文档治理

- 活跃导航只保留当前研究和当前权威方法。
- 历史阶段记录进入 archive。
- 超过 300 行且需要持续人工维护的文档，优先拆成稳定主题或生成索引。
- 一个事实只保留一个 source of truth，其他页面链接过去。
- 研究 agenda 可以较长，因为它描述问题地图。具体实验结果应拆到独立 experiment / evidence 页面，避免 agenda 变成运行日志。

## 9. 什么时候不应该新建仓库

以下理由单独出现时都不足以拆仓：

- 文件变多。
- 文档变长。
- 某个策略有很多实验。
- 想让目录看起来更干净。
- 某个 agent 觉得 submodule 很有建筑美感。

拆仓会增加版本锁、gitlink、组合测试、发布和依赖管理成本。

## 10. 新仓库触发条件

只有同时满足以下条件时才进入 ADR 评审：

1. 有稳定、独立且长期存在的领域 owner。
2. 有独立依赖或发布节奏。
3. 与现有 owner 的 public contract 已稳定。
4. 拆分能删除错误依赖、重复实现或发布耦合，而不只是移动文件。
5. 有明确维护者和质量门禁。
6. workspace 增加的组合验证成本有可说明的收益。

仓库布局不表达策略生命周期。一个 exploration 策略可以调用成熟 owner API，一个 production 策略也不因此获得独立仓库资格。

## 11. 与 ADR-0006 的关系

ADR-0006 已经确定：

- `strategy-research` 管策略知识和生命周期。
- `strategy-app` 管策略特有纯计算。
- 数据、alpha、统计和组合能力归 owner 仓。
- 两个策略可复用的能力不得留在 `strategy-app`。

本页把这套边界扩展到研究增长后的日常维护：研究可以不断增加，但通用实现不能随着每个 experiment 一起复制增长。

## 12. 建议的季度检查顺序

```text
1. inventory active experiments
2. mark validated / rejected / paused
3. identify duplicated capabilities
4. extract reusable code to owner repos
5. archive historical research
6. remove superseded duplication
7. refresh navigation and evidence links
8. record GC decision summary
```

衡量 GC 是否成功的标准是：

- active surface 是否更容易理解。
- owner 边界是否更清楚。
- 重复实现是否减少。
- 历史结论是否仍可追溯。
- 新研究是否能复用已有基础设施，减少复制旧实验。
