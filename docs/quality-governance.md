# 工作区质量治理

顶层仓库维护跨仓库质量入口。各子仓库继续负责自己的 Ruff、格式、类型检查、pytest、覆盖率和维护性配置。

## 检查分类

| 仓库 | 基础检查 | 补充诊断 | 人工复核 |
| --- | --- | --- | --- |
| 顶层工作区 | Ruff、格式、`ty`、依赖审计、密钥扫描、pytest、doctor、契约冒烟、研究能力目录与 Trial Ledger 校验 | dead-code 报告 | 私有子模块权限、版本组合和发布清单 |
| `market-data-platform` | Ruff、格式、`ty`、pytest、维护性和架构治理 | 依赖审计、覆盖率 | 数据权限、数据质量和当前契约发布 |
| `deep-learning-tick-data-prediction` | Ruff、格式、`ty`、pytest、覆盖率和研究协议检查 | 训练环境与依赖安全复核 | 真实数据、训练结果和研究口径 |
| `alpha-research` | Ruff、格式、`ty`、pytest、导入冒烟和维护性检查 | 依赖审计、研究证据定点测试 | signal artifact 和候选晋升证据 |
| `portfolio-backtester` | Ruff、格式、`ty`、pytest、导入冒烟和维护性检查 | 依赖审计、回测定点测试 | 成本、换手、容量和报告口径 |
| `strategy-research` | Ruff、格式、`ty`、pytest 和研究层检查 | 覆盖率 | 策略身份、生命周期和证据完整性 |
| `strategy-app` | lockfile、Ruff、格式、`ty`、pytest、维护性棘轮和隔离构建 | 依赖审计 | 冻结合同和研究应用结果 |
| `strategy-pipeline` | 仓库脚本中的 lint、format、`ty`、pytest 和边界检查 | 依赖审计 | 长窗口研究、编排和目标文件导出 |
| `quant-execution-engine` | Ruff、格式、`ty`、快速 pytest 和维护性检查 | 集成、端到端测试和依赖审计 | 券商凭证、模拟盘、实盘和对账 |

## 顶层命令

```bash
python scripts/run_quality_checks.py --profile hard
python scripts/run_quality_checks.py --profile ci-smoke
python scripts/run_quality_checks.py --profile dependencies
python scripts/run_quality_checks.py --profile architecture
python scripts/run_quality_checks.py --profile governance
python scripts/run_quality_checks.py --profile secrets
python scripts/run_quality_checks.py --profile dead-code
python scripts/run_submodule_checks.py --profile release_typecheck --dry-run
```

`hard` 包含 Ruff、格式、`ty`、工作区导入边界、研究治理和密钥扫描。它用于本地完整门禁，不依赖网络执行依赖审计。

`ci-smoke` 用于缺少私有子模块的公开环境，运行 Ruff、格式、`ty`、根项目 `pip-audit` 和密钥扫描。根仓 GitHub Actions 使用这个 profile，因此 public PR 会检查根仓自己的已知依赖漏洞。

`dependencies` 只运行根项目依赖审计，适合单独复核依赖变化。

`governance` 当前运行两项检查：

- `research_capability_registry.v1`：确认 capability 指向当前锁定工作区中真实存在的归属源码和验证证据，并检查依赖图与成熟度声明。
- `strategy-research/tools/scripts/trial_ledger_check.py`：校验 Trial Ledger 的 JSONL 契约、多重检验排除、重复项、父子关系和最终样本外规则。

顶层类型检查只覆盖 `pyproject.toml` 登记的工作区自有模块和脚本。新增质量门禁模块时，应同步判断是否加入 `ty` 范围。后续计划把当前手工文件列表收敛为目录范围，减少新文件漏检。

## GitHub Actions 策略

工作区采用统一的远端 CI 默认规则：

- public 仓库默认启用 GitHub Actions。远端 CI 主要提供拉取请求的快速反馈。
- private 仓库默认关闭 GitHub Actions，避免持续占用私有仓库的 Actions 额度。
- private 仓库需要远端 CI 时，应在仓库文档中记录原因、检查范围和资源成本，并由维护者明确批准。
- 本地 `pre-push` 和发布流程负责完整质量门禁。
- public 仓库的 workflow 应尽量调用仓库自己的权威检查入口，减少本地与远端命令分叉。

当前仓库可见性和默认状态如下：

