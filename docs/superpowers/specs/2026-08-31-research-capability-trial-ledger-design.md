# Research Capability Registry 与 Trial Ledger 设计

## 目标

在现有 `research-workspace` 架构内补齐两个研究治理能力：

1. 用机器可读的 capability registry 回答工作区当前真实具备哪些研究、验证、组合和执行能力，以及这些能力的 canonical owner、入口、依赖和成熟度。
2. 用 trial ledger 记录一个研究结论形成之前实际尝试过哪些候选、失败和变体，让多重检验、PBO、DSR 和最终样本外判断能够追溯到完整试验历史。

这两个对象只负责描述、治理和验证，不复制 owner 仓库中的数据、alpha、组合或执行实现。

## 背景

工作区已经具备清晰的 owner 边界、`research_spec.v1`、策略证据门禁、判断账本、反例、结果目标和显式生命周期。当前仍有两个空档：

- 能力分散在多个 owner 仓库里，人和 Agent 很难快速确认某项研究方法是否已经存在、入口在哪里、成熟到什么程度。
- `research_spec.v1` 能说明一次实验做了什么，但无法完整回答得到最终结果之前一共试过多少候选，哪些失败、哪些被淘汰、哪些应计入多重检验分母。

QuantSkills 在能力目录、依赖和验证等级方面提供了有用设计参考。AFML 继续作为金融机器学习方法来源。工作区现有 owner API、契约和证据仍是唯一事实来源。

## 方案选择

### 方案 A：元数据 registry + 试验 ledger，推荐

- 顶层维护 capability registry。
- `strategy-research` 维护 trial ledger。
- registry 只指向 canonical owner 实现或契约。
- ledger 只保存紧凑试验事实、标量指标和证据引用。
- 新对象均提供机器检查和测试。

优点是符合当前 owner architecture，不形成第二套研究框架，也能给 Agent 提供稳定发现入口。

### 方案 B：为每个能力增加一套 QuantSkills 风格 Skill 实现

优点是 Agent 发现体验直接。缺点是容易复制 owner 业务逻辑，产生接口和算法漂移。当前不采用。后续如需要 Agent Skill，只允许做薄适配层并调用 registry 中登记的 canonical entrypoint。

### 方案 C：在顶层建立统一研究框架包

优点是接口看起来整齐。缺点是会把数据、alpha、组合和执行逻辑重新吸回顶层，直接破坏 ADR-0006 的职责边界。明确不采用。

## 架构

```text
                           research-workspace
                    research_capability_registry.v1
                     /        |        |        \
                    /         |        |         \
        market-data     alpha-research  portfolio   execution
        canonical API   canonical API   canonical   canonical
              ^               ^             ^           ^
              |               |             |           |
              +---------------+-------------+-----------+
                              |
                     capability metadata only

strategy-research
  research_spec.v1
        |
        +---- trial-ledger/<experiment_id>.jsonl
        |          |
        |          +-- every evaluated candidate / invalid run / mutation
        |          +-- multiple-testing accounting
        |          +-- evidence references
        |
        +---- evidence / claims / counterexamples / decisions
```

## 1. Research Capability Registry

### 1.1 Owner 与文件位置

Registry 由 `research-workspace` 顶层维护，因为它描述跨仓库能力和 owner 关系。

计划新增：

```text
docs/research-capabilities.yml
scripts/research_capability_registry_check.py
tests/test_research_capability_registry.py
docs/research-capabilities.md
```

`docs/research-capabilities.yml` 是机器事实源。Markdown 只解释契约和使用方法，不手工复制完整清单。

### 1.2 Entry schema

以下 YAML 只说明 schema 形状，不声明示例中的 Python 路径当前已经存在：

```yaml
capability_id: alpha.purged_cross_validation
summary: 金融事件标签下的 purged/embargo 交叉验证
owner_repository: alpha-research
stage: validation
kind: computation
maturity: verified
canonical_entrypoint:
  type: python
  value: alpha_research.validation.purged_cv
inputs:
  - canonical_event_table
  - features
  - labels
outputs:
  - cv_report
requires:
  - data.pit_dataset
method_refs:
  - type: afml
    ref: chapter-7-cross-validation-in-finance
evidence_refs:
  - alpha-research/tests/test_validation.py
```

字段语义：

