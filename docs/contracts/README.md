# 跨仓契约

> status: active
> owner: workspace
> audience: human and agent
> last_verified: 2026-09-06
> source_of_truth: yes
> superseded_by: n/a

本目录说明跨仓库数据、研究产物、目标文件和路径约定。

- [跨仓库文件契约](../contracts.md)
- [数据质量契约](../data-quality-contracts.md)
- [数据生命周期术语](../data-lifecycle-terminology.md)
- [数据路径迁移映射](../data-path-migration-map.md)
- [数据路径重大变更登记](../data-path-breaking-change-register.md)
- [产物契约机器清单](../artifact-contracts.yml)
- [跨仓契约 ownership registry](contract-ownership.yml)

`contract-ownership.yml` 登记跨仓交接的唯一 producer、直接 consumers、版本兼容策略、最小测试和
回滚方式。`artifact-contracts.yml` 继续维护文件 artifact 的字段与入口明细。两份 registry 的
重叠项由 `research_contracts` smoke 检查防止 schema、producer 和 consumers 漂移。
