# 工作区质量治理矩阵

顶层仓库只管理稳定 profile 和跨仓库发布边界。每个子仓库继续拥有自己的 Ruff、类型检查、pytest、coverage 和 optional dependency 配置；顶层 Ruff 只检查 `scripts/` 与 `tests/`。

## 检查分类

| 仓库 | 硬门禁 | 建议项 | 人工或发布复核 |
| --- | --- | --- | --- |
| superproject | Ruff、Ruff format、secret scan、顶层 pytest、doctor、contract smoke | `pip-audit`、`deptry`、选择性 coverage ratchet | 港股 restore-only archive 复核、发布检查清单 |
| `market-data-platform` | Ruff、Ruff format、Pyright、pytest | `pip-audit`、`deptry`、Bandit 高置信规则、contract 模块 coverage ratchet | provider entitlement、数据质量报告、registry/current publication |
| `cross-sectional-trees` | 仓库自有 lint、format、Pyright、pytest | `pip-audit`、`deptry`、target-export coverage ratchet | 长窗口 benchmark、CPCV、turnover/cost、capacity 复核 |
| `quant-execution-engine` | Ruff、Ruff format、Pyright、pytest | mypy、`pip-audit`、`deptry`、Bandit 高置信规则、risk/execution-state coverage ratchet | 券商凭证扫描、受监督 paper/live smoke、对账和操作批准 |

顶层委托配置是 `scripts/submodule_checks.json`。`lint` 会同时运行子仓库自己的边界与维护债
ratchet：数据平台包含 `scripts/dev/architecture_governance.py --check`，策略研究包含
`scripts/dev/run_tests.sh maintainability`。`type` 始终表示各仓库当前 hard type gate；
执行引擎的 `mypy_advisory` 在迁移后的一个发布周期内单独运行，不替代 Pyright。
当前 Pyright 允许保留已分类 warning：延迟导出列表和 optional dependency source visibility；
任何 error 都会阻塞 hard gate。

## 顶层命令

```bash
python scripts/run_quality_checks.py --profile hard
python scripts/run_quality_checks.py --profile secrets
python scripts/run_submodule_checks.py --profile mypy_advisory \
  --submodule quant-execution-engine
```

涉及 provider 或券商凭证读取逻辑时，还应对改动所属子仓库执行 credential review；credential leak 属于阻塞问题，不按 advisory 处理。港股材料不再通过工作区内 public demo 路线发布，只保留 private restore-only archive 复核。

执行引擎至少保留一个发布周期的 mypy 观察期。下一次 release review 中，如果 mypy 没有独有阻塞发现，且 Pyright warning 分类保持稳定，可以评估移除 advisory。若需要回滚，将 `scripts/submodule_checks.json` 中执行引擎的 `type` 恢复为 mypy；已完成的 SDK 边界窄化修复继续保留。

## Advisory 依赖检查

依赖审计先作为 advisory 记录，不直接阻塞 A 股迁移：

```bash
uvx pip-audit
uvx deptry .
uvx bandit -q -r src -lll
```

每个仓库单独维护 baseline 或 allowlist。provider SDK、券商 SDK、UI extra、动态导入和仅在
本地操作环境安装的依赖必须先标注 owner、用途和复核命令，再决定是否晋升硬门禁。
coverage 同样按 contract、manifest、target export、risk、execution state 等高风险模块逐步
ratchet，不设置跨仓库统一阈值。
