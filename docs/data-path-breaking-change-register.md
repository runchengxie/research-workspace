# 数据路径 breaking change 登记

## 当前结论

以下目录虽然没有完全采用生命周期名称，但已经被脚本和日报当作稳定接口使用。它们不是可以
直接整体改名的普通旧目录：

| 当前接口 | 主要消费者 | 当前处理 | 是否允许直接改名 |
| --- | --- | --- | --- |
| `strategy_outputs/watchlist20/` | `market-intel` 日报、DailyWatch20 校验和投递 | 保留原入口，内部使用 `runs/`、`research/`、`features/`、`latest` | 否 |
| `strategy_outputs/d11_h5_shadow/` | 影子策略生产、状态恢复和日报交付 | 保留原入口，内部使用 `state/`、`runs/`、`latest` | 否 |
| `strategy_inputs/watchlist20/news_heat/` | DailyWatch20 生产和候选池构建 | 保留原入口，内部使用 `runs/`、`latest` | 否 |
| `artifacts/assets/benchmark/csi300_daily_return.parquet` | `strategy-research` Qlib 实验配置 | 已迁入 `published/benchmarks/`，旧路径保留 symlink | 已完成兼容迁移 |

这里的 `strategy_outputs` 和 `strategy_inputs` 是业务域命名空间，不再把它们视为生命周期
层。生命周期语义由内部的 `runs/`、`features/`、`state/`、`latest`、receipt 和 manifest
表达。这样做不会为了改名破坏日报接口。

## 已完成的兼容迁移

`artifacts/assets/benchmark/csi300_daily_return.parquet` 已移动到：

```text
published/benchmarks/csi300_daily_return.parquet
```

旧路径仍然是相对 symlink，所有现有配置继续可用。SHA-256、文件大小和可读性已在迁移回执
中记录：

```text
metadata/lifecycle/migrations/artifacts-assets-to-published-benchmark-20260831.json
```

## 三类生产接口的迁移流程

如果未来要把三类业务接口迁到新的物理根目录，必须按以下阶段推进：

1. 在生产方和消费方增加可配置的新路径，默认仍使用旧路径；
2. 新旧路径同时做存在性、receipt、版本和内容哈希检查；
3. 在一个完整日报周期内使用新路径做 shadow read，只记录差异，不切换发送结果；
4. 通过 clean-check、数据契约测试和日报 dry-run 后，原子切换 `current` 或新的稳定 alias；
5. 至少观察两个完整运行周期，确认无旧路径读取后再把旧路径标为 deprecated；
6. 再经过一次 retention 复核，才允许删除旧目录或兼容 alias。

## 当前不执行的动作

- 不把 `strategy_outputs/watchlist20/` 整体移动到 `published/`；
- 不把 `strategy_outputs/d11_h5_shadow/` 整体移动到 `experiments/`；
- 不把 `strategy_inputs/watchlist20/` 整体移动到 `features/`；
- 不删除旧路径、`latest` alias 或任何日报 receipt。

原因是当前 production `market-intel` release 仍直接读取这些路径。它们的 breaking change
需要跨仓库代码变更和 production promotion，不能只在数据目录层完成。
