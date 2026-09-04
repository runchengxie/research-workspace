# strategy-pipeline-internal 退役记录

> status: pre-retirement-baseline
> owner: research-workspace
> audit_date: 2026-09-05

本记录建立 internal 冻结后的第 0 个维护周期基线。它记录当前证据和未完成事项，不能替代正式下线评审。

## 冻结与版本

| 项目 | 值 |
| --- | --- |
| 冻结日期 | 2026-09-05 |
| internal 最后可用提交 | `a7513976ca19bb097c18dc7b33ceb1cf4ff5e0a7` |
| internal 冻结 tag | `retirement-freeze-20260905`，指向 `a7513976ca19bb097c18dc7b33ceb1cf4ff5e0a7` |
| production workspace release | `cbfc754d85a42d6cf916bb69f5b09f841cbf2f26` |
| production public pipeline | `5f7f8681608019987d995ed1ae8602468c1c0d32` |
| production 回滚点 | `9b50e2ef9a533faad624b1f7e525ccc174ccbfe7` |
| 迁移候选版本组合 | `e29e1887`，见 `docs/version-matrix.md` |

## 当前审计结果

- production 入口不需要 internal checkout、安装包或私有凭证。
- workspace 的 active producer、安装配置、CI 和运行脚本没有把 internal 作为入口。
- strategy-research 已记录 internal runner 路径为 archive-only，active external consumer 为 0。
- owner 仓库中的历史来源标记、schema 身份和迁移清单引用继续保留，用于溯源和兼容读取。
- public `strategy-pipeline` 的源码树不包含 `strategy_pipeline_internal`。

## 仍未完成的事项

1. internal 中的兼容 facade、CLI、commands、release tools 和剩余编排文件仍需逐项完成 owner 证据。
2. internal 的完整类型检查仍有历史诊断，需要在最终退役前决定修复、归档或记录豁免。
3. 迁移候选版本组合尚未替换 production release，需完成 workspace 全量回归和生产 smoke 后再提升。
4. 维护周期计数为 0/2。连续两个周期均确认无 active consumer 后，才能进入正式下线评审。

## 2026-09-05 production readiness audit

本轮基于 workspace `github/main` 的 `0724d9414c972cfab9c576c63bad68bb8c1b3289` 执行检查：

- `check-production-updates.sh` 已确认 workspace 有待提升版本，market-intel 无待提升版本。
- `promote-production.sh --dry-run` 已完成版本解析和 submodule 计划生成，没有切换 `current`。
- workspace 迁移、生产维护和 release 管理相关测试共 51 项通过。
- 生产维护测试中另有 1 项因主机剩余空间约 4.0 GiB 低于脚本要求的 5.0 GiB 而停止。这是主机容量门禁，不能视为代码回归通过。
- owner 仓库的完整回归尚未在本轮审计中完成，因此候选版本组合仍不能提升为 production release。

本轮结论：公共 pipeline 已具备当前 production release 所需的独立运行条件，workspace 仍需在容量门禁满足后完成 owner 全量回归、正式 promotion、生产 dry-run 与 smoke，随后才能开始两个维护周期的 internal 退役观察。

## 下次审计要求

下次审计需要重新运行 workspace、public pipeline 和各 owner 的完整门禁，检查生产入口、安装依赖、CI、配置、active 文档和消费者搜索，并把结果追加到本记录。若发现新的 active consumer，维护周期计数归零。

正式下线前还需要创建冻结 tag、只读归档和恢复演练记录，并由 workspace 与 internal 的最终退役 PR 分别完成合并。
