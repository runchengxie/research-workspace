# ADR-0002：采用 owner-native Python 命名空间

- 状态：accepted / workspace 2.0 cleanup completed
- 日期：2026-07-14
- 范围：`research-workspace`、`alpha-research`、`portfolio-backtester`、`strategy-pipeline`
- 发布清单：[`../owner-native-namespace-release.json`](../owner-native-namespace-release.json)

## 背景

历史上的 `cstree` 同时表示项目品牌、CLI 和三个 distribution 拼接的 Python
namespace。平台开始采用 Qlib、LEAN 和 vn.py 的可替换集成边界后，这个名称既错误暗示
单一截面树模型，也让物理拆仓继续以共享包形式耦合。

## 决策

- `alpha-research` 独占 `alpha_research.*`。
- `portfolio-backtester` 独占 `portfolio_backtester.*`。
- `strategy-pipeline` 独占 `strategy_pipeline.*`。
- 三个 distribution 不再使用 `pkgutil.extend_path`，也不再共同贡献 Python package。
- `strategy-pipeline` 在 1.x 内集中提供唯一的旧 Python facade 和 CLI alias；工作区 2.0
  已删除该兼容面。
- `strategy` 与 `strategy-pipeline` 是权威 CLI；`STRATEGY_PIPELINE_*` 是权威环境变量前缀。
- 旧 Python namespace、CLI alias 和 `CSTREE_*` fallback 在工作区 2.0 删除。

## 不变量

1. 三个仓库均不得重新引入旧共享 Python package。
2. strategy 仓库只发布 `strategy` 与 `strategy-pipeline` 两个 console script。
3. 跨仓库 API 使用 owner-native package；artifact contract 不携带第三方 runtime type。
4. 新代码、adapter、测试、文档和配置不得增加旧 namespace 依赖。
5. superproject 在下游提交验证完成后才更新 gitlinks。

## 后果

这是一组协调的 breaking migration。1.x compatibility facade 曾用于降低现有脚本的迁移峰值，
但不再充当实现所有者。工作区 2.0 已完成 consumer audit、替代入口文档、focused tests、
回滚说明和序列化对象审计；需要兼容旧入口时应回退到 1.x release tag。
