# ADR-0004：独立 research-apps 仓库与收尾迁移栈

- 状态：proposed
- 日期：2026-07-18
- 修订：ADR-0003

## 背景

`research_apps` 已从“可抽取的内嵌 Python 包”进入独立私有仓库。仍未决定未来采用多仓、monorepo 或公开镜像，但仓库是否合并不能继续阻塞剩余 owner 边界。

## 决策

1. `runchengxie/research-apps` 成为研究应用的权威发行仓库。
2. `market_data_platform` 提供分钟源目录、overlay 完整性、缓存分区指纹、输入可用性和 universe policy。
3. `alpha_research` 提供分钟 transform/evidence 和 alpha policy。
4. `portfolio_backtester` 提供 staggered cash/carry 状态机、受阻交易会计、终态口径和 public execution summary。
5. `research_apps` 组合上述 owner API，拥有 F-lite、slow-volume 与 DeepSeek V4 研究 runner；runner 返回普通 frames/report，不进行最终发布。
6. `strategy_pipeline` 保留 provider 调用、操作员控制、原子发布、receipt、release gate 与 target handoff。
7. `strategy_pipeline` wheel 不再打包内嵌 `research_apps`。源码 checkout 暂时保留 standalone-first/local-fallback 的兼容窗口，直到剩余历史 public module 被迁出或正式退役。

## 合并顺序

1. market-data-platform #11
2. alpha-research #12
3. portfolio-backtester #14
4. research-apps #1
5. 更新 lockfile 并运行最新组合验证
6. strategy-pipeline #27
7. 更新本仓 pin 并运行 smoke/full profile

## 验证门禁

所有 PR 在以下条件完成前保持 draft：

- owner 版本与 lockfile 一致；
- 四个 owner/应用分支在同一环境安装成功；
- 最新 pytest、Ruff、format、type check 通过；
- fresh wheel 包含 content-addressed campaign specs；
- workspace smoke/full profile 通过。

当前 workflow 缺失、禁用或 `action_required` 均不得解释为测试通过。软件已经有足够多的民间传说，不再增加 CI 神话。
