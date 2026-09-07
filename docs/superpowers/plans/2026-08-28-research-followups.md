# 研究后续工作实施计划

> 面向智能体执行者：每个仓库改动都使用独立 worktree 和单独 PR。在证明规范路径一致前，执行证据只用于比较。

目标：完成三层 owner 迁移后的安全后续工作，同时保持研究、组合和执行边界。

架构：合并前先评审会影响执行的工作，使仓库测试不依赖检出路径，将可复用哈希逻辑放在明确的 owner 中。增加模拟行为与执行台账行为之间的语义一致性 fixture，同时将 E2 晋升证据作为独立的数据驱动活动。

技术栈：Python、pytest、Ruff、ty、uv、Git worktree 和 GitHub PR。

规格：`docs/adr/0007-style-replica-ownership.md` 和 `docs/roadmap.md`。

## 全局约束

- `alpha-research` 负责信号研究和诊断。
- `portfolio-backtester` 负责组合构造和模拟经济结果。
- `quant-execution-engine` 负责真实订单生命周期、券商行为和对账。
- `strategy-pipeline` 继续只负责编排。
- 每个仓库改动都使用独立 worktree 和 PR。
- 没有可复现输入、输出和血缘凭证时，不得晋升 E2 结果。

### 任务 1：评审未关闭的执行 PR

- [ ] Inspect PR #224 and PR #225 file-by-file.
- [ ] Verify that owner-ledger output remains comparison-only.
- [ ] Verify dependency pins and tests use merged revisions.
- [ ] Record concrete blockers or approve only after local reproduction.

### 任务 2：让测试不依赖 worktree 路径

- [ ] Replace hard-coded repository path assertions with repository-root discovery or package metadata.
- [ ] Add regression tests that run from a non-canonical worktree path.
- [ ] Run each affected repository's full local gate.

### 任务 3：审计重复哈希辅助函数

- [ ] Inventory all `file_sha256` and `sha256_file` definitions.
- [ ] Classify identical helpers versus intentionally local wrappers.
- [ ] Move only safe shared behavior to the existing contracts owner.
- [ ] Update ownership budgets and tests.

### 任务 4：增加执行语义一致性 fixture

- [ ] Cover lot-size rounding, T+1, suspended/limit securities, partial fills, fees, and slippage.
- [ ] Compare normalized semantics, not internal runtime types.
- [ ] Keep the owner ledger explicitly non-canonical until equivalence is demonstrated.

### 任务 5：准备 E2 证据活动

- [ ] Freeze candidate, universe, date range, data revisions, execution rules, and cost model.
- [ ] Produce test, final OOS, CPCV, capacity, and lineage receipts.
- [ ] Add a reproducible promotion checklist and abstain when evidence is incomplete.
