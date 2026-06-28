# 架构拆分收敛清单（stage 4）

本页是从“阶段 3.5 物理拆分”走向“阶段 4 长期可维护边界”的可执行清单。

## 一、先确认现在是什么状态（已具备）

- `alpha-research`、`portfolio-backtester` 已成为独立 submodule。
- `strategy-pipeline` 负责运行编排、CLI 与 `targets.json` 导出。
- 文件交接主链路是：
  - `signals.parquet` / `signals.meta.json`（alpha 输出）
  - `positions_by_rebalance.csv`（回测输出）
  - `targets.json` / `targets.json.lineage.json`（执行交接输出）
- `market-data-platform` 和 `quant-execution-engine` 已经不承接研究核心实现。
- Import boundary 脚本与 test 已包含：
  - `workspace_import_boundaries.py`
  - `strategy-pipeline/tests/test_import_boundary.py`

## 二、落地目标（你这次强调的四条风险对齐）

1. **短期兼容但长期解耦 cstree 命名空间**
   - 短期保留共享 `cstree` facade（便于现有 CLI 与历史入口连续性）。
   - 长期通过 owner API 与文档契约，把 `alpha-research` 与 `portfolio-backtester` 的稳定入口作为显式主入口引用。

2. **所有关键交接都走 artifact contract**
   - `alpha-research` 仅输出信号与诊断契约化产物。
   - `portfolio-backtester` 仅消费这些 artifact，输出持仓/回测契约产物。
   - `strategy-pipeline` 只做编排与导出，不在同层重算内部逻辑。

3. **回测引擎不绑定 alpha 实现细节**
   - `portfolio-backtester` 不应在 runtime import 回到 `cstree.alpha`。
   - `alpha-research` 不应在 runtime import 回到 `cstree.backtesting`。

4. **执行与回测严格分离**
   - `quant-execution-engine` 只消费 `targets.json`。
   - `cstree export-targets` 不触发下单、不会做券商预演。

## 三、硬性验收项（建议按版本组合发布前逐项打勾）

- [ ] **边界扫描通过**：`python scripts/workspace_import_boundaries.py --check`
- [ ] **边界测试通过**：`python -m pytest tests/test_workspace_import_boundaries.py -q`
- [ ] **strategy-pipeline 内部边界通过**：`scripts/dev/run_tests.sh import-boundary`
- [ ] **顶层文件约定检查通过**：`python scripts/smoke_contracts.py --strict`
- [ ] **顶层质量门禁通过**：`python scripts/run_quality_checks.py --profile hard`
- [ ] **文档契约一致**：`docs/contracts.md` 与 `docs/platform-workflow.md` 的链路说明与清单保持一致。

## 四、建议的长期方向（可逐步推进）

- 为长期治理保留明确的 owner API（例如通过 `alpha-research` 与 `portfolio-backtester` 入口）
  并将 `cstree` 兼容面控制为“外部 facade + 兼容出口”。
- 将研究流程按“因子挖掘 → 组合构建 → 风控容量 → 执行交接”的闭环证据逐步沉淀为固定 sidecar。
- 对每类新增功能，优先补 `contracts` + `tests`，再补 `strategy-pipeline` 编排与 `workspace-import-boundary` 例外。

## 五、注意事项（容易误解的边界）

- 该链路不是“研究一次跑完就结束”的线性流程：
  在每次新特征/新构造层扫验后，需回到前一层（通常是 alpha / backtest / 风险层）补证据，再决定晋升。
- 本清单不建议把 `targets.json` 的成功 dry-run 解释为真实券商就绪。

