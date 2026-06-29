# 工作区质量治理矩阵

顶层仓库只管理稳定 profile 和跨仓库发布边界。每个子仓库继续拥有自己的 Ruff、类型检查、pytest、coverage 和 optional dependency 配置；顶层 Ruff 通过 `pyproject.toml` 限定在 workspace 自有脚本/测试，并排除子仓与历史探索脚本。

## 检查分类

| 仓库 | 硬门禁 | 建议项 | 人工或发布复核 |
| --- | --- | --- | --- |
| superproject | Ruff、Ruff format、ty、secret scan、顶层 pytest、doctor、contract smoke | BasedPyright advisory、`pip-audit`、`deptry`、选择性 coverage ratchet | 港股恢复专用归档复核、发布检查清单 |
| `market-data-platform` | Ruff、Ruff format、ty、pytest | BasedPyright 建议项、`pip-audit`、`deptry`、Bandit 高置信规则、contract 模块 coverage ratchet | provider entitlement、数据质量报告、registry/current publication |
| `alpha-research` | Ruff、Ruff format、ty、pytest、import smoke | BasedPyright 建议项、pytest coverage、CPCV/PBO 定点测试、feature evidence fixtures | signal artifact、feature evidence、promotion gate |
| `portfolio-backtester` | Ruff、Ruff format、ty、pytest、import smoke | BasedPyright 建议项、pytest coverage、capacity/exposure/backtest 定点测试 | turnover/cost、capacity、benchmark ladder、reporting |
| `strategy-pipeline` | 仓库自有 lint、format、ty、pytest | BasedPyright 建议项、`pip-audit`、`deptry`、target-export coverage ratchet | 长窗口 benchmark、编排层 smoke、目标文件导出复核 |
| `quant-execution-engine` | Ruff、Ruff format、ty、pytest | BasedPyright advisory、mypy、`pip-audit`、`deptry`、Bandit 高置信规则、risk/execution-state coverage ratchet | 券商凭证扫描、受监督 paper/live smoke、对账和操作批准 |

顶层 hard profile 还包含 workspace boundary gate：
`python scripts/workspace_import_boundaries.py --check`。该检查把阶段 3.5 /
阶段 4 的拆分方向转成可 ratchet 的预算：`alpha-research` 不应增加对
`cstree.pipeline` / `cstree.backtesting` 的运行时依赖，`portfolio-backtester`
不应增加对 `cstree.pipeline`、strategy-pipeline 根模块或 `cstree.alpha` 的运行时依赖，
数据平台和执行引擎不应导入 `cstree` 内部，strategy-pipeline 不应导入执行引擎实现；
同时 strategy-pipeline 不应重新承载本地 `cstree.alpha` / `cstree.backtesting`
实现源码。当前预算只封顶既有反向依赖和 source layout；清掉一批后再下调对应
`max_allowed`。

顶层委托配置是 `scripts/submodule_checks.json`。`lint` 会同时运行子仓库自己的边界与维护债
ratchet：数据平台包含 `scripts/dev/architecture_governance.py --check`，策略编排包含
`scripts/dev/run_tests.sh maintainability`。`type` 始终表示各仓库当前基础类型门禁；
现在统一为 `ty check`。`alpha-research` 和 `portfolio-backtester` 的 smoke / BasedPyright
配置不应通过 sibling source path 补齐 import；`release_typecheck` 统一运行
BasedPyright advisory。执行引擎的 `mypy_advisory` 在迁移后的一个发布周期内
单独运行，不替代 `ty check` 或 BasedPyright advisory。

## 顶层命令

```bash
python scripts/run_quality_checks.py --profile hard
python scripts/run_quality_checks.py --profile basedpyright
python scripts/run_quality_checks.py --profile architecture
python scripts/workspace_import_boundaries.py --check
python scripts/run_quality_checks.py --profile secrets
python scripts/run_quality_checks.py --profile dead-code
python scripts/run_submodule_checks.py --profile release_typecheck --dry-run
python scripts/run_submodule_checks.py --profile mypy_advisory \
  --submodule quant-execution-engine
```

涉及 provider 或券商凭证读取逻辑时，还应对改动所属子仓库执行 credential review；credential leak 属于阻塞问题，不按建议项处理。港股材料不再通过工作区内公开演示路线发布，只保留私有恢复专用归档复核。

执行引擎至少保留一个发布周期的 mypy 观察期。下一次发布复核中，如果 mypy 没有独有阻塞发现，且 BasedPyright warning 分类保持稳定，可以评估移除 mypy 建议项。若需要回滚，将 `scripts/submodule_checks.json` 中执行引擎的 `mypy_advisory` 保持为人工复核入口；已完成的 SDK 边界窄化修复继续保留。所有仓库统一使用 BasedPyright。

## 依赖建议项

依赖审计先作为建议项记录，不直接阻塞 A 股迁移：

```bash
uvx pip-audit
uvx deptry .
uvx bandit -q -r src -lll
```

每个仓库单独维护 baseline 或 allowlist。provider SDK、券商 SDK、UI extra、动态导入和仅在
本地操作环境安装的依赖必须先标注 owner、用途和复核命令，再决定是否晋升硬门禁。
coverage 同样按 contract、manifest、target export、risk、execution state 等高风险模块逐步
ratchet，不设置跨仓库统一阈值。

Dead-code 扫描先保持建议项：顶层入口只扫描 superproject-owned Python 代码，并默认把
Vulture 的高置信发现降级为 advisory；清理到零发现后可以用 `python scripts/dead_code_advisory.py
--strict` 做本地复核。子仓库 dead-code 候选应进入对应子仓库的维护性 ratchet，不由顶层直接阻塞。
