# Owner-native 命名空间迁移

## 权威入口

| Distribution | Python package | CLI |
| --- | --- | --- |
| `alpha-research` | `alpha_research.*` | n/a |
| `portfolio-backtester` | `portfolio_backtester.*` | n/a |
| `strategy-pipeline` | `strategy_pipeline.*` | `strategy`, `strategy-pipeline` |

工作区 2.0 已删除旧共享 namespace、兼容 CLI 和环境变量 fallback。所有活跃调用必须直接使用
上表列出的 owner-native package 与 `strategy` / `strategy-pipeline` CLI。

## 历史 1.x 合并顺序

1. 合并 alpha-research PR #6。
2. 合并 portfolio-backtester PR #8。
3. 合并 strategy-pipeline PR #20。
4. 更新并验证本 superproject PR 的 gitlinks。
5. 发布 0.2.0 / 0.2.0 / 1.1.0 兼容组合。

该顺序记录 1.x 过渡过程。工作区 2.0 在此基础上完成 breaking cleanup。各子仓库的
2.0 变更和 superproject gitlink 应作为同一组协调发布提交合并。

## 2.0 删除结果

repo-local import、CLI、环境变量、日志过滤、配置 dotted path 和序列化类路径均已迁到
owner-native 名称。旧 artifact 原样保留用于 provenance 与离线审计，但 2.0 reader 不承诺接受
旧 contract identity。需要复现时使用 1.x release tag 或一次性迁移工具。新的 producer 只写
owner-native contract 名称，2.0 主线不保留双入口。
