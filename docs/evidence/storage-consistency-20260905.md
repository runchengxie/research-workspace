# 存储维护版本更新的检查记录

## 范围

本次候选将深度学习子模块更新到 `9f22a99`、market-data-platform 更新到 `a22ac04`、
alpha-research 更新到 `b8fac12`，同步已锁定版本记录，
并用现有生成器重新生成维护性清单。生产版本、定时任务和研究数据保持不变。

## 初始问题

原有的维护性清单一致性、版本记录一致性和生产维护预演测试均通过，共 3 项。
测试临时目录放在可用空间充足的磁盘分区，保留原有磁盘空间门禁。
顶层严格质量检查通过。完整工作区测试为 427 项通过、3 项失败。

## 已完成的 owner 重构

用户确认后，已在两个独立 owner worktree 完成函数拆分，保持数据转换顺序和输出语义。
下表记录直接扫描候选源码得到的数量，原有预算未调整。

| 项目 | 指标 | 原有预算 | 重构前 | 候选数量 |
| --- | --- | ---: | ---: | ---: |
| market-data-platform | 长函数 | 89 | 90 | 89 |
| market-data-platform | 复杂度热点 | 56 | 58 | 56 |
| alpha-research | 长函数 | 28 | 29 | 28 |
| alpha-research | 复杂度热点 | 32 | 33 | 32 |

market-data-platform 的分批全量测试通过 895 项，跳过 1 项。alpha-research 全量测试
通过 436 项，跳过 4 项。新增测试覆盖披露日期、输入不变性、日期范围、数据源优先级、
整日替换和 checkpoint 恢复。两个项目的 lint、格式和变更文件类型检查通过。
market-data-platform 的质量债、维护性、兼容性和架构检查通过，alpha-research 的
维护性棘轮检查通过。

## 类型检查修复

初始全量类型检查中，alpha-research 有 45 项诊断，market-data-platform 有 13 项诊断
（含 2 项 warning）。使用相同锁定工具和依赖环境检查未修改的 main，得到相同诊断。
用户确认后，已修复可选依赖导入、可空返回值、标量转换和测试类型约束。
两个 owner 的全量类型检查与严格 warning 门禁均通过，完整 pre-push 门禁通过。

独立审查发现一个可选依赖测试可能将损坏安装误判为跳过，已恢复为失败并独立复验。
两项 owner 修复均已合并，market-data-platform PR #126，alpha-research PR #75。
alpha-research 的两项远端质量检查通过。market-data-platform 按私有仓库规则保留
本地完整门禁，未启用远端 CI。

本次没有跳过类型检查、提高预算或改变研究行为。顶层 gitlink 与清单已更新。
生产版本、定时任务和研究数据保持原状。

## 组合验证

`TMPDIR` 指向可用空间充足的独立测试目录，未降低磁盘空间门禁。

- `python3 scripts/run_workspace_tests.py` 通过 430 项测试，原有一致性与预算失败已消除。
- `uv run --extra dev python -m pytest tests -q` 在 strategy-research 中通过 399 项测试。
- `python3 scripts/run_research_layer_lint.py` 通过 lint、格式、类型和命令行预演。
- `python3 scripts/run_quality_checks.py --profile hard` 通过。独立安装依赖与工作区版本
  的既有差异仍作为 warning 报告，未改写其他 owner 的依赖锁。
- `python3 src/research_contracts/smoke_contracts.py` 无错误，三个未安装的可选命令行
  入口仍报告 warning。
- `python3 scripts/strategy_evidence_gate.py --strict` 通过，已登记的研究证据缺口保持不变。
