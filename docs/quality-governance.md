# 工作区质量治理矩阵

顶层仓库只管理稳定 profile 和跨仓库发布边界。每个子仓库继续拥有自己的 Ruff、类型检查、
pytest、coverage 和 optional dependency 配置；顶层 Ruff 只检查 `scripts/` 与 `tests/`。

## 检查分类

| 仓库 | Hard gate | Advisory | Manual / release review |
| --- | --- | --- | --- |
| superproject | Ruff、Ruff format、secret scan、顶层 pytest、doctor、contract smoke | `pip-audit`、`deptry`、选择性 coverage ratchet | 港股公开 demo staging scan、release checklist |
| `market-data-platform` | Ruff、Ruff format、Pyright、pytest | `pip-audit`、`deptry`、Bandit 高置信规则、contract 模块 coverage ratchet | provider entitlement、数据质量报告、registry/current publication |
| `cross-sectional-trees` | repo 自有 lint、format、Pyright、pytest | `pip-audit`、`deptry`、target-export coverage ratchet | 长窗口 benchmark、CPCV、turnover/cost、capacity 复核 |
| `quant-execution-engine` | Ruff、Ruff format、mypy、pytest | Pyright、`pip-audit`、`deptry`、Bandit 高置信规则、risk/execution-state coverage ratchet | 券商凭证扫描、受监督 paper/live smoke、对账和操作批准 |

顶层委托配置是 `scripts/submodule_checks.json`。`type` 始终表示各仓库当前 hard type gate；
执行引擎的 `pyright_advisory` 单独运行，不替代 mypy。

## 顶层命令

```bash
python scripts/run_quality_checks.py --profile hard
python scripts/run_quality_checks.py --profile secrets
python scripts/run_quality_checks.py --profile secrets \
  --demo-stage /tmp/hk-cross-sectional-strategy-demo
python scripts/run_submodule_checks.py --profile pyright_advisory \
  --submodule quant-execution-engine
```

公开 demo 发布前必须扫描 staging tree。涉及 provider 或券商凭证读取逻辑时，还应对改动所属
子仓库执行 credential review；credential leak 属于阻塞问题，不按 advisory 处理。

## Advisory 依赖检查

依赖审计先作为 advisory 记录，不直接阻塞 A 股迁移：

```bash
uvx pip-audit
uvx deptry .
uvx bandit -q -r src -lll
```

每个仓库单独维护 baseline 或 allowlist。provider SDK、券商 SDK、UI extra、动态导入和仅在
本地操作环境安装的依赖必须先标注 owner、用途和复核命令，再决定是否晋升 hard gate。
coverage 同样按 contract、manifest、target export、risk、execution state 等高风险模块逐步
ratchet，不设置跨仓库统一阈值。
