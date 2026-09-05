# strategy-pipeline-internal 退役记录

> status: retired
> owner: research-workspace
> audit_date: 2026-09-05

本记录已完成 internal 冻结后的第 2 个维护周期记录和最终下线动作。internal 已进入私有只读归档状态。

## 冻结与版本

| 项目 | 值 |
| --- | --- |
| 冻结日期 | 2026-09-05 |
| internal 最后可用提交 | `44fd1bae16f04f18c7fa5234c9f5f0860ae69ac3` |
| internal 最终退役提交 | `decd1b43b31c63fbb47a129fb872a93838a1cd36` |
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

## 退役结论

1. 各模块组的迁移或归档判断已经完成。策略专属 root modules 保留在私有 owner 和冻结的 internal 恢复参考中，不进入公共 pipeline。公共控制面 facade 已在 internal PR #297 中删除，CLI、release tools、研究 commands、pipeline 和 liveops 已完成 archive-only 审计。
2. 维护周期计数为 2/2。两个连续周期均没有发现 active consumer。
3. internal 最终退役 PR #298 已合并，GitHub 仓库已保持私有并进入 archived 状态。

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

## 2026-09-05 closeout consistency audit

本地工作区复核发现，记录中的 production workspace release `e322894a3d530959314dbd1a97eb9722f40b53da` 当前未出现在本机 `production/research-workspace/releases/`，而 `production/research-workspace/current` 实际指向 `deb89a3bd17c7c479fac35e8d844016bdbbec915`。复核时 `github/main` 为 `c2bb62ffd33fde0224e8871ede004953e80fb809`，可作为下一次 promotion 候选。因此本记录保留历史 promotion 声明。生产指针一致性列为独立 promotion follow-up。在完成授权 promotion 前，不把本地生产状态视为已与记录一致。

## 2026-09-05 production promotion resolution

已将 closeout 变更合并到 `github/main` 并完成正式 promotion。当前 `production/research-workspace/current`、promotion manifest、release 根目录和 submodule gitlink 校验通过，公共 `strategy-pipeline` gitlink 为 `5f7f8681608019987d995ed1ae8602468c1c0d32`。此前 closeout consistency audit 中记录的生产指针不一致已解决。生产 commit 不再复制进同一份 evidence JSON，避免 evidence 修改造成自引用 hash 失效。runtime pointer 和 promotion manifest 是生产版本的权威来源。

## 2026-09-05 maintenance cycle 1 audit

本周期重新核对了冻结版本、公共仓库和 production gitlink，并完成恢复演练：

- `retirement-freeze-20260905-r1` 解压到临时目录成功，README 和 `src/strategy_pipeline_internal` 目录均存在。
- 冻结归档 tar 的 SHA-256 为 `c2e412b85c34dc354668bf62db97f3fca43c045f3f7ffae943ad7a9b5315d17d`。
- workspace active import 扫描为 0，public pipeline active import 扫描为 0。
- workspace 中剩余的 2 处 internal 字符串只用于 import 边界拒绝规则和历史 artifact registry，不构成 active consumer。
- public `strategy-pipeline` clean-room 安装通过，55 项测试通过。
- production release `e322894a` 的 `strategy-pipeline` gitlink 仍为 public 提交 `5f7f868`。

详细机器可读证据见[maintenance cycle 1 evidence](../evidence/strategy-pipeline-internal-retirement-cycle-1-20260905.json)。

## 2026-09-05 maintenance cycle 2 audit

第 2 个维护周期重新执行了 public clean-room、active consumer 和冻结归档恢复检查：

- public `strategy-pipeline` 从 GitHub main 的 `5f7f868` 全新克隆，`uv sync --locked --all-groups` 通过。
- public pipeline 测试 55 项通过，active internal import 扫描为 0。
- workspace remote main 的 active internal import 扫描为 0，剩余 2 处字符串仍是边界拒绝规则和历史 artifact registry。
- production release `e322894a` 的 `strategy-pipeline` gitlink 仍为 `5f7f868`。
- `retirement-freeze-20260905-r1` 归档再次解压成功，README 和 internal 源码目录均存在，归档 tar SHA-256 未变化。
- 本周期审计结束时 internal 仍为私有、未归档状态，随后已完成最终退役 PR 和只读归档。

详细机器可读证据见[maintenance cycle 2 evidence](../evidence/strategy-pipeline-internal-retirement-cycle-2-20260905.json)。

release tools 的 archive-only 结论和恢复要求见[release tools 归档审计](2026-09-05-internal-release-tools-archive-audit.md)。

研究 commands 的 archive-only 结论和恢复要求见[研究命令归档审计](2026-09-05-internal-research-commands-archive-audit.md)。

internal CLI 的 archive-only 结论和恢复要求见[CLI 归档审计](2026-09-05-internal-cli-archive-audit.md)。

pipeline 和 liveops 的 archive-only 结论和恢复要求见[runtime 归档审计](2026-09-05-internal-runtime-archive-audit.md)。

策略专属 root modules 的私有归档边界、owner 和恢复要求见[root modules 归档审计](2026-09-05-internal-root-modules-archive-audit.md)。

internal 类型检查的 15 个历史诊断已完成分类并记录为归档豁免，详见[类型检查审计](2026-09-05-internal-typecheck-audit.md)。该豁免不影响 production release，也不改变 internal 冻结状态。

## 退役后的维护规则

日常维护不再修改 internal。需要历史复核时，只能从冻结 tag 恢复，并记录恢复原因、使用范围和结果。若出现新的 active 需求，应在对应 owner 仓库建立新的实现、测试、配置和文档证据，不能重新启用 internal 作为 workspace 运行入口。

正式退役动作已完成：internal 最终退役 PR 已合并，GitHub 仓库已确认保持私有并进入 archived 状态。冻结 tag 和本记录继续作为恢复入口。原冻结 tag 保留作为历史基线，`retirement-freeze-20260905-r1` 覆盖最后一次公共 facade 退役。

最终归档证据见[internal retirement final evidence](../evidence/strategy-pipeline-internal-retirement-final-20260905.json)。
