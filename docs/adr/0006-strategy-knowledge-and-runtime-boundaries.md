# ADR-0006：策略知识、可执行应用与运行控制面分离

- 状态：accepted
- 日期：2026-08-09
- 修订：ADR-0004 的当前仓库名称与职责表述

## 背景

策略思路、研究证据和运行代码分散在 `strategy-research`、原 `research-apps` 与 `strategy-pipeline`。代码位置一度被用来表达策略生命周期，导致生产策略看起来必须属于 pipeline，研究策略又被理解为应用包中的模块。这个结构不利于人工盘点，也促使运行控制面吸收策略计算、研究脚本和重复合同。

原 `research-apps` 已通过 PR #7 改名为 `strategy-app`，Python 命名空间改为 `strategy_app`。历史回执中的 `research_apps...v1` schema 和旧 ADR 名称继续保留，避免改写证据身份。

## 决策

1. `strategy-research` 是策略身份、投资假设、生命周期、评审结论和证据导航的权威位置。
2. `strategy-app` 只承载策略特有的可执行纯计算、冻结实验合同和 owner API 组合。
3. `strategy-pipeline` 只承载运行编排、外部服务调用、操作员控制、运行目录、原子发布、发布门禁和 `targets.json` 交接。
4. 数据、特征、标签、模型、统计推断、组合构造、成本、可交易性与执行回放分别归现有职责仓。两个策略可复用的能力不得留在 `strategy-app`。
5. 策略的生产状态由 `strategy-research/catalog.json` 显式记录。代码所在仓库不表达生命周期。
6. pipeline 中的策略计算、研究脚本、重复合同和 owner facade 按调用方迁移顺序删除，不新增兼容层。

## 依赖方向

```text
strategy-research  人类可读规格与生命周期
        ↓
strategy-app       策略特有纯计算
        ↓
strategy-pipeline  运行与发布控制面
        ↓
targets.json → quant-execution-engine
```

`strategy-app` 可以调用数据、alpha 和组合职责仓，禁止导入 `strategy-pipeline`。`strategy-research` 中的说明文件不得成为运行时依赖。

## 后果

- 人可以从一个目录回答有哪些策略、处于什么阶段、代码和证据在哪里。
- 策略晋级只更新显式生命周期与对应证据，不迁移整套代码来表达状态。
- `strategy-app` 的合理性取决于它是否保持薄且策略专用。若它发展出通用框架、第二套 contract 或 service locator，就属于过度抽象。
- pipeline 的体量下降不以移动文件数量为目标，而以删除重复实现、兼容 facade 和错误归属为目标。
