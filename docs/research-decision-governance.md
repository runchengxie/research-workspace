# 研究判断治理

> status: active
> owner: workspace、strategy-research
> last_verified: 2026-08-18
> source_of_truth: yes
> superseded_by: n/a

本页登记研究判断层的设计目标和采用顺序。它回答三个问题：我们究竟在相信什么，凭什么相信，
看到什么以后必须停止相信。

## 定位

现有体系已经覆盖实验与证据的工程治理：

- `research_spec.v1` 回答这次实验到底做了什么
- `evidence_policy.v1` 与 `strategy_evidence_gate.py` 回答策略当前凭什么达到某个生命周期
- `catalog.json` 与证据包登记生产资格和已知缺口

这套体系擅长验证经验证据的有效性，比如 PIT、walk-forward、CPCV、成本、最终样本外和市场状态。
它还没有同等强度地管理研究判断本身的可信度，比如某个判断有哪些事实支撑、哪些事实反驳、
最关键的假设是什么、什么观测一出现就必须推翻判断。

本页要补齐的就是这一层。它是决策线索，不是新的知识库或文档层级。不改变现有架构，
只在 `strategy-research` 增加机器可检查的判断对象。

## 设计目标

1. 把策略的投资判断从 README 叙述提升为机器可检查的一等对象。
2. 区分事实与推演，区分经验证据与来源证据。
3. 缺数据时显式放弃判断，禁止用模型补全叙事。
4. 判断的评审由独立视角完成，最终由人类裁决。
5. 每个判断都可以追溯到问题、实验、证据和生命周期。

## 概念映射

| 现有组件 | 回答的问题 |
| --- | --- |
| `research_spec.json` | 这次实验到底做了什么 |
| `evidence_policy.json` 与证据门禁 | 该信什么，证据是否通过强制检查 |
| `catalog.json` | 策略处于哪个生命周期 |
| 本页定义的判断对象 | 为什么可以信这个判断，什么出现就推翻它 |

## 待采用项目

### DG1 判断账本 schema

在 `strategy-research` 增加 `claim.v1` schema，让判断成为机器可检查对象：

| 字段 | 内容 |
| --- | --- |
| `claim_id` | 稳定标识，例如 `daily_watch20.alpha_persistence` |
| `statement` | 判断陈述 |
| `claim_type` | `hypothesis`、`fact`、`estimate`、`inference` |
| `supports` | 支撑该判断的证据引用，形如 `evidence://` |
| `contradicts` | 反驳该判断的证据引用 |
| `critical_assumptions` | 关键假设列表，每项含 `assumption_id` 与 `statement` |
| `invalidation_conditions` | 失效条件，每项含 `observable`、`threshold`、`horizon` |
| `abstain_conditions` | 因证据不足而拒绝判断的维度与原因 |
| `status` | `active`、`proposed`、`superseded`、`rejected` |
| `last_reviewed` | 最近评审日期 |

失效条件正式替代口语化的命门概念。引用路径必须存在，与 `research_spec.v1` 的
`evidence_refs` 非空要求保持一致。

schema 文件在 `strategy-research/schemas/claim.v1.schema.json`，校验脚本为
`scripts/decision_governance_check.py`，判断账本目录为 `strategy-research/judgment-ledger/`。

### DG2 研究案例与决策记录

在 `strategy-research/cases/<案例id>/` 增加 `research_case.v1`，补齐决策线索：

```text
strategy-research/cases/
    2026-08-<topic>/
        case.json
        decision.md
        reviews/
            logic.json
            evidence.json
```

`case.json` 只做导航，字段包括 `question`、`as_of`、`research_specs`、`claims`、
`evidence_bundles`、`reviews`、`known_gaps`、`abstentions` 与 `decision`。`decision` 状态
为 `no_view`、`provisional`、`accepted`、`rejected` 之一，并记录 `thesis`。

schema 文件在 `strategy-research/schemas/research_case.v1.schema.json`，校验脚本为
`scripts/decision_governance_check.py`，案例目录为 `strategy-research/cases/`。

