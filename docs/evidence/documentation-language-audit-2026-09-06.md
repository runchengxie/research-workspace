# 文档语言审计

> 审计日期：2026-09-06
>
> 审计范围：`research-workspace`、`market-data-platform`、`quant-platform`、`quant-research` 的受版本控制 Markdown 文档，包括根目录入口、`AGENTS.md`、`docs/`、研究记录、归档、设计稿和执行计划。

## 结论

上一轮迁移文档已经把仓库职责、迁移边界和目标架构写入主要入口，但没有完成全量中文化。当前需要处理的内容分成三类：

1. 新目标仓库入口仍有英文正文，尤其是 `quant-platform` 和 `quant-research`。
2. 当前有效的技术文档、研究记录和操作说明中，仍有较多英文文件。
3. 历史归档、`superpowers/plans` 和 `superpowers/specs` 中保留了大量英文设计记录。

仓库名称、Python 命名空间、CLI 命令、路径、配置键、schema 字段、协议名称、许可证原文和代码块中的可执行内容不属于翻译目标。说明性正文、标题、表格说明、注释性文字和状态描述属于翻译目标。

## 数量概览

以下数量来自 Git 已跟踪 Markdown 文件。语言分类使用保守规则：英文字符超过 300 个且没有足够中文字符的文件计为英文主导文件。该规则会把代码示例较多的中文文档归入混合或短文档，因此结果适合作为筛查底稿，不代表机器翻译质量评分。

| 仓库 | Markdown 文件 | 英文主导文件 | 重点问题 |
| --- | ---: | ---: | --- |
| `research-workspace` | 200 | 66 | 根仓库入口基本已中文化，历史计划和设计稿仍有大量英文 |
| `market-data-platform` | 56 | 12 | 核心入口基本中文，L2 文档、运维 README 和设计稿仍有英文 |
| `quant-platform` | 100 | 23 | 入口已明显改善，部分文档索引、alpha、回测和组合文档仍混杂英文 |
| `quant-research` | 532 | 195 | 入口已明显改善，研究记录、历史归档和复制过来的旧项目文档问题最多 |
| 合计 | 888 | 296 | 还需要逐文件确认代码示例和历史记录的翻译边界 |

`research-workspace` 的 Git 索引只记录子模块指针，不包含子模块内部 Markdown。因此上表中的 200 个文件不包含工作区下各旧子模块的内部文档。`quant-research` 还包含部分继承自旧研究项目的数据平台、alpha research、strategy app 和 strategy research 文档，需要在翻译时重新确认归属和状态。

## 分仓库筛查结果

### research-workspace

入口文档已经基本中文化，优先处理以下内容：

- `docs/superpowers/plans/` 中的研究、架构、数据布局、执行和治理计划
- `docs/superpowers/specs/` 中的设计说明
- `docs/archive/` 中仍会被检索或引用的历史记录
- `docs/evidence/`、`docs/research/`、`docs/runbooks/` 中的英文正文
- `docs/platform-asset-registry.md`、`docs/execution-semantic-parity.md` 等现行参考文档

历史计划不应简单删除或改写结论。应保留原始决策、补充中文标题和摘要，并标明文档状态、对应任务和当前是否仍然有效。

### market-data-platform

根目录 `README.md`、`AGENTS.md` 和 `docs/README.md` 已经适合中文新人阅读。仍需处理：

- `docs/l2-ingestion-gate.md`
- `docs/l2-special-event-semantics.md`
- `docs/superpowers/plans/` 下的分钟数据、质量门禁、TuShare 和生命周期迁移文档
- `docs/superpowers/specs/` 下的 L2、质量契约和分钟数据设计文档
- `scripts/systemd/README.md`
- `docs/archive/` 下的历史运维和回填记录

该仓库的翻译重点是保持数据字段、供应商名称、命令、路径和质量门禁名称不变，同时把操作步骤和故障判断写成中文。

### quant-platform

目前最需要优先处理的是：

- `README.md`
- `AGENTS.md`
- `docs/README.md` 中仍保留的英文状态字段和旧 owner 描述
- `docs/data/README.md`、`docs/execution/README.md`、`docs/microstructure/README.md`
- `docs/concepts/` 中的组合优化、因子归因、差异回测和风险后端文档
- `docs/alpha/concepts/` 中的因子目录、风险模型、模型风险和信号漂移文档
- `docs/orchestration/cashflow-publication.md`
- `docs/superpowers/plans/` 和 `docs/superpowers/specs/` 中的设计记录

这里要同时修正文档事实：入口不应继续把 `portfolio-backtester` 写成当前 owner，迁移状态、公共能力边界和回滚来源要与当前 `main` 保持一致。

### quant-research

这是翻译量最大的仓库。优先级如下：

- 根目录 `README.md` 和 `AGENTS.md`
- `docs/README.md`、`docs/project-status.md`、开发和研究操作指南
- 现金流指数、机器学习、DailyWatch20、基本面预测和策略生命周期文档
- `research/evidence/` 中用于当前决策的审计记录和结果说明
- `research/experiments/` 中仍被引用的正式结果和研究结论
- `docs/alpha-research/`、`docs/market-data-platform/`、`docs/strategy-app/`、`docs/strategy-research/` 中继承的旧项目文档
- `research/experiments/**/archive/` 中的历史研究记录
- `docs/archive/` 和旧项目目录下的归档文档

这里不能只做字面翻译。每份继承文档都需要补充归属、当前 owner、是否仍是 source of truth、是否已被新仓库文档取代，以及与 `market-data-platform` 或 `quant-platform` 的关系。

## 翻译边界

### 保留英文

- 仓库名、包名、Python 命名空间和模块名
- CLI 命令、环境变量、配置键、schema 字段和 artifact 名称
- 文件路径、URL、Git 分支名和 commit hash
- 第三方项目、供应商、模型和协议的官方名称
- 可执行代码块、JSON、YAML、SQL、正则表达式和 API 签名
- Apache、MIT 等许可证的法律原文

### 翻译成中文

- 文档标题、章节标题和目录说明
- 背景、职责、限制、状态、决策和迁移说明
- 表格中的描述、注释和阅读建议
- 命令前后的解释文字
- 研究结果、风险解释、操作步骤和故障排查说明
- 历史文档的摘要、状态和当前有效性说明

### 历史文档处理方式

历史归档保留原始文件名、日期、结论和证据引用。正文翻译完成后，在顶部增加中文元信息：

```markdown
> 文档状态：历史归档
> 当前有效性：仅作为历史记录，不作为当前实现依据
> 当前参考：`docs/...`
> 原始语言：英文
```

原文如果具有审计、合规或证据价值，可以保留英文段落，但必须先提供完整中文摘要，并明确原文位置。

## 后续执行计划

详细执行步骤见 [`docs/superpowers/plans/2026-09-06-documentation-chinese-localization.md`](../superpowers/plans/2026-09-06-documentation-chinese-localization.md)。
