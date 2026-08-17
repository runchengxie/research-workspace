# 发布检查清单

本清单用于更新子模块指针和发布一组已经验证的版本组合。各业务领域的详细检查留在
对应文档，本页只保留所有发布都需要完成的项目。

## 通用门禁

- [ ] 顶层和本次涉及的子仓库都位于 `main`，工作树只包含预期改动。
- [ ] `git fetch --all --prune` 后，各仓库与远端 `main` 都没有 ahead 或 behind。
- [ ] `git branch --no-merged main` 没有待合并分支，远端也没有遗留功能分支。
- [ ] `git submodule status --recursive` 与准备发布的 Git 子模块指针（gitlink）一致。
- [ ] `python scripts/install_pre_push_hooks.py --check` 通过。
- [ ] `python scripts/workspace_doctor.py --strict` 通过，或每条警告都有发布记录。
- [ ] `python src/research_contracts/smoke_contracts.py --strict` 通过。
- [ ] 顶层 pytest 通过。准确命令见[工作区维护](workspace-maintenance.md)。
- [ ] `python scripts/run_quality_checks.py --profile hard` 通过。
- [ ] `python scripts/run_submodule_checks.py --profile full` 对本次涉及的子仓库通过。
- [ ] `python scripts/run_submodule_checks.py --profile release_typecheck` 已运行并记录结果。
- [ ] `python scripts/print_version_matrix.py` 的结果与准备提交的子模块指针一致。
- [ ] 暂存区不含凭证、`.env`、大型数据、缓存、`artifacts/`、`outputs/` 或本地绝对路径。

## 架构边界门禁

- [ ] 框架状态已同步到 [`framework-integration-ledger.yml`](framework-integration-ledger.yml)。
- [ ] Qlib、vn.py、LEAN 和 Backtrader 类型没有进入跨仓库公开返回值或产物 schema。
- [ ] 未安装可选框架时，原生路径仍可导入和运行。
- [ ] `python scripts/workspace_import_boundaries.py --check` 通过。
- [ ] `uv run python -m pytest tests/test_workspace_import_boundaries.py -q` 通过。
- [ ] `cd strategy-pipeline && scripts/dev/run_tests.sh import-boundary` 通过。
- [ ] 新增边界例外已经记录 owner、原因、移除条件和对应测试。

## 按改动范围追加检查

| 范围 | 检查入口 |
| --- | --- |
| A 股数据资产与就绪度 | [data-transition-playbook.md](data-transition-playbook.md) |
| 跨仓库文件格式 | [contracts.md](contracts.md) |
| framework adapter | [archive/framework-adapter-release.md](archive/framework-adapter-release.md) |
| 港股历史恢复或再次冻结 | [archive/hk/README.md](archive/hk/README.md) |
| 研究、组合与执行交接 | [platform-workflow.md](platform-workflow.md) |
| 维护性和质量债务 | [maintainability-governance.md](maintainability-governance.md) 与 [quality-governance.md](quality-governance.md) |

涉及 A 股发布时，还要运行以下就绪度检查并保存结论：

```bash
python src/research_contracts/a_share_readiness.py \
  --artifacts-root "$DATA_PLATFORM_ROOT" \
  --evidence-manifest <json> \
  --pretty
```

涉及 `targets.json` 时，确认目标文件和血缘（lineage）sidecar 来自同一研究运行。执行侧至少完成
解析和 dry-run。模拟盘与实盘仍由 `quant-execution-engine` 的门禁和人工操作记录决定。

## 发布记录

记录实际提交、数据资产版本、检查结果和保留限制。动态版本状态由
`python scripts/print_version_matrix.py` 生成，不把脚本输出手工复制成长期静态表。
