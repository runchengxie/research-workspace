# 从 research-workspace 撤回牛门线 Implementation Plan

> For agentic workers: use the executing-plans skill.

Goal: 移除 research-workspace 与 strategy-app 中重复的早期牛门线内容。

Architecture: 先删除 strategy-app 的 Niu Men 专属实现，再删除 workspace 策略登记并更新 gitlink。

Tech Stack: Python、pytest、Ruff、uv、Git submodule。

Spec: docs/superpowers/specs/2026-08-25-remove-niu-men-from-workspace-design.md

---
## Global Constraints

- main 是 integration-only，所有实现只发生在独立 feature worktree。
- 独立 niu-men-line-strategy 保留 research_snapshot.v2 和全部研究逻辑。
- 不删除 Git 历史，不回滚包含 DailyWatch20 及其他改动的整个 strategy-app gitlink。
- workspace 当前 catalog 不再登记 niu_men_line。

---

### Task 1: 删除 strategy-app 的早期牛门线应用

Files:

- Delete: strategy-app/src/strategy_app/niu_men_line/__init__.py
- Delete: strategy-app/src/strategy_app/niu_men_line/contracts.py
- Delete: strategy-app/src/strategy_app/niu_men_line/indicators.py
- Delete: strategy-app/src/strategy_app/niu_men_line/event_study.py
- Delete: strategy-app/tests/test_niu_men_line.py
- Modify: strategy-app/README.md
- Modify: strategy-app/docs/application-catalog.md
- Modify: strategy-app/docs/quality-gates.md
- Create: strategy-app/tests/test_withdrawn_niu_men_line.py

Interfaces:

- Consumes: 当前 strategy-app 的两策略应用目录和质量门禁。
- Produces: 不再发布 strategy_app.niu_men_line，并有测试锁定该表面不会重新出现。

- [ ] Step 1: Write the failing withdrawal test.

新增 tests/test_withdrawn_niu_men_line.py，断言 Niu Men 专属目录和测试文件不存在，并断言 README 与 application-catalog 不包含 niu_men_line。

- [ ] Step 2: Run the test to verify it fails.

Run: uv run --locked --extra dev python -m pytest tests/test_withdrawn_niu_men_line.py -q
Expected: FAIL because the current package, test file, README entry, and catalog entry still exist.

- [ ] Step 3: Delete the Niu Men package and update current documentation.

删除五个专属 Python/test 文件；将 README 的应用族数量从三个改为两个并删除 Niu Men 行；删除 application-catalog 的牛门线章节。保留 quality-gates 中的历史 baseline 事实，并追加撤回说明。

- [ ] Step 4: Run focused and regression tests.

Run: uv run --locked --extra dev python -m pytest tests/test_withdrawn_niu_men_line.py -q
Expected: PASS.
Run: uv run --locked --extra dev python -m pytest -q
Expected: PASS with no imports from remaining DailyWatch20 or hotsector modules broken.

### Task 2: 删除 research-workspace 的牛门线登记

Files:

- Delete: strategy-research/strategies/niu_men_line/README.md
- Delete: strategy-research/strategies/niu_men_line/hypothesis.md
- Delete: strategy-research/strategies/niu_men_line/strategy-spec.yml
- Delete: strategy-research/experiments/niu_men_line/README.md
- Modify: strategy-research/README.md
- Modify: strategy-research/catalog.json
- Modify: tests/test_strategy_research_catalog.py

Interfaces:

- Consumes: strategy catalog schema and human-readable strategy map。
- Produces: catalog set excludes niu_men_line; all remaining human specs remain navigable。

- [ ] Step 1: 修改 catalog 测试，移除 EXPECTED_STRATEGIES 中的 niu_men_line，并增加两个撤回目录不存在断言。
- [ ] Step 2: 运行测试确认在实现前失败。

Run: uv run --project strategy-pipeline --with matplotlib>=3.8 --with tabulate>=0.9 python -m pytest tests/test_strategy_research_catalog.py -q
Expected: FAIL because the catalog and directories still contain Niu Men。

- [ ] Step 3: 删除 catalog 条目、策略地图行和四个顶层说明文件。
- [ ] Step 4: 运行 catalog 与 documentation 测试并确认其他策略不变。

Run: uv run --project strategy-pipeline --with matplotlib>=3.8 --with tabulate>=0.9 python -m pytest tests/test_strategy_research_catalog.py tests/test_research_documentation.py -q
Expected: PASS。

### Task 3: 更新 workspace 的 strategy-app gitlink

- [ ] Step 1: 确认 strategy-app diff 只删除 Niu Men 专属文件和文档引用，未删除其他策略。
- [ ] Step 2: 在 workspace worktree 中 git add strategy-app，并检查 git diff --cached --submodule=log。
- [ ] Step 3: 运行 python scripts/workspace_doctor.py。
Expected: PASS without dirty submodule or missing owner errors。

### Task 4: Final verification and commits

- [ ] Step 1: 使用 rg 检查当前 workspace，不应有活跃 source、catalog、README 或测试引用；撤回 spec/plan 和明确历史记录可以保留。
- [ ] Step 2: 运行相关 workspace 测试。
- [ ] Step 3: 在 strategy-app worktree 提交 refactor: withdraw niu men from strategy app。
- [ ] Step 4: 在 research-workspace worktree 提交 refactor: remove niu men from research workspace。
