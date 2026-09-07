# Strategy Pipeline Alpha 兼容门面审计

日期：2026-09-02
范围：委托给 `alpha-research` 的五个 `strategy-pipeline` 兼容门面
决定：在仓库规定的两次发布评审删除条件满足前保留。消费者迁移已完成。

## 已审计门面

| Pipeline facade | Owner replacement |
| --- | --- |
| `strategy_pipeline.pipeline.freshness_overlay` | `alpha_research.freshness_overlay` |
| `strategy_pipeline.pipeline.train_eval_request_builder` | `alpha_research.train_eval_request_builder` |
| `strategy_pipeline.pipeline.train_eval_result` | `alpha_research.train_eval_result` |
| `strategy_pipeline.pipeline.research_ops.promotion_gate` | `alpha_research.promotion_gate` |
| `strategy_pipeline.pipeline.research_ops.promotion_gate_thresholds` | `alpha_research.promotion_gate_thresholds` |

## 证据

### 仓库内扫描

2026-09-02 对 `strategy-pipeline` 的代码搜索没有发现生产调用方导入五个门面模块路径。剩余引用来自门面文件本身、兼容性和治理测试、命名空间冒烟覆盖、测试影响映射以及历史或证据文本。

调用方迁移已于 2026-08-10 由 strategy-pipeline 提交 `dcc4af707724bed09abb930e131db6310b1a3939`、PR #43 完成。该提交明确将生产环境的 `promotion_gate` 和 `freshness_overlay` 调用方改到 `alpha_research.*`，并记录 train/eval 与 threshold 门面已经委托给 owner，生产调用方可以删除。

### 下游扫描

2026-09-02 对以下关联仓库的代码搜索没有发现运行时导入五个 `strategy_pipeline` 门面路径的引用：

- `strategy-app`
- `alpha-research`
- `market-data-platform`
- `portfolio-backtester`
- `research-workspace`

工作区中的引用属于治理记录、可维护性证据和删除清单，不是运行时消费者。

### 替代实现文档

`docs/compatibility-facades.yml` 已记录每个门面对应的 `alpha_research.*` 直接替代实现，不需要新增兼容包。

### 针对性测试

删除时必须保留 owner 测试以及 pipeline 命名空间和导入冒烟测试。仅为证明兼容性而有意导入门面的 pipeline 测试，应在删除 PR 中删除或改为测试 owner API。这类测试不能证明存在真实下游消费者。

### 回滚

如果删除后发现此前未观测到的外部消费者，应从上一版 `strategy-pipeline` 发布标签恢复完全相同的包装器，同时让消费者迁移到文档中的 `alpha_research.*` owner API。不要再增加第二套替代门面。

## 删除决定

技术消费者审计已完成，结果为零个运行时消费者。因此这些文件已经具备代码删除条件，但注册表的明确删除条件仍要求两次发布评审。本审计不会把时间流逝或普通提交重新解释为发布评审。

删除应在第一次能够证明剩余评审次数条件满足的 strategy-pipeline 发布评审中进行。删除 PR 应：

1. 将五个包装模块作为一个兼容批次一并删除。
2. 删除或更新保护这些包装器本身的 pipeline 测试和命名空间冒烟条目。
3. 在同一次工作区同步中从 `docs/compatibility-facades.yml` 删除五条记录。
4. 删除对应的 strategy-pipeline 导入边界债务条目。
5. 合并前重新运行仓库内和下游扫描。
6. 保留本审计作为证据，不重写历史。

## 单独的未注册根包装器

同时检查了 `strategy_pipeline.return_metrics`、`strategy_pipeline.sharpe_stats` 和 `strategy_pipeline.liquidity_proxy`。搜索没有发现真实下游运行时消费者，当前引用来自迁移或归档文档、边界规则和 owner 测试。它们不属于上面注册的五个 alpha 门面，删除前需要单独做注册表和发布策略决定。
