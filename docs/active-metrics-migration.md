# Active metrics migration

本工作区变更由两个下游仓库 PR 组成：

1. `portfolio-backtester#11`
   - 新增 position benchmark evaluation
   - 新增 PSR、DSR 和 Expected Max Sharpe 公共统计 API
2. `strategy-pipeline#25`
   - 将重复的 active-return、period-return 和 Sharpe inference 实现改为兼容 re-export
   - 保留 pipeline 专属预测评估指标

## 合并顺序

1. 合并 `portfolio-backtester#11`
2. 发布或在工作区锁定 `portfolio-backtester 0.4.0`
3. 更新并验证 `strategy-pipeline#25` 的依赖锁文件
4. 合并 `strategy-pipeline#25`
5. 最后合并本工作区 PR

## 验证重点

- position benchmark 日收益必须按 entry/exit 持有期复合，不能直接与 period returns 按退出日做日频 merge
- `run_position_backtest()` 保持 benchmark-agnostic
- strategy、benchmark 和 active stats 保持分层，不把 IR 扁平混入策略自身 stats
- 旧 `strategy_pipeline.return_metrics` 和 `strategy_pipeline.sharpe_stats` 导入路径继续可用
- 工作区测试应确认共享函数对象来自 `portfolio_backtester`
