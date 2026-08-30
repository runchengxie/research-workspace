# Market Intel 与研究工作区职责边界

## 结论

`market-intel` 继续作为 `research-workspace` 的兄弟系统，区别于本工作区的子模块。两者生命周期不同：本工作区负责可复现的数据、研究、策略和执行链，`market-intel` 负责市场上下文、面向人的报告、Dashboard、飞书投递和运行保障。

2026-08-30 起，`market-intel` 退休并移除历史三个 owner submodule：

- `a-share-factor-core`
- `hot-sector-screener`
- `ai-stock-picker`

这些仓库曾承担的活跃研究职责已经由本工作区现有 owner 接管，不再通过把同一实现复制到第二个 superproject 来表达 ownership。

## 当前 owner 映射

| 历史 market-intel 能力 | 当前 owner |
| --- | --- |
| DailyWatch20 分钟/Hermite/消融与研究应用 | `strategy-app` + `alpha-research` + `portfolio-backtester` |
| DailyWatch20 正式 freshness、运行和原子发布 | `strategy-pipeline` |
| 热点板块研究应用、候选约束和 AI shadow 评估 | `strategy-app.hotsector` |
| 外部模型调用与正式发布控制 | `strategy-pipeline` |
| A 股权威数据资产与研究视图 | `market-data-platform` |
| 策略身份、生命周期、研究规格与证据 | `strategy-research` |

`strategy_app.migration_manifest` 记录这批迁移的机器可读状态。

## 对 market-intel 的接口

research-workspace 只向 market-intel 暴露稳定接口：

1. 公开 CLI，例如 `marketdata ...`、`strategy watchlist20 ...`。
2. 版本化 artifact / receipt，例如 DailyWatch20 selection receipt、style-factor publication、D11-H5 artifact。

market-intel 可以在故障恢复中调用公开 producer CLI，但不应：

- import owner 的内部业务源码，
- 复制特征、训练、回测、Hermite、ablation 或 AI ranking 实现，
- 根据相邻目录布局推断 owner 路径，
- 通过旧兼容开关恢复已经退休的 AI 精选产品。

## 发布与变更顺序

跨仓变更采用 provider-first 顺序：

1. owner 仓补齐 API / artifact / migration manifest，
2. research-workspace 更新 gitlink 并通过组合门禁，
3. market-intel 切换 consumer / 运维桥，
4. market-intel 删除重复实现与旧 submodule，
5. 部署时停用旧 research-only timer，并验证正式报告只消费 owner artifact。

本次迁移不改变 DailyWatch20 的正式模型定义或选择结果语义，目标是删除重复 owner、旧调度入口和源码路径耦合。
