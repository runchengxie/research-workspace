# 版本矩阵

本页记录工作区版本组合。真正锁定版本的是 Git 子模块指针；本页只保存当前检出状态和人工验证结论。

## 当前检出状态

先用脚本生成当前状态：

```bash
python scripts/print_version_matrix.py
```

当前本地输出：

| component | commit |
| --- | --- |
| workspace | `de0a8d1` + local changes |
| market-data-platform | `fce11ef` |
| alpha-research | `c694b08` |
| portfolio-backtester | `e05bde7` |
| cross-sectional-trees | `143cc69` |
| quant-execution-engine | `00cfced` |

如果脚本报告 `not initialized`，先运行：

```bash
git submodule update --init --recursive
```

普通 zip 或 source snapshot 没有 `.git` 元数据，不能生成 commit matrix；这种场景只适合阅读顶层文档，不能作为版本锁定或完整链接测试依据。

## 已验证组合

| 日期 | 顶层仓库提交 | market-data-platform | alpha-research | portfolio-backtester | cross-sectional-trees | quant-execution-engine | 验证状态 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-06-27 | stage-3 split branch local checkout | `fce11ef` | `c694b08` | `e05bde7` | `143cc69` | `00cfced` | `alpha-research` 和 `portfolio-backtester` 已拆为 workspace 子模块；新子模块 lint/type/import smoke 通过；`cross-sectional-trees` 保留编排层并通过 lint/type/fast tests；顶层 workspace 测试和子模块检查通过 | `python scripts/run_submodule_checks.py --profile full --submodule alpha-research --submodule portfolio-backtester`；`scripts/dev/run_tests.sh fast` in `cross-sectional-trees`；`uv run --with pytest python -m pytest tests -q` |
| 2026-06-13 | `hk-freeze-20260613` -> `8d2f5fd` | `hk-freeze-20260613` -> `e802f12` | n/a | n/a | `hk-freeze-20260613` -> `b6e4cad` | `hk-freeze-20260613` -> `dc520cf` | 港股 restore-only freeze tag 已推送；private legacy archive staging 已从该 tag 组合重建并通过 gate；`hk-research-workspace-archive` 已创建为 private restore-only superproject；删除评审仍 blocked pending audit | `docs/evidence/hk-private-archive-stage-20260613.json`；`docs/evidence/hk-research-workspace-archive-20260613.json`；`python scripts/hk_archive_gate.py --check --export-manifest /tmp/hk-quant-legacy-archive-export-20260613/archive-export-manifest.json --format json` |
| 2026-05-27 | `f38ce4c` | `a310a80` | n/a | n/a | `10ca23f` | `85ad0e7` | 部分验证 | 已验证研究系统导出目标持仓文件，以及执行引擎解析文件并生成离线调仓计划；模拟盘持续联调证据仍需补齐 |

## 更新方法

生成当前版本矩阵：

```bash
python scripts/print_version_matrix.py
```

然后根据实际验证结果填写：

- 是否只验证了解析或预演流程。
- 是否验证了模拟盘端到端流程。
- 是否涉及实盘；实盘状态只能按人工监督下的真实结果填写。
- 子模块是否存在未提交改动；如存在，请标为本地工作状态，发布前先清理或提交。
