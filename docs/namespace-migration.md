# Owner-native 命名空间迁移

## 权威入口

| Distribution | Python package | CLI |
| --- | --- | --- |
| `alpha-research` | `alpha_research.*` | n/a |
| `portfolio-backtester` | `portfolio_backtester.*` | n/a |
| `strategy-pipeline` | `strategy_pipeline.*` | `strategy`, `strategy-pipeline` |

`cstree` 只由 `strategy-pipeline` 提供 1.x 兼容 facade。它不再是共享 namespace，
也不再承载业务实现。兼容面计划在工作区 2.0 删除。

## 合并顺序

1. 合并 alpha-research PR #6；
2. 合并 portfolio-backtester PR #8；
3. 合并 strategy-pipeline PR #20；
4. 更新并验证本 superproject PR 的 gitlinks；
5. 发布 0.2.0 / 0.2.0 / 1.1.0 组合。

## 删除门槛

删除旧 facade 前必须完成 import、CLI、环境变量、日志过滤、配置 dotted path、pickle/joblib
类路径和外部 notebook 的 consumer audit，并保留可执行回滚说明。
