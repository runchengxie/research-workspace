# 每日飞书 10 股回测输入盘点

盘点日期：2026-09-09

## 当前结论

当前仓库中已经存在 `Weekly Client Basket 10` 的设计和实现。它是一个组合编排层，从 DailyWatch family、Cashflow 和 Microcap 的最近一次有效 artifact 组成 10 只股票快照，并输出 `NEW / KEEP / DROP` 差分；它不是新的 alpha 选股策略。

因此，本次回测必须评价最终生成并推进到飞书的 10 股快照，不能直接把 Cashflow Top50、DailyWatch20 或 D11-H5 的单独回测结果当作 10 股组合结果。

当前状态：`blocked_pending_runtime_artifacts`

## 已确认的契约

- 设计规格：`/home/richard/code/quant/quant-intel-platform/docs/superpowers/specs/2026-09-09-weekly-client-basket-10-design.md`
- 实现入口：`/home/richard/code/quant/quant-intel-platform/src/a_share_daily/weekly_client_basket.py`
- 渲染入口：`/home/richard/code/quant/quant-intel-platform/src/a_share_daily/weekly_client_basket_render.py`
- 投递入口：`/home/richard/code/quant/quant-intel-platform/src/a_share_daily/weekly_client_basket_delivery.py`
- CLI：`a-share-daily weekly-basket`
- 设计口径：每周第一个交易日生成并在本周冻结，默认来源配额为 DailyWatch family 4、Cashflow 3、Microcap 3。
- 缺少输入、过期、hash 不匹配、候选不足时必须 fail closed。
- Cashflow 和 Microcap 仍然是 research/shadow 证据，不能被解释为生产资格。

## 只读扫描结果

在以下位置扫描了 JSON/CSV/Markdown/receipt 文件：

- `/home/richard/code/quant/quant-intel-platform/out`
- `/home/richard/code/production`
- `/home/richard/code/research-workspace/market-intel/state`
- `/home/richard/code/research-workspace/market-intel/out`

已发现历史 DailyWatch20、D11-H5 和旧 AI stock picker 投递回执，但没有发现 `weekly_client_basket/YYYYMMDD/{basket.json,receipt.json}` 或等价的最终 10 股快照产物。

当前 `quant-intel-platform/out` 中可见的 `weekly` 相关文件只有 `weekly_recap.meta.json`，不属于 10 股组合快照。

用户配置目录 `/home/richard/.config/market-intel` 中没有发现独立的 `cashflow-shadow.env`；因此无法从当前配置推导 Cashflow shadow 的外部输出根目录。配置文件中存在 API/市场数据相关文件，但本盘点不读取凭证内容。

## 回测所需最小输入

要把状态改为 `ready_for_gray_replay`，至少需要：

1. 每个实际推进日的 canonical `basket.json`，包括 symbol、权重、source strategy、signal date、valid until、artifact hash。
2. 对应的组合 `receipt.json`，证明输入 artifact 和最终 basket hash 未被替换。
3. 如需评价“实际发到飞书”，还需要对应 delivery receipt；它用于确认投递状态，但不替代 basket canonical artifact。
4. 从每个生效日开始的权威行情数据，至少包含前复权或明确调整口径的 open/close，以及停牌、涨跌停和缺失状态。
5. 基准日收益和成本假设。主口径固定为信号日收盘后、下一交易日开盘执行；不得使用同日收益作为主结果。

## 当前行动

在真实 basket artifact 被定位或补齐前，不生成收益结论。下一步应检查生产运行目录、定时任务环境文件和外部 artifact 根目录；如果确认没有保存历史 10 股快照，则先补一个从当前运行起点开始的不可变回测归档，再等待足够的前向观测样本。
