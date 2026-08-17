# 治理文件索引

本工作区把治理做成数据驱动：规则写在机器可校验的 YAML 注册表里，再由脚本自检。本文把分散在 `docs/` 下的治理 YAML 集中导航，方便新接手的人先建立全局认知，再深入单份文件。

每份文件都带 `schema_version`，改动时先读头部说明与现有登记项，再按各自的移除或更新条件操作。修改治理文件后通常要同步对应测试（见各文件引用）。

## 跨仓库契约与边界

工作区级完成状态和优先级见[工作区路线图](roadmap.md)。各机器账本保存字段级事实，
文档之间的归集关系见[文档归集与去重清单](documentation-consolidation.md)。

| 文件 | 用途 | 关联检查 |
| --- | --- | --- |
| `artifact-contracts.yml` | 跨模块产物契约，定义权威运行时实现的归属规则 | `src/research_contracts/`、契约测试 |
| `framework-integration-ledger.yml` | 外部框架集成账本，列明禁止进入跨仓库契约的对象类型 | 导入边界检查 |
| `compatibility-facades.yml` | 兼容性门面登记，追踪待移除的向后兼容层 | `scripts/workspace_governance.py` |

## 废弃与重构

| 文件 | 用途 | 关联检查 |
| --- | --- | --- |
| `deprecations.yml` | 废弃入口登记与预算，记录待跟进的废弃面 | `scripts/workspace_governance.py` |
| `maintainability-refactor-roadmap.yml` | 维护性重构路线图与热点预算（棘轮策略）。债务上限下调需在同一提交完成，上调需独立 owner 决策 | `scripts/maintainability_baseline.py`、维护性门禁 |
| `quality-coverage-governance.yml` | 质量覆盖治理，登记允许的排除项与每文件忽略上限 | 各仓 ruff `per-file-ignores` |

## 脚本与应用生命周期

| 文件 | 用途 | 关联检查 |
| --- | --- | --- |
| `script-lifecycle.yml` | 脚本生命周期登记（dev/ci/release/archive/migration）与移除评审条件 | `scripts/` 下各脚本 |
| `research-app-ownership-ledger.yml` | 研究应用归属账本，定义 owner 边界与身份保留门面规则 | ADR-0003、应用归属测试 |

## 框架适配器与归档

| 文件 | 用途 | 状态 |
| --- | --- | --- |
| `framework-adapter-release.yml` | 可选框架适配器发布门禁与合并前锁定规则 | 历史终止候选，相关候选未在 owner-native `main` 形成可验证发布组合 |
| `hk-private-archive-manifest.yml` | 港股私有 legacy 归档清单，仅恢复用途，带访问控制 | 恢复专用 |
| `hk-public-split-manifest.yml` | 港股公开拆分清单，对应已退役的公开演示路线 | 恢复专用 |

## 阅读建议

先读 `ARCHITECTURE.md` 与 `AGENTS.md` 建立仓库边界认知，再按上表按需查证具体注册表。历史研究与阶段记录不在此列，统一从 `docs/archive/README.md` 进入。

## 语言风格边界

活跃治理文档（本文及 `README`、`AGENTS`、`ARCHITECTURE`、各 `*.md` 治理说明）遵循中文标点、不用双引号与加粗、不用分号与破折号、避免先否定再转折的句式。

`docs/archive/` 下的历史研究笔记与 `artifacts` 下的研究产物是带日期的证据记录，保留写作当时的原貌，不在润色范围。盘点显示先否定再转折的句式集中在这两类文件，活跃文档已基本没有，因此无需对归档内容做批量改写，避免损害研究记录的可追溯性。
