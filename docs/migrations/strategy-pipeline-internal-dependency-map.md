# strategy-pipeline-internal 依赖关系图

> status: active
> owner: workspace
> source: internal `pyproject.toml`、源码导入和当前 submodule 关系
> last_verified: 2026-09-04

## 当前关系

```text
research-workspace
  └─ strategy-pipeline-internal
       ├─ strategy-pipeline
       ├─ alpha-research
       ├─ market-data-platform
       ├─ portfolio-backtester
       ├─ strategy-app
       └─ research-contracts
```

internal 当前同时承担策略应用、研究证据、数据接口、组合回测、执行交接、CLI 和运行目录编排。这个组合关系是退役风险的来源，单独替换 CLI 或公共包不能解除它。

本次切片已将 `pipeline/position_output_artifacts.py` 的持仓视图写入职责归入 `portfolio-backtester.position_outputs`。internal 的输出编排仍在过渡期保留，但不再维护这份重复实现。

`pipeline/position_postprocess_artifacts.py` 的后处理诊断写入职责也已归入 `portfolio-backtester.position_postprocess_outputs`，并由 owner API 继续维护四类运行产物。

`pipeline/output_context.py` 已归入公共 `strategy-pipeline.control_plane.output_context`，internal 输出编排只消费公共上下文接口。

`pipeline/output_summary.py` 已确认只是兼容 facade。输出模块现在直接调用 summary sections 和 metadata 实现，internal 不再保留这层重复入口。

`commands/__init__.py` 和 `release_tools/__init__.py` 只提供空包入口，已在 internal PR #214 中退役。对应的命令和发布工具子模块继续保留原有导入路径，因此这次清理不会改变运行入口。

根包 `__init__.py` 和 `liveops/__init__.py` 也已在 internal PR #215 中退役。根包和 liveops 子模块继续通过原有路径加载，workspace 不依赖这些初始化 facade。

`commands/tune/__init__.py` 已在 internal PR #216 中退役。调参 CLI 和 runner 直接使用 `parser`、`report`、`spec` 实现模块，原有调参子模块路径继续可用。

`pipeline/owner_ports.py` 已在 internal PR #217 中迁入公共 `strategy-pipeline.control_plane.ports`。协议、适配器和运行回执属于无领域知识的控制面，internal 的 pipeline runner 已切换到公共版本。

## 目标关系

```text
market-data-platform
  └─ 发布数据资产、provider、PIT 和数据契约

alpha-research
  └─ 读取数据契约，维护 alpha、特征、模型、信号和研究证据

portfolio-backtester
  └─ 读取数据与研究证据，维护组合、回测、成本、容量和暴露

strategy-app
  └─ 组合策略应用、policy、campaign 和决策解释

strategy-research
  └─ 维护实验 runner、研究配置和试验账本

quant-execution-engine
  └─ 消费 targets，维护风险、订单、券商适配和执行审计

research-workspace
  └─ 维护跨仓 schema、版本组合、集成测试和治理索引

strategy-pipeline
  └─ 只维护无领域知识的 request、artifact、receipt、publication 和 handoff
```

## 退役检查

每个迁移 PR 必须在本文件补充一条从旧模块到新 owner 的边，并在对应 manifest 记录迁移 commit。internal 只有在以下命令都找不到 active 引用时才能进入冻结阶段：

```bash
rg -n "strategy_pipeline_internal|strategy-pipeline-internal" . \
  --glob '!docs/archive/*' \
  --glob '!docs/migrations/*'
```

历史归档中的引用只用于恢复和溯源，必须在归档说明中标注，不能重新成为默认安装、CI 或运行入口。
