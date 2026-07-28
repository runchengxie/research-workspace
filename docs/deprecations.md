# 废弃入口登记

本页记录废弃兼容入口的删除状态。登记记录本身不授权删除。删除前必须满足 [`deprecations.yml`](deprecations.yml) 中的证据要求，并通过 [`hk-public-split-manifest.yml`](hk-public-split-manifest.yml) 中的拆分门禁。

## 当前记录

| 入口 | 负责仓库 | 替代入口 | 状态 | 目标里程碑 |
| --- | --- | --- | --- | --- |
| `hkdata` | `market-data-platform` | `marketdata` | removed | completed 2026-06-13 |
| `src/hk_data_platform/*` | `market-data-platform` | `market_data_platform` public modules | removed | completed 2026-06-13 |
| `rqdata-hk-depth` | `market-data-platform` | `marketdata migration hydrate-hk` + 恢复专用归档 | removed | completed 2026-06-13 |
| `rqdata-tick` | `market-data-platform` | `marketdata migration hydrate-hk` + 恢复专用归档 | removed | completed 2026-06-13 |
| `rqdata-hk-assets` | `market-data-platform` | `marketdata migration hydrate-hk` + 恢复专用归档 | removed | completed 2026-06-13 |
| 历史港股调仓命令行（CLI） | `strategy-pipeline` | `strategy alloc` 加 `strategy export-targets` | removed | 命令行与 `alloc_hk` 模块已于 2026-06-13 删除 |
| 港股历史实验配置 | `strategy-pipeline` | `docs/archive/research/hk/configs/experiments` + 恢复专用归档 | removed | 活跃实验配置已于 2026-06-13 归档 |
| 旧共享 Python 命名空间、CLI 与环境变量 兜底 | `strategy-pipeline` | `strategy_pipeline.*`、`alpha_research.*`、`portfolio_backtester.*`、`strategy` | removed | removed in workspace 2.0 on 2026-07-14 |

## 删除门禁

只有下列证据齐全后，才能把废弃入口标记为可进入删除评审：

- 下游或仓库内使用审计。
- 替代入口文档。
- 回滚路径。
- 负责仓库中的针对性测试。
- 涉及恢复的敏感入口需要恢复证据。

实际删除必须在负责仓库内做针对性核验，并把结果写回本页和 YAML 清单。2026-06-13 的清理已把港股数据提供方生产命令、历史港股调仓命令行、`alloc_hk` 模块、港股研究实现模块和活跃港股实验配置移出活跃区。需要复现时从冻结标签或恢复专用归档恢复。

框架替换产生的兼容门面还必须满足以下条件：

- 在 [`compatibility-facades.yml`](compatibility-facades.yml) 登记负责方、替代入口和移除版本。
- 原生与替代后端的差分夹具已通过，行为差异有明确分类。
- 第三方框架关闭或卸载后，回滚路径仍可运行。
- 删除不会把 Qlib、vn.py 或 LEAN 类型提升为跨仓库契约。
- 对应工作流已在 [`framework-integration-ledger.yml`](framework-integration-ledger.yml) 达到退出条件。

早期私有旧版归档暂存本身不授权删除。本页的 removed 状态必须同时引用恢复演练、下游消费审计、来源标签、针对性核验和删除审计证据。删除评审前后都可运行 `python scripts/hk_archive_gate.py --check --format json`，并保留 [archive/hk/README.md](archive/hk/README.md) 链接到的恢复路径。

## Owner-native 命名空间兼容

旧兼容面已从 `strategy-pipeline` 删除。alpha 和 portfolio 子仓库（发布侧）
不得重新安装共享命名空间。删除门禁除通用要求外，还必须覆盖 pickle/joblib 类路径、
配置点分路径、日志命名空间、外部 notebook 与命令行下游消费审计。
