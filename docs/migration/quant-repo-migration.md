# 量化仓迁移说明

> status: active
> owner: research-workspace maintainers
> audience: human and agent
> last_verified: 2026-09-06

## 结论

`research-workspace` 将逐步 sunset。它保留为历史工作区、跨仓库版本组合和迁移导航入口，不再作为新策略或新平台能力的默认实现仓库。

新的权威边界如下：

```text
quant-platform  -> 通用数据接口、回测、组合构造、风险、执行模拟和公共 contracts
quant-research  -> 私有策略 IP、因子、机器学习、实验、研究证据和策略应用
market-intel    -> 报告、看板、消息交付和运营入口
```

## 旧模块映射

| 旧模块 | 目标归属 | 迁移期用途 |
| --- | --- | --- |
| `alpha-research` | `quant-research`，公共机制另行进入 `quant-platform` | 历史研究和迁移兼容 |
| `strategy-research` | `quant-research` | 策略身份、实验和证据的历史来源 |
| `strategy-app` | `quant-research` | 策略专用计算和应用兼容 |
| `strategy-pipeline` | `quant-research`，公共编排能力进入 `quant-platform` | 历史编排入口 |
| `portfolio-backtester` | `quant-platform` | 通用组合和回测能力迁移来源 |
| `market-data-platform` | 独立数据平台项目 | 数据生产、质量治理、版本和发布，不迁入 `quant-platform` |
| `quant-execution-engine` | `quant-platform` 的执行接口边界 | 执行兼容和审计复现 |
| `deep-learning-tick-data-prediction` | 按模型专用逻辑进入 `quant-research`，通用数据能力进入 `quant-platform` | 模型研究历史来源 |

## 新代码放置规则

- 现金流策略的 PIT 特征、ML 选股、实验协议和策略结论进入 `quant-research`。
- `market-data-platform` 继续独立负责 provider、数据生产、质量治理、版本和 published asset。
- 现金流指数权重、组合构造、风险约束、D11-H5 执行模拟等可复用机制进入 `quant-platform`。
- 策略专属参数和模型不得放入 `quant-platform`。
- `research-workspace` 只保留导航、版本锁定、兼容说明和历史复现所需内容。

## 迁移期阅读顺序

1. 先读本页，确认模块归属。
2. 再读 [`quant-research` README](../../../.private-staging/quant-research/README.md) 或 [`quant-platform` README](../../../.public-staging/quant-platform/README.md)。
3. 进入目标仓库的 `docs/` 阅读技术细节、开发命令和质量门禁。
4. 只有需要复现旧结果时，才回到本工作区或旧 submodule。

旧仓库中的实现、路径和实验结果在迁移完成前仍可能是历史事实来源，但不代表新的架构方向。