| 仓库 | 可见性 | GitHub Actions 默认状态 | 说明 |
| --- | --- | --- | --- |
| `research-workspace` | public | 启用 | `contracts.yml` 运行公开契约回归和 `ci-smoke`，不检出私有子模块 |
| `market-data-platform` | private | 关闭 | 使用仓库本地门禁和共享 `pre-push` |
| `deep-learning-tick-data-prediction` | public | 启用 | `ci.yml` 运行轻量 PR 检查 |
| `alpha-research` | private | 关闭 | 使用仓库本地门禁和共享 `pre-push` |
| `portfolio-backtester` | public | 启用 | `ci.yml` 运行 PR 检查 |
| `strategy-research` | private | 关闭 | 使用本仓测试、研究层质量门禁和共享 `pre-push` |
| `strategy-app` | private | 关闭 | 使用仓库权威 `scripts/dev/check.py` |
| `strategy-pipeline` | private | 关闭 | 使用仓库 `scripts/dev/run_tests.sh full` |
| `quant-execution-engine` | public | 启用 | `ci.yml` 运行 lint、格式、类型和单元测试 |

顶层 workflow 不递归检出 private 子模块。远端检查通过只说明公开范围已通过，不能代替完整工作区验证。

## 跨仓库边界

`python scripts/workspace_import_boundaries.py --check` 检查以下方向：

- `alpha-research` 不新增对策略编排和回测内部实现的运行时依赖
- `portfolio-backtester` 不新增对策略编排和 alpha 内部实现的运行时依赖
- 数据平台和执行引擎不导入已移除的共享命名空间
- `strategy-app` 不导入 `strategy-pipeline`
- `strategy-pipeline` 不重新承载 `alpha_research`、`portfolio_backtester` 或策略应用源码
- 第三方框架对象不跨仓库文件契约

顶层委托配置是 `scripts/submodule_checks.json`。所有委托 `lint` 和 `full` 都先验证 lockfile，清单里的直接 `uv run` 使用 `--locked`。子仓库的维护性阈值和排除项留在各自仓库。

维护性基线记录已知债务上限。删除大文件、长函数或复杂热点后，应在同一提交中下调基线和预算。上调需要独立的负责人决策记录。

## 依赖与安全

依赖审计能力按仓库实际配置管理，不能假定所有仓库都已经安装 `pip-audit`。

当前顶层、`market-data-platform`、`alpha-research`、`portfolio-backtester`、`strategy-app`、`strategy-pipeline` 和 `quant-execution-engine` 的开发依赖包含 `pip-audit`。当前 `deep-learning-tick-data-prediction` 和 `strategy-research` 尚未把 `pip-audit` 纳入开发依赖，需要在后续依赖治理中补齐或登记明确例外。

根仓 public CI 已运行：

```bash
python scripts/run_quality_checks.py --profile ci-smoke
```

其中 `pip-audit` 使用根项目的 `dev` 依赖环境。依赖审计在当前 PR 验证中返回 0 个已知漏洞。

其他仓库常用手工检查：

```bash
uv run --group dev pip-audit
uvx deptry .
uvx bandit -q -r src -lll
```

使用 `[project.optional-dependencies].dev` 的仓库改用 `uv run --extra dev pip-audit`。使用 `[dependency-groups].dev` 的仓库按自身配置使用 `uv run --group dev pip-audit`。

依赖审计应按仓库可见性、风险和运行成本进入 public CI、本地完整门禁或定期审计。工具已经安装却长期不执行的情况应视为治理缺口。

## 覆盖率

各仓库使用自己的包路径作为 coverage 的 `source`。覆盖率按风险分层提高，不设置跨仓库统一百分比。

建议采用以下原则：

- 契约、发布、执行和资金相关模块优先提高 branch coverage。
- 已有覆盖率不应无理由下降。
- 新增关键路径需要相应测试覆盖。
- 研究探索和一次性诊断可以使用较低覆盖要求，但应保持明确边界。
- `deep-learning-tick-data-prediction` 当前已经配置 branch coverage 和 `fail_under = 80`，其他仓库不应直接复制这个数值。

## 非 Python 文件

工作区包含 Bash、systemd 和 GitHub Actions YAML。后续质量治理应在相应文件发生改动时使用 ShellCheck、`shfmt --diff` 和 `actionlint`。是否引入 `yamllint` 取决于实际 YAML 结构和误报成本。

## Dead code 与忽略项

`python scripts/run_quality_checks.py --profile dead-code` 运行高置信度 dead-code 建议检查。它默认只报告，不阻塞日常门禁。

历史 `# noqa` 审计已经确认，早期数千条统计主要来自把 `.venv` 第三方代码计入扫描。当前重点是缩小真实设计类豁免范围，并为必要例外保留原因、负责人、复核节点和删除条件。

`market-data-platform` 的大面积 `F401` 文件级豁免用于兼容门面重导出，后续应在保证公开 API 稳定的前提下逐步收窄。`strategy-pipeline` 和 `quant-execution-engine` 的类型检查例外也应继续按具体模块缩小范围。
