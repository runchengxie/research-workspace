# D11-H5 五袖套影子策略

D11-H5 按 T 日收盘生成每日信号和五袖套合并目标，在下一交易日开盘语义下做只追加影子跟踪。产物固定 `research_only=true`、`eligible_for_live=false`。

当前 `v2` 组合合同固定为五个互斥子组合、每个子组合 4 只，合并后恰好 20 只股票且单股目标权重 5%。每个交易日只刷新一个子组合，因此单日最多新增 4 只、移除 4 只；保留股不足 4 只时才会达到这个上限。停机后恢复或跨日追赶时按最新完整输入只运行一次当前目标，不逐日重复换仓。

- 生命周期：`shadow`
- 生产资格：无
- 特征和模型：`alpha-research`
- 组合构造与成本：`portfolio-backtester`
- 运行与版本化 JSON 输出：`strategy d11-h5-shadow`
- 复现打包：`strategy-research/packaging/d11_h5`

发布方使用 `strategy_pipeline.d11_h5_shadow.v2` / `d11_h5_shadow.cn.v2`，并在发布前强制校验 5×4、跨子组合不重叠、20 只等权和总权重为 100%。`v1` 仅由消费端在迁移窗口内兼容读取，不再作为新产物生成。

pipeline 只应保留运行和发布外壳。尚在其中的模型或目标构造计算需要迁回职责仓或 `strategy-app`，再由 catalog 记录新的入口。
