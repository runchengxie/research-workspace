# 每日飞书 10 股回测输入盘点

盘点日期：2026-09-09

## 当前结论

当前仓库中已经存在 `Weekly Client Basket 10` 的设计和实现。它是一个组合编排层，从 DailyWatch family、Cashflow 和 Microcap 的最近一次有效 artifact 组成 10 只股票快照，并输出 `NEW / KEEP / DROP` 差分；它不是新的 alpha 选股策略。

因此，本次回测必须评价最终生成并推进到飞书的 10 股快照，不能直接把 Cashflow Top50、DailyWatch20 或 D11-H5 的单独回测结果当作 10 股组合结果。

当前状态：`ready_for_forward_observation_not_historical_replay`

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
- `/home/richard/data/quant`

已发现历史 DailyWatch20、D11-H5 和旧 AI stock picker 投递回执，以及 Cashflow 研究回放和 Cashflow shadow publication receipt，但没有发现 `weekly_client_basket/YYYYMMDD/{basket.json,receipt.json}` 或等价的最终 10 股快照产物。

当前 `quant-intel-platform/out` 中可见的 `weekly` 相关文件只有 `weekly_recap.meta.json`，不属于 10 股组合快照。

用户配置目录 `/home/richard/.config/market-intel` 中没有发现独立的 `cashflow-shadow.env`；`/home/richard/.config/quant` 中也没有发现 `WEEKLY_BASKET_*` 运行配置，因此无法从当前配置推导 weekly basket 或 Cashflow shadow 的完整外部输出根目录。配置文件中存在 API/市场数据相关文件，但本盘点不读取凭证内容。

用户级 systemd 当前可见的是 DailyWatch20 producer/prewarm/freshness timer，没有启用中的 `weekly-client-basket.timer`。部署仓库虽然有对应的 bridge 和 service template，但它们不能证明历史 10 股快照已经生成或发送。

## 飞书消息来源观测

通过飞书用户身份只读搜索 `Weekly Client Basket`，发现 2026-09-09 09:12 和 09:17 的两条私聊机器人预览消息，内容一致，均对应 `2026-09-14` 的冻结周组合。可解析出以下 10 只股票：

- DailyWatch family：688110.SH、002837.SZ、600118.SH、300475.SZ、688037.SH、300476.SZ、688627.SH。
- Cashflow：603173.SH、002071.SZ、601083.SH。
- Microcap：本次无有效 artifact，因此实际配额为 7/3/0，而不是设计默认的 4/3/3。

消息来源是飞书 `post`，发送方为 `凯川智能分析AI`；目前没有在消息中发现对应的 canonical `basket.json`、`receipt.json` 或 delivery receipt。该记录可以作为真实灰度推进的观测样本，但暂时只能标记为 `message_derived`，不能替代 canonical artifact，也不能产生历史收益结论。由于组合生效日是 2026-09-14，当前行情最多覆盖到 2026-09-09，尚无可结算的前向收益。

对这 10 只股票做行情可执行性预检时，2026-09-09 数据覆盖 9/10；`002071.SZ` 的历史行情最后日期为 2021-05-06，不能证明它在 2026-09-14 可交易。因此首个样本还需要在生效日前通过 instrument snapshot/交易状态再次校验。回测实现应将其标记为不可执行，不得静默当作正常零收益；组合口径需要明确选择 fail-closed，或暴露缺失权重并对可用成分重归一化。

回测仓库已增加显式的飞书预览适配器 `research.experiments.daily_feishu10.message_preview.parse_message_preview`。它只接受标题、消息创建时间和编号股票行，强制要求恰好 10 只，输出等权 selections，并在 DataFrame metadata 标记 `provenance=message_derived`；它不绕过 canonical basket/receipt 校验。用真实 2026-09-09 09:17 消息跑通后，确认解析结果为 10 只、DailyWatch family 7 / Cashflow 3，生效日 2026-09-14。

回测仓库同时提供 `write_replay_artifacts`，会输出逐股票 observations、逐信号日 signal_days、指标 JSON 和带 SHA-256 的 manifest，便于首个真实结算日保存可审计结果。

另发现 `/home/richard/data/quant/market-data-platform/research/index_replication/cashflow_three_weekly_20260909_v1..v6` 下存在 Cashflow 3 组件历史回放，以及多处 DailyWatch20 单策略/控制组回放。它们可以用于组件诊断，但没有最终飞书10股的组合身份、同日来源配额、basket hash 或投递证明，因此不纳入本次10股组合收益，也不作为最终组合的 PIT 替代样本。

## 回测所需最小输入

要把状态改为 `ready_for_gray_replay`，至少需要：

1. 每个实际推进日的 canonical `basket.json`，包括 symbol、权重、source strategy、signal date、valid until、artifact hash。
2. 对应的组合 `receipt.json`，证明输入 artifact 和最终 basket hash 未被替换。
3. 如需评价“实际发到飞书”，还需要对应 delivery receipt；它用于确认投递状态，但不替代 basket canonical artifact。
4. 从每个生效日开始的权威行情数据，至少包含前复权或明确调整口径的 open/close，以及停牌、涨跌停和缺失状态。
5. 基准日收益和成本假设。主口径固定为信号日收盘后、下一交易日开盘执行；不得使用同日收益作为主结果。

## 当前行动

在真实 basket artifact 被定位或补齐前，不生成历史收益结论。当前已把 2026-09-14 消息样本纳入待结算队列；下一步应将消息解析结果与行情快照、投递回执一起固化为不可变观测记录，并从 2026-09-15 起按下一交易日开盘执行口径结算 1/3/5/10 个交易日收益。若能补齐历史 canonical artifact，再追加历史样本外回放。
