# 平台工作流与集成边界

本页描述 `research-workspace` 中各模块如何组成数据到研究与执行交接链路，以及可选交易执行系统的验证边界。顶层仓库负责表达能力地图和锁定已确认的版本组合，不承担各模块内部业务逻辑。

## 当前边界

截至 2026-05-26，工作区正式锁定以下研究到执行交接链路：

```text
数据资产维护 / 盘口加工 -> 共享数据契约 -> 策略研究与回测 -> canonical targets 导出 -> 可选执行引擎契约 / 离线计划验证
```

券商执行是下一段可选链路：

```text
持仓 / 分配结果 -> 目标持仓交接契约 -> 执行 preflight / paper 验证 -> 显式 live 门禁 -> 券商执行
```

当前 `cross-sectional-trees` 已实现 canonical `targets.json` 与 lineage sidecar 的显式导出入口；`quant-execution-engine` 已作为可选 submodule 固定版本，用于复现契约交接和离线计划验证。paper / live 操作验证与运行门禁仍属于独立执行系统的职责。

## 模块分工

| 层级 | 模块 | 职责 | 当前接口 |
| --- | --- | --- | --- |
| 数据平台入口 | `market-data-platform` | 定义共享路径、contract、registry，原生维护 CN TuShare / RQData MVP，并统一调度迁移中的 HK 数据工具 | `marketdata tushare ...`、`marketdata rqdata hk-{depth,assets} -- ...`、current contract |
| 盘口迁移 backend | `rqdata-hk-depth-snapshots` | 在物理迁移完成前承载港股十档盘口的下载、检查、聚合和发布实现 | 由 `marketdata rqdata hk-depth -- ...` 调用 |
| 策略研究 | `cross-sectional-trees` | 消费发布数据，完成特征、模型、评估、回测、持仓分配和显式执行目标交接 | `summary.json`、`positions_current*.csv`、snapshot / alloc、canonical `targets.json` 与 lineage |
| 交易执行（可选） | `quant-execution-engine` | 消费目标持仓，连接券商执行调仓、对账和异常恢复 | 标准化 `targets.json` 输入、订单审计输出 |

## 正式研究链路

### 1. 发布数据资产

数据资产的共享点是版本化资产目录和 current contract，而不是某个代码仓库的临时输出目录。

```text
<artifacts_root>/
  assets/
  metadata/
    current_assets/
      hk_current.json
      cn_current.json
    dataset_registry.csv
  reports/
```

目前 `market-data-platform` 已提供 CN provider 实现和统一数据维护入口；部分 HK
日线 / PIT 等维护实现仍在 `cross-sectional-trees` 中作为
`marketdata rqdata hk-assets -- ...` 的 transition backend，盘口 raw / daily
聚合实现仍由 `rqdata-hk-depth-snapshots` 作为
`marketdata rqdata hk-depth -- ...` 的 transition backend 承载。

### 2. 消费数据并完成研究

`cross-sectional-trees` 应读取 current contract 解析出的已发布数据资产，而不是硬编码其他模块的工作目录。其正式职责包含：

- 特征工程、训练与评估；
- 历史回测、benchmark 对比和研究证据管理；
- 当前持仓、snapshot 和执行前资金 / 手数分配输出。
- 使用 `cstree export-targets` 将已保存且通过门禁的 long-only live 持仓导出成执行引擎输入文件，并保留 lineage sidecar。

### 3. 锁定可复现组合

当某组数据契约、盘口工具、策略版本和可选执行接口已经共同验证后，顶层仓库通过 submodule commit 指针锁定这组组合。数据本体仍保存在发布目录、归档介质或 release asset 中，不写入顶层 Git 历史。

## 可选执行链路

### 当前接入程度

研究侧目前可通过 `cstree export-targets` 将 `positions_current*.csv` / live holdings 交接成执行引擎接受的标准化 `targets.json`。导出器会拒绝 short 持仓、非法权重和隐式杠杆，并将 run、输入文件、时间口径和质量门禁信息保存到独立 sidecar。

执行引擎已作为固定 submodule 纳入工作区。当前已使用真实研究导出产物验证引擎 canonical parser 和离线调仓计划路径，包括目标列表以外持仓的清仓处理；引擎对港股等非 USD 报价要求先配置 FX 并换算至 USD 估值，避免混币种计算。

尚未完成的是：使用实际 paper broker 凭证形成的端到端持续联调证据，以及任何 live 下单自动化。

因此当前约束是：

- README 和 submodule 指针可以表达已验证的研究到执行交接版本组合。
- `export-targets` 只导出文件；研究结果不得被顶层脚本默认提交给真实券商执行。
- 执行引擎作为可选下游接入，不等同于 paper 或 live 下单路径已经放行。

### 执行放行门槛

| 门槛 | 需要形成的交付 |
| --- | --- |
| 目标持仓契约 | 已落地：研究侧输出 `quant-execution-engine.targets/v2` canonical `targets.json` |
| 导出能力 | 已落地：`cstree export-targets` 输出目标文件及 run / config / 数据资产 lineage sidecar |
| 输入验证 | 已落地：执行侧接受真实导出文件，港股 symbol 可生成计划，非 USD 报价在缺少 FX 时拒绝调仓 |
| 联调证据 | 部分落地：已具备 parser 与离线计划验证；仍需 paper broker 的端到端验证记录 |
| 实盘门禁 | live 下单仍要求执行引擎独立的显式启用、preflight 和人工监督流程 |

当前 submodule 接入使工作区能够复现“研究到执行交接”；在 paper 证据和实盘门禁完成前，不应将其表述为已可自动执行交易。

## 调度原则

当前阶段应先稳定模块间契约和顺序说明，不在顶层建立包含业务逻辑的中央调度器。

未来若跨模块流程已经稳定并且反复需要统一执行，顶层编排层应保持很薄：

1. 仅调用各模块公开 CLI，不 import 子模块内部实现。
2. 每一步检查 versioned input、manifest、current contract 和输出状态。
3. 将 run id、输入资产版本、子模块 commit 和质量检查结论写入可审计记录。
4. 数据维护与研究可以被编排；真实券商执行不能作为无人确认的默认下一步。

## 推荐阅读

| 主题 | 文档 |
| --- | --- |
| 数据控制面与迁移顺序 | [`market-data-platform/docs/README.md`](../market-data-platform/docs/README.md) |
| 策略研究主流程 | [`cross-sectional-trees/docs/pipeline-overview.md`](../cross-sectional-trees/docs/pipeline-overview.md) |
| 共享 HK 数据边界 | [`cross-sectional-trees/docs/concepts/shared-hk-data-platform.md`](../cross-sectional-trees/docs/concepts/shared-hk-data-platform.md) |
| 盘口资产处理工作流 | [`rqdata-hk-depth-snapshots/docs/workflow.md`](../rqdata-hk-depth-snapshots/docs/workflow.md) |
| 可选交易执行系统 | [`quant-execution-engine`](../quant-execution-engine/README.md) |
| 顶层初始化与检查 | [`bootstrap.md`](bootstrap.md)、[`contracts.md`](contracts.md)、[`release-checklist.md`](release-checklist.md)、[`version-matrix.md`](version-matrix.md) |
