# strategy-pipeline-internal 退役记录

> status: pre-retirement-baseline
> owner: research-workspace
> audit_date: 2026-09-05

本记录建立 internal 冻结后的第 0 个维护周期基线。它记录当前证据和未完成事项，不能替代正式下线评审。

## 冻结与版本

| 项目 | 值 |
| --- | --- |
| 冻结日期 | 2026-09-05 |
| internal 最后可用提交 | `44fd1bae16f04f18c7fa5234c9f5f0860ae69ac3` |
| internal 冻结 tag | `retirement-freeze-20260905-r1`，指向 `44fd1bae16f04f18c7fa5234c9f5f0860ae69ac3` |
| production workspace release | `e322894a3d530959314dbd1a97eb9722f40b53da` |
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

1. internal 中剩余的 CLI 和研究编排文件仍需逐项完成 owner 证据。公共控制面 facade 已在 internal PR #297 中删除，release tools 与研究 commands 已完成 archive-only 审计。
2. 维护周期计数为 0/2。连续两个周期均确认无 active consumer 后，才能进入正式下线评审。

## 2026-09-05 production readiness audit

本轮基于 workspace `github/main` 的 `e322894a3d530959314dbd1a97eb9722f40b53da` 执行检查：

- `check-production-updates.sh` 已确认 workspace 有待提升版本，market-intel 无待提升版本。
- `promote-production.sh --dry-run` 已完成版本解析和 submodule 计划生成。
- `promote-production.sh` 已完成正式 promotion，`current` 已切换到 `e322894a3d530959314dbd1a97eb9722f40b53da`。
- workspace 迁移、生产维护和 release 管理相关测试共 51 项通过。
- production release 根目录 clean，8 个 submodule 均已初始化并与 release 中的 gitlink 一致。
- workspace doctor 结果为 0 errors、3 个既有 warning，contract smoke 结果为 0 errors、0 warnings。
- public pipeline CLI smoke 已通过。
- 首次测试曾因主机剩余空间低于 5 GiB 触发门禁，随后空间恢复到约 454 GiB，正式 promotion 已成功完成。

本轮结论：公共 pipeline 已完成 production cutover，并在无 internal checkout、安装包或私有凭证的 production release 中通过运行时检查。internal PR #297 已删除 5 个公共控制面兼容 facade。下一阶段集中处理 internal 剩余 owner 证据和两个维护周期的退役观察。

release tools 的 archive-only 结论和恢复要求见[release tools 归档审计](2026-09-05-internal-release-tools-archive-audit.md)。

研究 commands 的 archive-only 结论和恢复要求见[研究命令归档审计](2026-09-05-internal-research-commands-archive-audit.md)。

internal 类型检查的 15 个历史诊断已完成分类并记录为归档豁免，详见[类型检查审计](2026-09-05-internal-typecheck-audit.md)。该豁免不影响 production release，也不改变 internal 冻结状态。

## 下次审计要求

下次审计需要重新运行 workspace、public pipeline 和各 owner 的完整门禁，检查生产入口、安装依赖、CI、配置、active 文档和消费者搜索，并把结果追加到本记录。若发现新的 active consumer，维护周期计数归零。

正式下线前还需要完成只读归档和恢复演练记录，并由 workspace 与 internal 的最终退役 PR 分别完成合并。原冻结 tag 保留作为历史基线，`retirement-freeze-20260905-r1` 覆盖最后一次公共 facade 退役。
