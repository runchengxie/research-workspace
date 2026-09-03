# strategy-pipeline-internal 依赖关系图

> status: active
> owner: workspace
> source: internal `pyproject.toml`、源码导入和当前 submodule 关系
> last_verified: 2026-09-03

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
  --glob '!docs/archive/**' \
  --glob '!docs/migrations/**'
```

历史归档中的引用只用于恢复和溯源，必须在归档说明中标注，不能重新成为默认安装、CI 或运行入口。
