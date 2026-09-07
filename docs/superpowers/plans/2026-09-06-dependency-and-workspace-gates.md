# 依赖和工作区门禁实施计划

目标：恢复工作区测试和治理门禁，并确保 Dependabot 更新只有在所有者仓库检查通过后才能合并。

架构：保持公开顶层仓库与私有 submodule 运行时包相互独立。修复根仓库中过期的文档和生成式治理证据，使 submodule gitlink 与已提交清单一致，并将磁盘容量视为环境前置条件。Dependabot 更新按所有者仓库分别评估，不批量合并。

技术栈：Python、`uv`、`pytest`、Git submodule、GitHub Actions、GitHub CLI。

依据：2026-09-06 记录的当前工作区测试失败项和未关闭 Dependabot PR 清单。

## 全局约束

- 不得提交凭证，也不得把私有包依赖加入公开 CI。
- 必需检查失败时，不得合并 Dependabot PR。
- 每个仓库只保留一个本地 `main` 分支，只删除已经合并或明确被 superseded 的分支。
- 工作区集成测试使用 `python scripts/run_workspace_tests.py`。
- 生产晋级与依赖 PR 合并分开处理。

### 任务 1：复现并分类当前门禁

文件：无。

- [ ] 运行 `python scripts/run_workspace_tests.py`，记录每项失败。
- [ ] 运行 `python scripts/workspace_doctor.py` 和 `python src/research_contracts/smoke_contracts.py`。
- [ ] 将已提交的 submodule 清单与实际 gitlink 比较。
- [ ] 记录失败属于代码、生成元数据还是环境容量问题。

### 任务 2：修复根目录文档和生成的基线

文件：
- 修改：`tests/test_documentation_entrypoints.py` 报告的文档文件。
- 修改：基线测试报告的已提交可维护性基线。
- 测试：`tests/test_documentation_entrypoints.py`、`tests/test_maintainability_governance.py`。

- [ ] 只有在预期契约缺失时，才增加或更新针对性断言。
- [ ] 删除禁止的标点和风格片段，同时保留原文含义。
- [ ] 使用仓库生成器重新生成可维护性基线。
- [ ] 运行两个针对性测试和工作区测试运行器。

### 任务 3：对齐 submodule 清单和 gitlink

文件：
- 修改：失败契约指出的根 submodule 清单或 gitlink 元数据。
- 测试：`tests/test_namespace_contracts.py` 和相关工作区 doctor 检查。

- [ ] 找出所有不匹配的所有者提交。
- [ ] 确认每个目标提交存在于所有者仓库的 main 分支。
- [ ] 使用仓库的标准同步流程更新清单或根 gitlink。
- [ ] 运行命名空间和 submodule 一致性检查。

### 任务 4：解决维护测试的环境容量问题

文件：只有现有测试无法使用有足够空间的有效临时目录时才修改。

- [ ] 检查 `/tmp` 和配置的临时根目录的可用空间。
- [ ] 优先使用更大的临时目录运行测试。
- [ ] 只有在阈值错误地硬编码为不适用于支持环境的值时，才修改测试或阈值。
- [ ] 重新运行 `tests/test_production_maintenance.py`。

### 任务 5：按仓库处理 Dependabot PR

文件：只有失败检查可以复现为代码或配置原因时，才修改所有者仓库分支和 workflow 文件。

- [ ] 审查 `research-workspace`、`alpha-research`、`portfolio-backtester` 和公开 `strategy-pipeline` 中未关闭的 Dependabot PR。
- [ ] 只合并必需检查通过且依赖变更兼容的 PR。
- [ ] CodeQL 或契约检查失败时，先检查失败原因，再决定是否修改代码。
- [ ] 修复后重新运行检查，合并成功的 PR，并删除已合并分支。

### 任务 6：最终同步和晋级审计

文件：所有者仓库合并后只有根 gitlink 发生变化时才修改，否则无文件改动。

- [ ] 拉取并清理所有相关远端。
- [ ] 确认根仓库和每个 submodule 没有未提交文件、过期本地功能分支或意外遗留的可合并 PR。
- [ ] 为所有者仓库已经合并的改动更新根 gitlink。
- [ ] 再次运行工作区检查。
- [ ] 只有 main 与发布清单一致后，才晋级生产。
