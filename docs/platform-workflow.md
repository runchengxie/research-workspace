# 平台工作流与集成边界

本页描述 `research-workspace` 中各模块如何组成数据到研究的正式链路，以及可选交易执行系统在什么条件下可以接入。顶层仓库负责表达能力地图和锁定已确认的版本组合，不承担各模块内部业务逻辑。

## 当前边界

截至 2026-05-26，工作区正式纳入以下链路：

```text
数据资产维护 / 盘口加工 -> 共享数据契约 -> 策略研究与回测 -> 持仓及执行前分配结果
```

券商执行是下一段可选链路：

```text
持仓 / 分配结果 -> 目标持仓交接契约 -> 执行 preflight / paper 验证 -> 显式 live 门禁 -> 券商执行
```

当前后半段尚未在本工作区内形成可运行的跨仓库集成，因此 `quant-execution-engine` 被记录为可选下游，而不是本仓库锁定的 submodule。

## 模块分工

| 层级 | 模块 | 职责 | 当前接口 |
| --- | --- | --- | --- |
| 数据控制面 | `market-data-platform` | 定义共享路径、asset keys、current contract、dataset registry、health 和发布规范 | `<artifacts_root>/metadata/current_assets/<market>_current.json`、manifest |
| 盘口资产加工 | `rqdata-hk-depth-snapshots` | 下载、检查、聚合和发布港股十档盘口资产 | `tick_depth_raw`、`tick_depth_daily`，未来 `execution_cost_model` |
| 策略研究 | `cross-sectional-trees` | 消费发布数据，完成特征、模型、评估、回测和持仓分配 | `summary.json`、`positions_current*.csv`、snapshot / alloc |
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

目前 `market-data-platform` 提供控制面规范；部分日线 / PIT 等维护实现仍在 `cross-sectional-trees` 中按迁移计划过渡，盘口 raw / daily 聚合由 `rqdata-hk-depth-snapshots` 负责。

### 2. 消费数据并完成研究

`cross-sectional-trees` 应读取 current contract 解析出的已发布数据资产，而不是硬编码其他模块的工作目录。其正式职责包含：

- 特征工程、训练与评估；
- 历史回测、benchmark 对比和研究证据管理；
- 当前持仓、snapshot 和执行前资金 / 手数分配输出。

### 3. 锁定可复现组合

当某组数据契约、盘口工具和策略版本已经共同验证后，顶层仓库通过 submodule commit 指针锁定这组组合。数据本体仍保存在发布目录、归档介质或 release asset 中，不写入顶层 Git 历史。

## 可选执行链路

### 当前不直接接入的原因

研究侧当前正式交付为 `positions_current*.csv` 与 `alloc-hk` 等结果；执行引擎公开接收的是标准化 `targets.json`。两者在顶层工作区中尚无已验证的转换器、schema 版本和跨仓库 paper 验证记录。

因此当前约束是：

- README 可以展示执行引擎在完整平台中的位置。
- 研究结果不得被顶层脚本默认转换并触发真实券商执行。
- 执行引擎暂不加入 pinned submodule 组合，避免将未完成的集成误表示为已支持流程。

### 纳入执行引擎前的验收门槛

| 门槛 | 需要形成的交付 |
| --- | --- |
| 目标持仓契约 | 版本化 schema，定义日期、来源、市场、symbol、目标权重、gross exposure 和校验规则 |
| 导出能力 | 研究侧显式导出执行引擎输入文件，并保留 run / config / 数据资产 lineage |
| 输入验证 | 执行侧能够在提交订单前验证 schema、symbol、市场、资金和风险约束 |
| 联调证据 | 至少具备 dry-run 与 paper broker 的端到端验证记录 |
| 实盘门禁 | live 下单仍要求执行引擎独立的显式启用、preflight 和人工监督流程 |

满足这些条件后，可以重新评估将 `quant-execution-engine` 纳入顶层 submodule，使工作区表达从“数据与研究复现”扩展为“研究到执行交接复现”。

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
| 可选交易执行系统 | [`quant-execution-engine`](https://github.com/runchengxie/quant-execution-engine) |
