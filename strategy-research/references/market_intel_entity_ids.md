# market-intel 稳定 entity_id 引用说明

本仓（research-workspace）在热点板块策略中只消费 `market-intel`（即 `market-data-platform` submodule）发布的稳定 `entity_id`，不另存或推断产业拓扑关系。

## 权威来源

- 产业链与行业分类的权威定义在 `market-data-platform` 内维护，包括 SW2021 行业口径与对应实体标识。
- 数据契约与实体口径以 `market-data-platform/docs/contracts.md` 与 `market-data-platform/src` 内的数据模型为准。

## 本仓约定

- 热点板块策略代码与实验脚本通过 `entity_id` 引用标的，不本地维护产业上下游拓扑。
- 若需要新的产业关系维度，应在 `market-intel` 侧扩展并发布新版本化 `entity_id`，本仓随之升级引用，而非在仓内重建关系表。
- 禁止在本仓伪造或推测 `entity_id` 之间的产业链归属，所有引用须可追溯到 `market-intel` 的已发布实体。
