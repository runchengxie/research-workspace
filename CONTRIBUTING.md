# 贡献说明

本工作区是多个子模块的集成层。大多数功能改动应进入对应子仓库。顶层改动集中在
跨仓库文件约定、子模块版本、工作区健康检查、发布清单和治理文档。

## 范围

- 数据平台改动进入 `market-data-platform`。
- Alpha、因子和信号研究改动进入 `alpha-research`。
- 组合构造和研究回测改动进入 `portfolio-backtester`。
- 策略编排、命令行（CLI） 兼容层和执行目标导出改动进入 `strategy-pipeline`。
- 交易执行改动进入 `quant-execution-engine`。
- 顶层文档和脚本只覆盖跨仓库交接、文件约定、发布、健康检查和治理事项。

改动子模块内容时，先阅读对应子模块的 `AGENTS.md`，并在最终汇报中包含子模块 `git status --short`。不要回退无关的子模块改动或脏 gitlink。

## 验证顺序

汇报验证结果时按以下顺序：

1. 数据平台。
2. Alpha 研究。
3. 组合回测。
4. 策略编排。
5. 交易执行。
6. 顶层文档和 doctor。
7. 剩余限制。

未触及的仓库说明无需 focused tests。

## 维护治理门禁

提交前检查改动是否涉及以下事项：

- 新增或扩展已废弃入口。
- 新增一次性脚本或迁移工具。
- 新增 Ruff 或 `ty` 排除项。
- 改动 `targets.json` 交接约定。
- 读取数据供应商或券商凭证。
- 需要迁移说明、回退路径、恢复证据或定点验证。

这些检查的权威入口是 [docs/deprecations.md](docs/deprecations.md)、[docs/script-lifecycle.yml](docs/script-lifecycle.yml)、[docs/quality-coverage-governance.yml](docs/quality-coverage-governance.yml) 和 [docs/maintainability-refactor-roadmap.yml](docs/maintainability-refactor-roadmap.yml)。
