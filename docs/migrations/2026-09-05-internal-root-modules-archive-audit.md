# internal 策略专属 root modules 归档审计

审计日期：2026-09-05  
来源仓库：`runchengxie/strategy-pipeline-internal`  
来源提交：`44fd1bae16f04f18c7fa5234c9f5f0860ae69ac3`  
冻结 tag：`retirement-freeze-20260905-r1`

## 结论

策略专属 root modules 不属于公共 `strategy-pipeline` 的职责范围。它们包含 DailyWatch20、Hotsector、研究运行和策略配置等私有实现，继续放入公共仓库会扩大策略细节的披露面。

这组模块当前没有 workspace 或 owner 仓库的 active consumer。已有的策略能力迁移记录分别指向 `strategy-app`、`strategy-research` 和相关 owner 仓库。剩余 internal 文件只作为冻结版本的私有恢复参考，状态记为 `archive`。

## 边界与归属

| 范围 | 处理方式 | owner |
| --- | --- | --- |
| 策略信号、策略规则和 DailyWatch20 具体实现 | 保留在私有 owner 仓库，按已有迁移记录维护 | `strategy-app` |
| 研究运行和证据编排 | 使用 owner 仓库中的迁移实现 | `strategy-research`、`alpha-research` |
| internal 中的历史 root-module 文件 | 只读冻结，保留恢复用途 | `strategy-app` |

公共 pipeline 只提供控制面、契约和生命周期能力，不承载这些策略实现。生产 release 已使用公共 pipeline，运行入口不需要 internal checkout、安装包或私有凭证。

## 审计证据

- internal `main` 的 root-module 代码树已按文件核对，来源为冻结提交 `44fd1bae`。
- workspace active producer、安装配置、CI、运行脚本和 owner 迁移记录中没有发现对这些 internal 模块的 active consumer。
- 公共 `strategy-pipeline` 源码树不包含 `strategy_pipeline_internal`。
- workspace production release `e322894a` 已完成 public pipeline cutover，并通过 production contract smoke 和 public pipeline CLI smoke。
- 具体策略能力的 owner、目标路径和回归证据继续以迁移清单中的逐文件记录为准。

## 恢复路径

只有在发现新的 active consumer，或需要复核历史策略结果时，才从私有仓库的 `retirement-freeze-20260905-r1` 恢复这组代码。恢复前需要重新建立 owner、测试、配置和文档证据，并经过 workspace 与 owner 仓库的迁移评审。恢复代码不得直接进入公共 pipeline。

本记录不表示删除 internal。正式下线前仍需完成只读归档、恢复演练，以及连续两个维护周期的无消费者确认。
