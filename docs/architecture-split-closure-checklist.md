# 架构边界发布清单

> status: active
> owner: workspace
> last_verified: 2026-07-16
> source_of_truth: yes
> superseded_by: n/a

物理拆分已经完成。本页只保留当前版本组合发布前需要复核的架构边界。历史阶段记录见
[归档入口](archive/README.md)。

## 当前边界

- `market-data-platform` 发布数据契约、资产、清单和 registry。
- `alpha-research` 使用 `alpha_research.*`，输出 `signals.parquet` 和 `signals.meta.json`。
- `portfolio-backtester` 使用 `portfolio_backtester.*`，输出 `positions_by_rebalance.csv`。
- `strategy-pipeline` 使用 `strategy_pipeline.*`，负责编排和 `targets.json` 导出。命令行入口为 `strategy`。
- `quant-execution-engine` 读取 `targets.json`，研究仓库不连接券商或提交订单。
- 跨仓库交接使用文件契约，各仓库不导入其他仓库的内部实现。

## 发布前检查

- [ ] 框架边界符合 [ADR-0001](adr/0001-framework-integration-boundaries.md)，状态已同步到 [`framework-integration-ledger.yml`](framework-integration-ledger.yml)。
- [ ] Qlib、vn.py 和 LEAN 类型没有进入跨仓库 Python 公共返回值或产物（artifact）schema。
- [ ] 未安装 Qlib 或 vn.py 时，原生端到端路径仍可导入和运行。
- [ ] 边界扫描通过：`python scripts/workspace_import_boundaries.py --check`
- [ ] 边界测试通过：`uv run python -m pytest tests/test_workspace_import_boundaries.py -q`
- [ ] 策略仓库内部边界通过：`cd strategy-pipeline && scripts/dev/run_tests.sh import-boundary`
- [ ] 顶层文件约定通过：`python src/research_contracts/smoke_contracts.py --strict`
- [ ] 顶层质量门禁通过：`python scripts/run_quality_checks.py --profile hard`
- [ ] `docs/contracts.md`、`docs/platform-workflow.md` 和机器可读契约保持一致。

## 变更规则

- 第三方框架通过 adapter 接入。LEAN 只通过框架无关的场景契约做对照。
- 删除原生实现前，先保存等价性证据、兼容窗口和回滚方案。
- 新的跨仓库字段先更新文件契约和测试，再更新编排层。
- 新增边界例外时，记录 owner、原因、移除条件和对应测试。
- `targets.json` dry-run 只证明文件可以交接。券商能力由执行仓库单独验收。