- `capability_id`：稳定、全局唯一、点分命名。
- `summary`：一句话能力说明。
- `owner_repository`：canonical 实现所属仓库。
- `stage`：取 `data-ingestion`、`data-quality`、`feature-engineering`、`labeling`、`modeling`、`validation`、`portfolio-construction`、`backtesting`、`risk`、`orchestration`、`execution`、`governance` 之一。
- `kind`：`computation`、`validation`、`contract`、`orchestration`、`monitoring` 之一。
- `maturity`：`experimental`、`runnable`、`verified`、`deprecated`。
- `canonical_entrypoint`：公开 Python API、CLI、脚本或文件契约。不得指向私有符号。
- `inputs`、`outputs`：稳定输入输出名，只描述契约，不复制 schema。
- `requires`：其他 capability ID，形成可检查依赖图。
- `method_refs`：AFML、论文、QuantSkills 等方法来源，只作参考，不构成运行依赖。
- `evidence_refs`：测试、契约、验证文档或真实证据路径。

### 1.3 Maturity 规则

`experimental`

- 可以只有文档或试验入口。
- 必须有 owner 和至少一条 evidence/reference 路径。

`runnable`

- 必须有 canonical entrypoint。
- 入口对应路径或模块必须能在当前版本组合中定位。
- 必须有至少一条测试或可运行示例证据。

`verified`

- 满足 `runnable`。
- 至少包含自动测试证据。
- 对会产生金融研究结论的能力，必须有时间点、泄漏、成本、样本外或适用边界中的相关验证证据。具体要求按 capability kind 判断，不强行套同一清单。

`deprecated`

- 必须给出替代 capability 或废弃说明。

Registry 的成熟度描述能力实现的工程和研究验证程度，不代表策略收益或未来有效性。

### 1.4 Validator

`research_capability_registry_check.py` 至少检查：

- YAML 可解析，顶层 schema 版本正确。
- `capability_id` 唯一且格式合法。
- owner 只能来自当前 workspace owner 集合，包括顶层治理 owner 和已登记子仓库。
- `stage`、`kind`、`maturity` 只能使用固定枚举。
- `requires` 引用存在且依赖图无环。
- canonical entrypoint 不得使用明显私有模块或私有符号。
- path/script/contract 类型入口必须存在。
- `runnable` 和 `verified` 满足对应证据要求。
- evidence path 必须存在于当前工作区或已初始化子模块。
- 不把 QuantSkills、AFML 或论文中的能力直接登记成 workspace 已实现能力。

提供 `--json` 输出，便于 Agent 和其他检查脚本消费。

### 1.5 初始 registry 种子

首个实现 PR 只登记当前代码或契约可以验证存在的能力。候选盘点范围包括：

- PIT 数据发布与 provenance。
- triple barrier / event window。
- meta-labeling。
- uniqueness weighting / sequential bootstrap。
- purged / embargo / CPCV。
- OOS calibration。
- PSR / PBO / strategy failure probability。
- HRP / calibrated sizing。
- cost / turnover / capacity。
- research spec / evidence gate / decision governance。
- targets handoff / execution preflight / audit。

以上只是盘点候选。每条在合入前都必须从对应 owner 仓库找到真实入口和证据，找不到的候选不进入 registry。

## 2. Trial Ledger

### 2.1 Owner 与文件位置

Trial ledger 属于研究历史和证据导航，由 `strategy-research` 维护。

计划新增：

```text
schemas/trial_ledger_entry.v1.schema.json
trial-ledger/README.md
trial-ledger/<experiment_id>.jsonl
scripts/trial_ledger_check.py
tests/test_trial_ledger.py
docs/trial-ledger.md
```

大规模收益序列、模型文件、行情和回测产物继续存放在仓库外。Ledger 只保存可版本控制的紧凑元数据和 evidence references。

### 2.2 Entry schema

每行 JSON 对应一个实际研究 trial。`evaluation_windows` 只登记本 trial 实际执行过评价的窗口。冻结但尚未运行的 final OOS 只存在于 `research_spec.v1`，不会提前复制进每个 candidate trial。

