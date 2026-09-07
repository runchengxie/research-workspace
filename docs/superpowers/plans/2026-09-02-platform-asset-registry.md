# 平台资产注册表实施计划

> **面向智能体执行者：**必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项执行本计划。步骤使用复选框跟踪。

**目标：**增加机器可读的逻辑平台依赖图，不改变 Git 仓库嵌套关系。

**规格：**`docs/superpowers/specs/2026-09-02-platform-asset-registry-design.md`

- [x] 为代表性研究流程、缺失依赖、循环和无效新鲜度策略增加测试。
- [ ] 运行针对性测试，在实现前确认 RED 状态。
- [x] 实现带图校验和拓扑排序的 `PlatformAssetDefinition` 与 `PlatformAssetRegistry`。
- [x] 记录逻辑资产图与 Git 顶层仓库或编排器之间的区别。
- [ ] 运行 `uv run --project strategy-pipeline --extra dev python -m pytest tests/test_platform_asset_registry.py -q`。
- [ ] 运行工作区 hard 和 smoke 契约门禁。
