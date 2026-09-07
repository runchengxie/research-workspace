# strategy-pipeline-internal 迁移收尾实施计划

> 面向智能体执行者：必须使用 `superpowers:executing-plans`，按任务逐项执行本计划。

目标：协调迁移清单、文档归属证据和生产就绪记录，使仓库只陈述当前工作区能够验证的事实。

架构：将冻结的内部仓库作为归档和恢复来源，将 owner 仓库和公开 `strategy-pipeline` 作为当前实现面。关闭仓库内元数据不一致，保留历史证据，在获得单独授权的晋升前保持生产指针不变。

技术栈：Markdown、JSON、Python/pytest、Git worktree 和现有工作区发布脚本。

规格：`docs/migrations/strategy-pipeline-internal-retirement-record.md` 和 `docs/evidence/strategy-pipeline-internal-retirement-final-20260905.json`。

## 全局约束

- 不要将私有策略实现复制到公开 `strategy-pipeline`。
- 保留冻结的内部标签和历史源提交，作为恢复引用。
- 没有明确的生产晋升决定，不要修改 `/home/richard/code/production/research-workspace/current`。
- 每项状态声明都必须由最新命令或已提交的证据文件支持。

---

### 任务 1：关闭工作区迁移清单

文件：
- Modify: `docs/migrations/strategy-pipeline-internal-migration-manifest.md`
- Test: `tests/test_strategy_pipeline_internal_migration_manifest.py`

- [x] 将清单头部从 `status: active` 改为 `status: retired`。
- [x] 在保留冻结源归属分类的同时增加独立收尾计数。
- [x] 删除 `docs/metric-ownership.md` 和 `docs/strategy-catalog.md` 中过时的两处 `migration_pr: pending`。
- [x] 增加说明，标记源仓库归属清单为冻结的历史证据。
- [x] 运行针对性的迁移清单测试并确认通过。

### 任务 2：澄清当前文档状态

文件：
- Modify: `docs/strategy-catalog.md`
- Modify: `docs/migrations/strategy-pipeline-internal-retirement-record.md`
- Modify: `docs/evidence/strategy-pipeline-internal-retirement-final-20260905.json`
- Test: `tests/test_strategy_pipeline_internal_retirement_record.py`

- [x] 替换声称迁移仍在进行的表述，区分当前迁移完成和仅归档保留。
- [x] 将本地观测到的生产指针与历史声称的发布版本分开记录，并将不一致标记为晋升后续事项。
- [x] 增加机器可读字段，记录观测到的本地生产工作区版本和发布匹配状态。
- [x] 运行针对性的退役记录测试并确认通过。

### 任务 3：验证所有当前实现面和发布就绪状态

**Files:**
- No source changes expected.

- [x] 运行工作区迁移和退役针对性测试：45 个通过。
- [x] 运行公开 `strategy-pipeline` 测试：55 个通过。
- [x] 重新运行 owner 目标存在性检查：113 个代码迁移和 16 个文档目标，缺失数为 0。
- [x] 运行生产晋升 dry-run，并确认实际的当前指针。
- [x] 确认没有当前导入或运行时路径引用 `strategy_pipeline_internal`。

### 任务 4：评审并交接生产晋升

**Files:**
- No automatic production symlink change.

- [x] 检查最终差异，确认没有修改生产目录。
- [x] 报告准确的晋升命令和当前或目标发布身份。
- [ ] 在获得明确晋升批准并协调生产指针前，保持目标开放。
