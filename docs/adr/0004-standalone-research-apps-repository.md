# ADR-0004：独立 research-apps 仓库与收尾迁移栈

- 状态：accepted（已实现）
- 日期：2026-07-18
- 修订：ADR-0003

## 背景

`research_apps` 已从“可抽取的内嵌 Python 包”进入独立仓库。工作区继续采用带锁定
gitlink 的多仓组合；未来是否增加公开镜像不影响当前 owner 边界。

## 决策

1. `runchengxie/research-apps` 成为研究应用的权威发行仓库。
2. `market_data_platform` 提供分钟源目录、overlay 完整性、缓存分区指纹、输入可用性和 universe policy。
3. `alpha_research` 提供分钟 transform/evidence 和 alpha policy。
4. `portfolio_backtester` 提供 staggered cash/carry 状态机、受阻交易会计、终态口径和 public execution summary。
5. `research_apps` 组合上述 owner API，拥有 F-lite、slow-volume 与 DeepSeek V4 研究 runner；runner 返回普通 frames/report，不进行最终发布。
6. `strategy_pipeline` 保留 provider 调用、操作员控制、原子发布、receipt、release gate 与 target handoff。
7. `strategy_pipeline` wheel 和源码 checkout 均不再包含内嵌 `research_apps`；历史
   `strategy_pipeline.*` public module 仅保留直接委派 owner API 的薄兼容 facade，并由
   `docs/compatibility-facades.yml` 单独管理退役条件。

## 已执行合并顺序

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

## 实施结果

2026-07-19 已按上述顺序合并 owner PR，并将六个子模块固定到各自 `main`。Strategy 删除
内嵌 `research_apps` 源码，只保留登记过的 owner-delegating public facade。最终本地验证包括
176 个 superproject 测试、36 条 delegated full-profile 命令、research-apps 的 54 模块和
4 资源 wheel smoke，以及 Strategy 的 206 模块隔离安装 smoke。所有仓库的 GitHub Actions
权限保持禁用，权威检查由共享 pre-push 调度。
