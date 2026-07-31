# 工作区质量治理

顶层仓库只维护跨仓库质量入口。每个子仓库仍拥有自己的 Ruff、格式、类型检查、pytest 和维护性配置。

## 检查分类

| 仓库 | 基础检查 | 补充诊断 | 人工复核 |
| --- | --- | --- | --- |
| 顶层工作区 | Ruff、格式、`ty`、secret scan、pytest、doctor、契约 smoke | 依赖审计、dead-code 报告 | 私有子模块权限、版本组合和发布清单 |
| `market-data-platform` | Ruff、格式、`ty`、pytest、架构治理 | 依赖审计 | 数据权限、数据质量和 current 契约发布 |
| `alpha-research` | Ruff、格式、`ty`、pytest、导入冒烟 | 研究证据定点测试 | signal artifact 和候选晋升证据 |
| `portfolio-backtester` | Ruff、格式、`ty`、pytest、导入冒烟 | 回测定点测试 | 成本、换手、容量和报告口径 |
| `research-apps` | lockfile、Ruff、格式、`ty`、pytest、维护性 ratchet 和隔离构建 | 仓库权威 `scripts/dev/check.py` | F-lite、slow-volume、DeepSeek V4 runner 和普通研究报告 |
| `strategy-pipeline` | 仓库脚本中的 lint、format、`ty`、pytest 和边界检查 | 依赖审计 | 长窗口研究、编排和目标文件导出 |
| `quant-execution-engine` | Ruff、格式、`ty`、快速 pytest | 集成和端到端测试 | 券商凭证、模拟盘、实盘和对账 |

执行引擎已经移除 mypy。顶层委托配置不再提供对应的建议检查 profile。

## 顶层命令

```bash
python scripts/run_quality_checks.py --profile hard
python scripts/run_quality_checks.py --profile ci-smoke
python scripts/run_quality_checks.py --profile architecture
python scripts/run_quality_checks.py --profile secrets
python scripts/run_quality_checks.py --profile dead-code
python scripts/run_submodule_checks.py --profile release_typecheck --dry-run
```

`hard` 包含 Ruff、格式、`ty`、工作区导入边界和 secret scan。`ci-smoke` 是缺少私有子模块时可运行的顶层轻量档位。名称保留用于本地和未来自动化，目前没有活动 GitHub Actions workflow。

顶层类型检查只覆盖 `pyproject.toml` 登记的 workspace 自有模块和脚本。当前已纳入
`workspace_doctor.py`、`workspace_governance.py`、`workspace_governance_quality.py` 和
`maintainability_baseline.py`。新增质量门禁脚本时，应同时判断是否加入 `ty` 的目标列表。

## 跨仓库边界

`python scripts/workspace_import_boundaries.py --check` 检查以下方向：

- `alpha-research` 不新增对策略编排和回测内部实现的运行时依赖
- `portfolio-backtester` 不新增对策略编排和 alpha 内部实现的运行时依赖
- 数据平台和执行引擎不导入已移除的共享命名空间
- `strategy-pipeline` 不重新承载 `alpha_research` 或 `portfolio_backtester` 源码
- 第三方框架对象不跨仓库文件契约

顶层委托配置是 `scripts/submodule_checks.json`。所有委托 `lint` 和 `full` 都先验证
lockfile，清单里的直接 `uv run` 使用 `--locked`。子仓库的维护性阈值和排除项留在
各自仓库。

维护性 baseline 是已知债务上限。删除大文件、长函数或复杂热点后，应在同一提交中下调
baseline 和 budget。上调需要独立的 waiver 记录，不能只改两个数值来吸收新增债务。

## 自动化状态

`.github/workflows/superproject.yml.disabled` 是停用模板，顶层与六个子仓库的 Actions
权限均禁用。`portfolio-backtester` 保留一份 `ci.yml` 定义，但当前不会运行。其余仓库只
保留停用模板或没有 workflow。当前检查以本地 pre-push 为权威入口。恢复远端自动化时，
应先核对私有子模块权限、Python 版本和每个子仓库的实际命令，再更新文档。

## 依赖与安全

依赖审计和静态安全扫描按仓库运行：

```bash
uvx pip-audit
uvx deptry .
uvx bandit -q -r src -lll
```

provider 软件开发工具包（SDK）、券商 SDK、动态导入和可选依赖需要记录用途、负责人和复核命令。凭证泄漏属于阻塞问题。

coverage 按高风险模块逐步提高，不设置跨仓库统一阈值。
