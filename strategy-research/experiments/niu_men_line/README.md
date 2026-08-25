# 牛门线事件研究

这一目录记录牛门线第一阶段的事件研究入口和结果索引。

## 研究边界

第一阶段只研究：

- 指标是否按公式正确计算
- 第一次实体触及 `NML` 后的未来收益
- 指数、行业、波动、成交量、前期涨幅和成本线分组
- 4 个退出变体和 1 个成本线入场过滤

这一阶段不生成生产信号，不连接 AKQuant，也不创建第二套组合回测引擎。

## 计算入口

策略特有入口位于：

~~~text
strategy_app.niu_men_line.indicators
strategy_app.niu_men_line.event_study
~~~

通用指标计算位于：

~~~text
alpha_research.technical
~~~

组合回放应使用 `portfolio_backtester` 的公开接口。

## 输入字段

事件研究至少需要以下字段：

| 字段 | 含义 |
| --- | --- |
| `symbol` | 标的代码 |
| `trade_date` | 交易日 |
| `open` | 开盘价 |
| `high` | 最高价 |
| `low` | 最低价 |
| `close` | 收盘价 |
| `volume` | 成交量 |

如果提供 `amount`，成本线按标的版公式计算。没有 `amount` 时，成本线按 `close × volume` 计算，适用于指数类输入。

可选字段包括：

- `index_regime`
- `industry_regime`
- `industry_id`

## 结果要求

每次运行至少记录：

- 策略规格版本
- 数据快照标识
- 样本起止日期
- 事件数量
- 每个持有期的完整样本数量
- 每个退出变体的退出原因
- 成本和滑点假设
- 尚未完成的验证

没有数据快照时，只能运行合成数据测试，不能把测试结果当作策略证据。
