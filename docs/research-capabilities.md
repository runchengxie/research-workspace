# 研究能力目录

`docs/research-capabilities.yml` 是工作区当前研究能力的机器可读目录。它回答某项能力是否真的存在、由哪个仓库负责、canonical 入口在哪里、依赖哪些其他能力，以及当前验证成熟度。

## 边界

能力目录只保存元数据。数据、alpha、统计、组合、编排和执行实现继续归各 owner 仓库。目录不得复制算法，也不得因为 AFML、QuantSkills 或论文中存在某个方法，就把它登记成工作区已经实现的能力。

外部方法只出现在 `method_refs`，用于解释方法来源。运行时依赖只由 owner 仓库和既有跨仓契约决定。

Registry validator 位于 `src/research_contracts/`，因为它验证的是跨仓库能力契约。它不在顶层新增研究计算实现，也不进入 `scripts/` 生命周期清单。

## 条目字段

每个 capability 至少包含：

- `capability_id`：稳定的点分 ID
- `summary`：一句话说明
- `owner_repository`：canonical owner
- `stage`：工作流阶段
- `kind`：计算、验证、契约、编排或监控
- `maturity`：`experimental`、`runnable`、`verified` 或 `deprecated`
- `canonical_entrypoint`：公开入口及其 `source_path`
- `inputs`、`outputs`：稳定输入输出概念
- `requires`：其他 capability ID
- `method_refs`：AFML、论文或外部项目参考
- `evidence_refs`：owner 仓库内测试、契约或验证证据

## 成熟度

`experimental` 表示已有明确 owner 和可定位的研究入口或证据，但尚未形成稳定运行能力。

`runnable` 要求当前 pinned workspace 中能定位 canonical source，并有可运行示例或测试证据。

`verified` 在 runnable 基础上要求已有自动测试证据。这个等级说明工程和研究检查成熟度，不代表策略未来收益，也不等于生产资格。

`deprecated` 必须声明替代能力或废弃原因。

## 校验

```bash
python -m src.research_contracts.research_capability_registry
python -m src.research_contracts.research_capability_registry --json
```

Validator 会检查 ID、owner、路径越界、私有入口、依赖缺失、依赖环、source/evidence 是否存在，以及 verified 项是否真的有测试证据。

`python scripts/run_quality_checks.py --profile hard` 会运行这项校验，因此它属于现有本地 pre-push root-quality 门禁的一部分，不新增第二套 CI。

目录以当前 workspace 的 pinned 子模块为准。owner 主分支后来新增了能力，但顶层 gitlink 尚未更新时，该能力仍不能登记成当前工作区已经具备。

## Agent 使用

Agent 可以先读 registry 判断某个研究任务是否已有 canonical capability，再进入对应 owner。发现缺失能力时，应提出 owner 级实现或适配建议，不在顶层临时复制一套算法。

后续如果为 Agent 增加 Skill 接口，Skill 只能做薄适配并调用本目录登记的 canonical owner surface。Skill 不是第二套实现。
