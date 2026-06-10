# 贡献说明

本工作区是三个子模块的集成层。大多数功能改动应进入对应子仓库；顶层改动应集中在跨仓库文件约定、子模块版本、工作区健康检查、发布检查清单、治理清单和跨仓库说明文档。

## 范围

- 数据平台改动进入 `market-data-platform`。
- 策略研究改动进入 `cross-sectional-trees`。
- 交易执行改动进入 `quant-execution-engine`。
- 顶层文档和脚本只覆盖跨仓库交接、contract、发布、健康检查和治理事项。

改动子模块内容时，先阅读对应子模块的 `AGENTS.md`，并在最终汇报中包含子模块 `git status --short`。不要回退无关的子模块改动或脏 gitlink。

## 验证顺序

汇报验证结果时按以下顺序：

1. 数据平台。
2. 策略研究。
3. 交易执行。
4. 顶层文档和 doctor。
5. 剩余限制。

未触及的仓库说明无需 focused tests。

## 维护治理门禁

开 PR 前，检查改动是否涉及以下事项：

- 新增或扩展 `deprecated surface`。
- 新增 `one-off script` 或迁移工具。
- 新增 Ruff、Pyright 或 mypy 排除项。
- 改动 `targets.json` 交接 contract。
- 读取 provider 或 broker 凭证。
- 需要 migration note、rollback path、restore evidence 或 focused verification。

这些检查的权威入口是 [docs/deprecations.md](docs/deprecations.md)、[docs/script-lifecycle.yml](docs/script-lifecycle.yml)、[docs/quality-coverage-governance.yml](docs/quality-coverage-governance.yml) 和 [docs/maintainability-refactor-roadmap.yml](docs/maintainability-refactor-roadmap.yml)。
