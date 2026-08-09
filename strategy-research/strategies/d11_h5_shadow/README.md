# D11-H5 五袖套影子策略

D11-H5 按 T 日收盘生成每日信号和五袖套合并目标，在下一交易日开盘语义下做只追加影子跟踪。产物固定 `research_only=true`、`eligible_for_live=false`。

- 生命周期：`shadow`
- 生产资格：无
- 特征和模型：`alpha-research`
- 组合构造与成本：`portfolio-backtester`
- 运行与版本化 JSON 输出：`strategy d11-h5-shadow`
- 复现打包：`strategy-research/packaging/d11_h5`

pipeline 只应保留运行和发布外壳。尚在其中的模型或目标构造计算需要迁回职责仓或 `strategy-app`，再由 catalog 记录新的入口。
