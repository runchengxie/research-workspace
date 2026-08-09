# 准生产策略（pre_production）

已验证、值得长期跟踪但尚未完全生产化的量化策略。每个子目录是一个自包含的策略，
通过框架公共 API 消费数据、研究和回测能力，不反向依赖框架内部。

## 策略研究分层

`strategy-research/` 收纳全部策略身份和人类可读研究记录。生命周期以 [../catalog.json](../catalog.json) 为准，目录只服务组织和导航：

| 层 | 目录 | 定位 | 门槛 |
| --- | --- | --- | --- |
| 短期探索 | `strategy-research/experiments/` | 一次性想法与结论记录 | 无门槛，快速试错 |
| 准生产 | `strategy-research/pre_production/` | 已验证、值得跟踪、未完全生产化 | 验证证据（见下方升格门槛） |
| 生产或受控运行 | `strategy-research/catalog.json` 中的显式状态 | 已有受控运行或发布路径 | 证据评审与发布 gate |

代码位置不表达生命周期。策略特有纯计算进入 `strategy-app`，运行和发布控制进入 `strategy-pipeline`，通用能力进入相应职责仓。

## 目录

| 策略 | 说明 | 状态 |
| --- | --- | --- |
| `dividend_growth_momentum/` | 红利 vs 成长 ETF 动量轮动 | 已迁移，待补充验证证据 |

## 从 experiments 升格到 pre_production 的门槛

一个探索从 `experiments/` 升格到 `pre_production/` 需要同时满足：

1. 有明确结论，实验 README 记录可复现的收益、IC 或回测结论。
2. 有验证证据，至少包含独立验证的结果文件或证据 JSON，并能追溯到实验脚本。
3. 值得长期跟踪，策略逻辑可定义、可监控。
4. 消费框架公共 API，通过职责仓公开接口取数、训练和回测。
5. 在 `catalog.json` 登记生命周期、生产资格、代码 owner 和已知迁移债务。

## 从 pre_production 升格到 production 的门槛

策略获得生产资格并进入 `targets.json` 交接链路时走现有治理：

- 通过 `strategy-pipeline` 的发布 gate 和证据要求
- 符合 `docs/framework-support-matrix.md` 的框架边界
- 由 `docs/script-lifecycle.yml` 和维护性治理记录管理生命周期
- 更新 `catalog.json` 的评审证据与 `production_eligible`，不以移动代码代替授权

## 规则

- 每个策略目录自包含：策略脚本 + README（结论）+ 验证证据
- 不引入跨策略隐式依赖；可复用逻辑沉淀到框架子仓库的正式包里
- 策略只通过框架公共 API 消费能力，不反向依赖、不改框架内部
- 长时间无跟踪更新的策略应降级回 `experiments/` 或归档
- 维护性治理：`pre_production/` 默认不计入根仓库活跃债预算（同 `experiments/`）。
  策略升格 production（进入 `strategy-pipeline` campaign）时，才纳入正式维护性治理
  并接受代码拆分与质量门禁。这个约定随 `maintainability_baseline.py` 的排除规则维护。
