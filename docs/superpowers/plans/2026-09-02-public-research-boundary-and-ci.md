# 公开研究边界和 CI 策略实施计划

> 面向智能体执行者：必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项执行本计划。步骤使用复选框（`- [ ]`）跟踪。

目标：统一公开和私有仓库策略，为 `alpha-research` 和 `strategy-research` 的公开部分准备独立 GitHub Actions 检查，并将生产数据操作和私有策略资产留在公开仓库之外。

架构：保持 `market-data-platform` 和 `strategy-pipeline` 为私有仓库。移除 `alpha-research` 公开测试路径对私有数据平台安装的强制要求，使其具备公开条件。`strategy-research` 保留可复用研究基础设施，只有在完成明确的文件清单和消费者审计后，才将个人策略资产移动到独立私有仓库。公开 CI 必须不依赖私有凭证和真实数据。

技术栈：GitHub 仓库可见性、Git 子模块、Python、`uv`、pytest、Ruff、`ty`、Markdown 和 GitHub Actions。

规格：`docs/quality-governance.md`、各仓库的 `AGENTS.md`，以及本次审计记录的文件级分类。

## 全局约束

- 公开仓库默认启用 GitHub Actions。
- 私有仓库默认关闭 GitHub Actions。
- 私有仓库例外必须记录原因、范围和资源成本。
- 公开 CI 不得要求私有仓库凭证、真实数据资产或生产路径。
- 不要移动或删除 `strategy-research/research/experiments/long_term_fundamental_v2/run_quarterly_research.py` 中并行存在的未提交改动。
- 公开就绪检查通过前，不要修改仓库可见性。

### 任务 1：使仓库文档与 CI 策略一致

文件：
- Modify: root `AGENTS.md`, `README.md`, and `docs/quality-governance.md`
- Modify: each repository `AGENTS.md`, README, or quality/testing document where the policy is missing
- Test: existing documentation and policy tests in each repository

- [ ] 将同一套三条规则加入每个当前仓库的维护文档。
- [ ] 分别记录当前可见性和当前工作流状态。
- [ ] 替换声称所有 Actions 都已关闭的过时根文档表述。
- [ ] 增加仓库可见性矩阵，记录五个私有仓库及其保持私有的原因。
- [ ] 运行每个仓库的文档和策略测试。
- [ ] 将策略文档与代码改动分开提交。

### 任务 2：确定 `alpha-research` 的公开边界

文件：
- Modify: `alpha-research/pyproject.toml`, dependency source configuration, and CI/test entrypoints
- Test: `alpha-research/tests` and public-install smoke test

- [ ] 识别运行时需要 `market-data-platform` 的导入。
- [ ] 将供应商专属功能放到可选依赖或窄适配器边界之后。
- [ ] 确保默认公开测试和 lint 配置无需私有仓库即可安装。
- [ ] 保持 fixture 测试确定性且离线运行。
- [ ] 启用公开 CI 前解决现有 `ty` 诊断，或明确限定其范围。
- [ ] 在公开风格的干净环境中运行锁定安装、Ruff、格式检查、`ty`、pytest 和依赖审计。

### 任务 3：冻结 `strategy-research` 的公开和私有文件清单

**Files:**
- Create: a file-level public/private manifest in the private research boundary documentation
- Review: `research/experiments/**`, `research/cases/**`, `research/evidence/**`, `research/ledgers/**`, `src/**`, `tests/**`, `tools/**`, and `docs/**`
- Test: path and import-boundary tests

- [ ] 将可复用框架代码、模式、测试和脱敏规格标记为公开。
- [ ] 将个人策略逻辑、判断、证据、结果和接近生产的脚本标记为私有候选。
- [ ] 搜索公开候选文件中的凭证、绝对本地路径、真实数据标识和私有依赖固定版本。
- [ ] 移动文件前审计消费者。
- [ ] 只有私有清单包含稳定且有实际规模的资产集时，才创建 `strategy-research-private`。
- [ ] 保持公开代码不依赖私有仓库。

### 任务 4：清理公开 CI 和路径依赖

**Files:**
- Modify: public repository workflow files
- Modify: public-facing package dependency declarations and path defaults
- Test: CI workflow syntax, clean checkout install, and offline test suite

- [ ] 公开仓库的干净检出测试通过后，才启用轻量 PR CI。
- [ ] 私有仓库保持没有工作流，除非记录了例外原因。
- [ ] 使用环境变量或相对于 fixture 的默认值替换个人绝对路径。
- [ ] 确保 fork PR 的工作流不访问私有仓库或密钥。

### 任务 5：修改可见性并验证远端行为

**Files:**
- Repository settings for `alpha-research` and, if Task 3 passes, `strategy-research`
- Modify: root submodule pins and CI policy matrix

- [ ] 所有公开就绪检查通过后，才修改仓库可见性。
- [ ] 确认公开 Actions 工作流在默认分支成功运行。
- [ ] 确认根仓库子模块固定版本可以从公开仓库解析。
- [ ] 运行顶层工作区契约检查，并记录剩余的无关失败。
- [ ] 更新最终可见性矩阵，并记录任何延期处理的仓库。
