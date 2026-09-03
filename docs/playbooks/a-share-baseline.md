# A 股 baseline 运行手册

> 状态：active
> 维护方：research-workspace
> 核对时间：2026-09-04

本文给出 A 股研究基线的阅读顺序、运行入口和验收边界。数据资产由
`market-data-platform` 维护，特征与信号由 `alpha-research` 维护，组合与回测由
`portfolio-backtester` 维护，策略专用计算由 `strategy-app` 维护，运行编排和执行交接由
`strategy-pipeline` 维护。

## 当前基线

A 股是工作区当前的研究主线。默认入口使用日频价格、估值信息和按日期保存的全市场股票池。
财务报表和历史行业特征通过显式配置开启，数据资产已经发布不代表研究结果自动达到生产级。

策略身份、投资假设、生命周期和证据导航以 `strategy-research/catalog.json` 为准。代码所在仓库
不代表策略已经进入生产状态。

## 最小前置条件

先确认 `DATA_PLATFORM_ROOT` 指向数据平台的共享资产根目录，并检查 A 股当前契约：

```text
$DATA_PLATFORM_ROOT/metadata/current_assets/a_share_current.json
```

研究运行至少需要以下边界：

- 使用数据平台发布的 `daily_clean` 和 `instruments` 资产。
- 使用按日期保存的全市场股票池，不用当前指数成分回填历史股票池。
- 需要时间点财务或历史行业时，先核对对应资产的 current contract、覆盖范围和可用日期语义。
- 研究结果和运行凭证放在数据根目录或生产目录，不提交到工作区 Git。
- `targets.json` 是研究到执行的文件交接格式，真实券商能力由 `quant-execution-engine` 单独验收。

## 推荐运行顺序

### 1. 检查工作区和数据契约

```bash
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
```

需要确认当前资产清单存在，数据平台的质量检查已经通过，工作区子模块指针处于同一版本组合。

### 2. 运行 A 股日频基线

```bash
strategy run --config default
```

运行后检查运行目录中的 `summary.json`、`config.used.yml` 和持仓文件。`config.used.yml` 是本次运行
实际使用配置的记录，发生争议时以它为准。

重点核对以下字段：

```yaml
market: a_share
data:
  source_mode: platform_assets
research_universe:
  mode: pit
  require_by_date: true
execution:
  market: a_share
```

`default_next` 只用于迁移兼容和历史脚本。新增运行应使用 `default`。

### 3. 完成研究证据检查

基线可复现后，再检查 benchmark、时间序列交叉验证、最终样本外、成本、换手、容量、暴露和晋升证据。
这些证据分别由 alpha 研究、组合回测和策略研究模块维护，不能用一次短窗口运行替代。

顶层就绪度分为四档：

| 就绪度 | 含义 |
| --- | --- |
| `baseline_reproducible` | 数据契约、研究输出和目标文件链路可以复现 |
| `complete_pit_research_data` | 补齐时间点财务、历史行业和研究窗口覆盖 |
| `production_strategy_evidence` | 补齐长窗口、基准、交叉验证、成本、容量和晋升证据 |
| `broker_trading_enabled` | 执行引擎完成券商适配、权限、监督和操作批准 |

就绪度检查只读取契约、清单和证据，不会自动训练模型或连接券商。详细规则见
[`strategy-evidence-gate.md`](../strategy-evidence-gate.md) 和
[`data-transition-playbook.md`](../data-transition-playbook.md)。

### 4. 导出执行目标

研究结果通过流水线导出标准目标文件：

```bash
strategy export-targets
```

导出结果至少包括 `targets.json` 和对应的 lineage 文件。先在
`quant-execution-engine` 中执行文件解析和 dry-run，再考虑模拟盘或实盘流程。文件解析成功只说明
交接格式正确，不代表已经获得真实下单资格。

## 港股边界

港股资产按恢复专用归档管理。需要复现历史港股运行时，先按照
[`archive/hk/README.md`](../archive/hk/README.md) 和数据迁移手册恢复明确版本，再使用对应的市场配置。
新的 A 股研究不能直接复用港股 benchmark、交易日历、港股通约束或市场专项参数。

## 常见误区

- 数据资产已经发布，不等于策略证据已经通过。
- 全市场按日期股票池，不等于时间点财务或历史行业数据。
- `targets.json` 能被解析，不等于券商实盘已经放行。
- 短窗口基线成功，不等于长窗口研究已经完成。
- 研究配置和实际运行配置不一致时，以运行目录中的 `config.used.yml` 为准。

## 相关文档

- [平台工作流与集成边界](../platform-workflow.md)
- [A 股数据与研究入口](../data-transition-playbook.md)
- [跨仓库产物契约](../contracts.md)
- [策略证据门禁](../strategy-evidence-gate.md)
- [生产发布检查](../release-checklist.md)
