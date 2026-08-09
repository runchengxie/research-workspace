# 热点板块选股

热点板块策略从外部版本化候选文件取得候选范围，以 Numeric 排名为确定性基准，研究低换手、会话选择和模型重排是否能在严格证据约束下增加价值。外部模型结果只作为低权重 shadow 或受保护分数带内的辅助判断。

Numeric v2、低换手、会话 challenger、AI shadow、DeepSeek 五臂和 V4 配对回放都是同一策略族的变体。当前历史实验不构成新的样本外证据，DeepSeek 既有门槛未通过，禁止自动晋级。

- 生命周期：`research_shadow`
- 生产资格：无
- 候选和外部选择输入：`market-intel`
- 策略特有计算：`strategy_app.hotsector`
- 组合与执行回放：`portfolio_backtester`
- 外部调用和证据冻结：`strategy_pipeline`
- 证据入口：`strategy-app/docs/research/README.md`

pipeline 当前仍保存大量分析、campaign、合同和兼容 facade。迁移时先把调用方切到 `strategy_app`，再删除重复文件，模型调用、调用预算、凭证和原始响应归档不下沉。