```json
{
  "schema_version": "trial_ledger_entry.v1",
  "trial_id": "factor-search-20260831-001",
  "experiment_id": "factor-search-20260831",
  "parent_trial_id": null,
  "duplicate_of_trial_id": null,
  "trial_kind": "candidate",
  "hypothesis_refs": ["claim://example.alpha_persistence"],
  "state": "completed",
  "decision": "reject",
  "created_at": "2026-08-31T09:00:00+08:00",
  "completed_at": "2026-08-31T09:03:00+08:00",
  "code_revision": "0123456789abcdef0123456789abcdef01234567",
  "data_revision": "a_share_current@20260830",
  "search_family": "volume-price-v1",
  "multiple_testing": {
    "family_id": "volume-price-v1",
    "counted": true,
    "exclusion_reason": null
  },
  "evaluation_windows": [
    {
      "name": "train",
      "role": "train",
      "start": "2018-01-01",
      "end": "2022-12-31",
      "used_for_selection": true
    },
    {
      "name": "validation",
      "role": "validation",
      "start": "2023-01-01",
      "end": "2024-12-31",
      "used_for_selection": true
    }
  ],
  "candidate": {
    "formula": "rank(close / ref(close, 5) - 1)",
    "model": null,
    "features": [],
    "parameters": {"lookback": 5}
  },
  "metrics": {
    "rank_ic": 0.012,
    "sharpe": 0.4
  },
  "evidence_refs": ["evidence://factor-search-20260831/trial-001"],
  "failure_reason": null
}
```

### 2.3 状态与决策

`trial_kind`：

- `baseline`
- `candidate`
- `mutation`
- `ablation`
- `negative_control`
- `diagnostic`

`state`：

- `proposed`
- `running`
- `completed`
- `failed`
- `invalid`

`decision`：

- `keep`
- `reject`
- `mutate`
- `duplicate`
- `invalid`
- `no_decision`

表现差的候选仍然是一次有效评价，应写成 `state=completed`、`decision=reject` 并保留。`failed` 和 `invalid` 用于没有产生有效统计评价的技术失败或无效运行，必须记录 `failure_reason`。

### 2.4 Multiple-testing 规则

每条 trial 都必须显式写出 `multiple_testing.counted`，不依赖隐式默认值。

如果 `counted=false`，必须提供受限 `exclusion_reason`：

- `invalid_execution`
- `exact_duplicate`
- `non_statistical_diagnostic`

约束：

- `state=completed` 且属于 baseline、candidate、mutation、ablation、negative_control 的统计评价，原则上 `counted=true`。
- `invalid_execution` 只适用于没有产生有效统计评价的 `failed` 或 `invalid` trial。
- `exact_duplicate` 必须填写 `duplicate_of_trial_id`，并由 validator 验证 candidate fingerprint 一致。
- `non_statistical_diagnostic` 只适用于 `trial_kind=diagnostic`。
- 不允许使用 `bad_result`、`failed_to_improve` 或人工自由文本作为排除原因。

这样失败的研究结论不会被静默删除，技术上根本没有完成统计检验的无效运行也不会机械膨胀多重检验分母。

### 2.5 Final OOS 保护

Validator 强制：

- `role=final_oos` 时 `used_for_selection` 必须为 `false`。
- 同一个 experiment 中，实际执行过的 final OOS 日期定义必须与 `research_spec.v1` 的冻结定义一致。
- 同一 experiment 不得出现两个不同的 final OOS 窗口。
- trial 一旦实际评价 `final_oos`，该 trial 的 decision 不能是 `mutate`。
- 已评价 final OOS 的 trial 不能成为同一 experiment 后续 mutation 的 parent。
- 如需根据 final OOS 结果重新设计，必须新建 experiment ID，并把旧结果视为先验研究证据，不能继续声称新的窗口是同一份冻结 OOS。

这些规则只防止机器可见的直接污染，不能证明研究者没有在其他地方偷看 final OOS，因此最终证据仍需现有 evidence gate 和人工评审。

### 2.6 Parent / mutation 关系

- `mutation` 必须有 `parent_trial_id`。
- parent 必须存在于同一 experiment ledger。
- parent 不得指向自己。
- parent 图必须无环。
- `exact_duplicate` 必须有 `duplicate_of_trial_id`。
- duplicate target 必须存在于同一 experiment ledger。
- duplicate target 不得指向自己。

Validator 为 candidate 建立稳定 fingerprint，至少覆盖公式或模型身份、参数、universe/horizon、实际评价窗口、成本和数据版本。Fingerprint 只用于发现重复，不代替 trial ID。

## 3. 与 ResearchSpec、Evidence Gate 的连接

### 3.1 ResearchSpec

`research_spec.v1` 增加可选字段：

```json
"trial_ledger": {
  "path": "trial-ledger/factor-search-20260831.jsonl",
  "multiple_testing_family": "volume-price-v1"
}
```

兼容旧 spec，不要求历史实验一次性回填。

如果声明了 `trial_ledger`：

