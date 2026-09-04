# 策略与研究应用导航

> 状态：reference
> 维护方：research-workspace
> 核对时间：2026-09-04
> 权威策略目录：`strategy-research/catalog.json`

本文用于说明工作区中的策略身份、研究应用、运行编排和执行交接分别由哪个模块负责。
策略身份、投资假设、生命周期和证据导航以 `strategy-research` 为准，本文只维护跨仓入口和术语说明。

## 三个容易混淆的对象

- 策略是可复核的投资假设、候选范围、信号、组合、调仓和风险规则，归 `strategy-research`。
- 策略应用是策略特有的可执行计算和冻结合同，归 `strategy-app`。
- 策略流水线是运行、外部调用、发布和执行交接控制面，归 `strategy-pipeline`。

`StrategySpec` 是信号到组合的技术合同。`strategy run --config ...` 是可配置工作流。它们都不单独代表一项策略。

## 运行入口

| 入口 | 用途 | 输出或边界 |
| --- | --- | --- |
| `strategy run --config default` | 运行当前 A 股默认配置 | 运行目录、摘要和持仓 |
| `strategy summarize` | 汇总已有运行目录 | 只读取已有产物 |
| `strategy init-config` | 生成配置起点 | 不运行研究或回测 |
| `strategy-pipeline export-targets` | 导出执行目标 | `targets.json` 和 lineage 文件 |

可配置流程可以组合信号、组合和回测设置，不绑定固定策略名称。运行入口的完整参数和配置说明以
`strategy-pipeline` 当前文档及工作区锁定版本为准。

## 具名策略与研究应用

策略的身份和生命周期登记在 `strategy-research/catalog.json`。策略特有的纯计算和冻结合同由
`strategy-app` 维护，当前覆盖 DailyWatch20、Hotsector、StyleReplica、D11-H5 以及相关研究变体。
应用输入、输出和证据要求见 `strategy-app/docs/application-catalog.md`。

研究脚本默认生成 `research_only` 产物，不修改线上模型、选股规则或当前指针。实验说明、研究证据和
历史运行记录由 `strategy-research` 维护，不能仅凭脚本名称判断某项策略已经进入生产。

## 当前 A 股主线

A 股是工作区当前研究主线。`default` 是日频价格、日频估值和按日期保存股票池的默认入口，
`default_next` 只用于迁移兼容。时间点财务、历史行业、长窗口、成本、容量和最终样本外证据需要按
就绪度分别验收，数据资产发布或一次运行成功都不能替代这些证据。

详细运行顺序见 [A 股 baseline 运行手册](playbooks/a-share-baseline.md)。

## 执行交接

`strategy-pipeline` 负责从研究产物导出 `targets.json` 和审计附属文件。以下命令服务持仓复核和目标导出：

```bash
strategy holdings --help
strategy snapshot --help
strategy alloc --help
strategy-pipeline export-targets --help
```

这些命令只负责文件和运行控制，不连接券商。`quant-execution-engine` 负责预演、风控、券商适配、下单和审计。
文件解析成功只说明交接格式正确，不代表已经获得实盘资格。

## 当前迁移状态

`strategy-pipeline-internal` 已冻结，正在按清单完成退役迁移。文档迁移项已经完成，代码清单仍记录每个
internal 模块的 owner、替代路径、测试和删除条件：

[strategy-pipeline-internal 迁移清单](migrations/strategy-pipeline-internal-migration-manifest.md)

在清单中的替代入口和验证证据全部完成前，internal 不能正式下线。

## 相关入口

| 目的 | 入口 |
| --- | --- |
| 查看策略身份和生命周期 | [strategy-research/catalog.json](../strategy-research/catalog.json) |
| 阅读策略假设和研究证据 | [strategy-research/README.md](../strategy-research/README.md) |
| 查看策略应用接口 | [strategy-app/docs/application-catalog.md](../strategy-app/docs/application-catalog.md) |
| 查看运行工作流 | [platform-workflow.md](platform-workflow.md) |
| 查看 A 股基线 | [playbooks/a-share-baseline.md](playbooks/a-share-baseline.md) |
| 查看执行交接契约 | [contracts.md](contracts.md) |

新策略或生命周期变化先更新 `strategy-research`，再更新应用接口和运行入口。新增跨仓接入时同步更新本页、
工作区契约和对应测试。
