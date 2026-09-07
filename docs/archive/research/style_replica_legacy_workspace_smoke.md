# StyleReplica 旧工作区 smoke 测试

旧的 `tests/test_style_replica.py` 是职责边界建立前的集成测试。它导入已经移除的 `alpha_research.style_replica` 组合接口（`StyleReplicaPortfolioConfig`、主题配额和仓位构造），StyleReplica 拆分到各所有者仓库后，该测试已经无法继续运行。

当前覆盖由所有者仓库中的原生测试维护：

- `alpha-research/tests/test_style_replica_signal_generator.py` 覆盖信号生成和因子行为。
- `strategy-pipeline/tests/test_style_replica_output_ownership.py` 覆盖 pipeline 输出边界。
- `portfolio-backtester` 负责组合构造和执行行为。

该旧测试已从当前工作区测试套件中有意移除。不能为了保留已经废弃的导入接口而让当前 API 回退。