- path 必须存在。
- ledger 中 `experiment_id` 必须与 spec 一致。
- `multiple_testing_family` 必须至少对应一条 counted trial。
- spec 中冻结的 final OOS 与 ledger 中实际执行的 final OOS 必须一致。

自动候选搜索、网格搜索、遗传搜索和 Agent 批量生成的新实验应当登记 ledger。探索性单次诊断可以不登记。

### 3.2 Evidence Gate

首期不新增新的生命周期硬门槛，避免把所有历史策略瞬间变成迁移项目。

已有 `multiple_testing_adjustment`、PBO 等证据可以引用 trial ledger 作为试验次数和候选集合来源。后续只有在真实策略完成迁移并证明门禁稳定后，才考虑把 `trial_accounting` 独立提升为 `operational` 强制项。

## 4. Agent 使用方式

Agent 在准备复用研究能力时：

1. 先查 capability registry。
2. 找到 canonical owner 和 entrypoint。
3. 读取 capability 的 evidence、requires 和 maturity。
4. 不在顶层重写已有能力。
5. 找不到 capability 时先确认 owner 仓是否已有未登记实现，再决定新增 capability 或新实现。

Agent 在批量搜索策略或因子时：

1. 在执行第一批候选前固定 experiment ID 和 multiple-testing family。
2. 每个候选先登记 trial identity 和 fingerprint 所需字段。
3. 执行后写回状态、指标和 evidence refs。
4. 有效但表现差的候选写成 completed/reject 并保留。
5. final OOS 只用于最终验证，不用于 mutation 或筛选。

当前设计不新增独立 `skills/` 目录。未来如需要 Claude Code / Codex Skill，只允许生成调用 registry canonical entrypoint 的薄加载器。

## 5. 门禁与测试

### strategy-research PR

至少包含：

- schema 正反例测试。
- JSONL 解析和坏行定位测试。
- ID 唯一性测试。
- parent DAG 测试。
- duplicate fingerprint 测试。
- multiple-testing 排除原因测试。
- final OOS 禁止 selection / mutation 测试。
- evidence ref 与 experiment ID 一致性测试。

本仓标准测试：

```bash
uv run --project strategy-research --extra dev python -m pytest tests -q
```

### research-workspace PR

至少包含：

- capability ID 唯一性测试。
- owner 枚举和 canonical path 测试。
- requires DAG 测试。
- maturity gate 测试。
- evidence refs 存在性测试。
- `research_spec.v1` optional trial ledger 兼容性测试。
- 子模块版本和 registry owner 事实测试。

并运行：

```bash
python scripts/research_capability_registry_check.py
python scripts/research_spec_check.py
python scripts/decision_governance_check.py
python scripts/run_quality_checks.py --profile hard
python scripts/run_submodule_checks.py --profile smoke
```

顶层继续通过现有 pre-push 体系调用检查，不建立第二套 CI。

## 6. PR 与合并顺序

按 owner-first 原则拆成三个 PR：

1. `research-workspace` 设计 PR：只提交本设计，作为实现审查基线。
2. `strategy-research` 实施 PR：落地 `trial_ledger.v1`、validator、测试、文档。
3. `research-workspace` 实施 PR：更新 `strategy-research` gitlink，落地 capability registry、validator、测试、ResearchSpec 接线和文档入口。

如实现过程中发现某个 capability 没有公开 owner API，只把它标为 `experimental` 或暂不登记。需要修改 owner 代码时另开独立 owner PR，合并后再更新 registry，不在顶层 PR 中偷渡实现。

## 7. 非目标

本次不做：

- 不导入 QuantSkills 的社区资产。
- 不复制 AFML 或 QuantSkills 的算法实现。
- 不建立统一 `research_framework` 包。
- 不自动生成交易信号或改变任何策略生产资格。
- 不把 capability maturity 当成 alpha 有效性评分。
- 不把历史回测重新标记为新的 OOS。
- 不要求一次性回填所有历史 trial。

## 8. 验收标准

设计完成后的系统应能机器回答：

1. 这项能力是否已经存在，canonical owner 和入口是什么，成熟度和证据在哪里。
2. 某个批量研究结果之前一共尝试过哪些 trial，哪些计入多重检验，排除理由是什么。
3. 某个 final OOS 是否被显式用于 selection 或 mutation。
4. 一个 trial 的 parent、参数、数据版本、代码版本和证据能否追溯。
5. registry 和 ledger 的错误是否会被本地质量门禁可靠阻断。

成功标准是提升研究可追溯性和防自欺能力，不增加新的业务实现 owner，也不改变现有策略输出。