决策线索的完整链条：

```text
研究问题
  ↓
research_spec
  ↓
实验、数据、回测
  ↓
证据包
  ↓
判断账本
  ↓
对抗评审
  ↓
决策记录
  ↓
策略生命周期
```

### DG3 定性来源溯源

为外部研究素材增加来源 schema，记录来源、事实属性与可验证性：

| 字段 | 内容 |
| --- | --- |
| `source_id` | 来源标识 |
| `source_type` | 来源类型 |
| `publisher` | 发布方 |
| `published_at`、`effective_at`、`observed_at`、`ingested_at` | 四个时间点 |
| `content_hash` | 内容哈希 |
| `claim_type` | `fact`、`estimate`、`guidance`、`opinion`、`inference`、`forecast` |
| `directness` | `primary`、`secondary`、`tertiary` |
| `verifiability` | `independently_verified`、`single_source`、`unverifiable` |
| `supports`、`contradicts` | 关联判断 |
| `entity_refs` | 关联实体 |

四个时间点分开记录，防止未来函数在人类阅读层被自然发明。不采用单一来源等级排序，
来源可信度拆成直接性、可验证性、独立性、时间有效性和事实与推演属性多个维度。

### DG4 缺数据即放弃判断

把放弃判断变成正式输出状态。报告生成器必须遵守：

```text
可用证据 -> 支持结论
缺失证据 -> no_view
```

`no_view` 与 `abstain` 作为一等状态写入决策记录，禁止在证据缺失时生成综合来看之类的
填补性结论。现有证据门禁的 `partial`、`pending`、`missing`、`known_gaps` 语义保留，
本项把它们延伸到判断层。

### DG5 逻辑与证据双评审

每个案例的评审拆成两个独立视角：

| 评审 | 只看 | 找什么 |
| --- | --- | --- |
| 逻辑评审 | 结论、判断、假设、证据引用 | 偷换概念、因果跳跃、相关性当因果、外推超出证据范围、样本选择、缺口被叙事补上 |
| 证据评审 | 证据是否真的支持判断 | 来源时间、PIT、统计口径、冲突证据、缺失证据、测量值被误称事实 |

两个评审各自输出机器可读文件，交集与分歧交由人类裁决。评审独立性至少来自不同评审
prompt、不共享对方输出、必要时不同输入切片与确定性检查，禁止用同一模型的相似输出
冒充独立证据。

### DG6 证据完备度卡片

引入概念时把两个指标拆开：

| 概念 | 定义 | 可否量化 |
| --- | --- | --- |
| `evidence_readiness` | 结论的证据完整程度 | 可量化 |
| `investment_conviction` | 判断成立的主观概率 | 难以可靠量化 |

不合成单一置信度总分，先按维度展示证据覆盖、来源可靠性、稳健性、未解决矛盾和时效性。
积累足够案例后再检验高置信度判断的命中率，之后才谈权重。

### DG7 产业链显式关系

为 `hotsector` 类研究维护实体关系层，放在外部 `market-intel`，`research-workspace` 只引用
稳定实体标识。不把关系图塞进 `research-workspace`，避免本仓同时承担数据平台、知识库与
产业链数据库的职责。

## 不建议采用

- 把项目目录改造成 raw、wiki、output、rules 四层结构，现有职责拆分已经更成熟
- 简单来源等级排序，官方公告一定高于路演纪要与网络媒体的假设不成立
- 多个同模型 Agent 互评互信，同模型共享盲点，不构成独立评审
- 合成单一置信度总分，容易制造伪精确性

## 与现有文档的关系

- `research-spec.md` 负责实验说明书格式，本页不重复
- `strategy-evidence-gate.md` 负责证据门禁，本页不改变强制证据集合
- `strategy-research/README.md` 负责策略身份与生命周期，判断账本只补充认识论身份
- 观察类工具只作查看层，不作为事实来源，事实来源仍是无障碍 JSON、YAML、Git 与哈希
