# 架构决策记录

本目录保存跨仓库且需要长期遵守的架构决策。实现细节仍由各子仓库维护，顶层工作区只记录边界、迁移条件和回滚规则。

| 编号 | 决策 | 状态 |
| --- | --- | --- |
| [ADR-0001](0001-framework-integration-boundaries.md) | Qlib、vn.py 与 LEAN 的集成边界 | accepted |
| [ADR-0002](0002-owner-native-python-namespaces.md) | 采用 owner-native Python 命名空间 | accepted |
| [ADR-0003](0003-research-application-ownership.md) | 研究应用归属与仓库布局解耦 | superseded by ADR-0004 |
| [ADR-0004](0004-standalone-research-apps-repository.md) | 独立 `research-apps` 仓库与收尾迁移栈 | accepted |
| [ADR-0005](0005-qlib-alpha-research-backends.md) | Qlib 预处理管线引入 alpha-research 训练后端 | accepted |
| [ADR-0006](0006-strategy-knowledge-and-runtime-boundaries.md) | 策略知识、可执行应用与运行控制面分离 | accepted |
