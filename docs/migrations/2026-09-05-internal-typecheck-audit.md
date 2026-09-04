# internal 类型检查审计

## 审计范围

审计对象是 `strategy-pipeline-internal` 冻结提交
`a7513976ca19bb097c18dc7b33ceb1cf4ff5e0a7`。执行了：

```bash
scripts/dev/run_tests.sh typecheck
scripts/dev/run_tests.sh typecheck-all-report
```

## 结果

阻断型 `typecheck` 报告 15 个诊断。完整报告命令按设计只报告问题，因此退出码为 0。

| 类型 | 数量 | 处理决定 |
| --- | ---: | --- |
| `unresolved-import` | 4 | 归档。涉及冻结仓库内已经迁移或不再作为生产入口的模块引用。 |
| `not-subscriptable` | 7 | 归档。涉及迁移清单、控制面归属和文档证据测试的动态 JSON 类型推断。 |
| `call-non-callable` | 1 | 归档。涉及已迁移输出元数据 writer 的历史测试替身。 |
| `invalid-argument-type` | 1 | 归档。涉及冻结 liveops 历史测试传入的 pandas 时间值。 |
| `unresolved-attribute` | 1 | 归档。涉及冻结迁移清单测试的动态对象读取。 |
| `not-iterable` | 1 | 归档。涉及冻结文档归属测试的动态证据字段。 |

## 退役决策

internal 已冻结，不再接收新功能、策略逻辑或新的生产依赖。production release、workspace active producer 和 owner 仓库均不依赖这 15 个诊断涉及的运行入口。

因此本轮不修改冻结仓库来追求类型门禁全绿，也不把这些诊断迁移到公共
`strategy-pipeline`。它们作为 internal 历史复核和归档恢复的已知限制保留，正式退役时随冻结 tag 一并归档。若未来需要恢复某个历史入口，应先建立独立恢复分支并重新评估对应诊断。
