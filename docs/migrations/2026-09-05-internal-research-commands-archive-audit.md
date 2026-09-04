# internal 研究命令归档审计

## 审计结论

internal `commands` 目录当前包含 9 个文件，覆盖 grid backtest、fixed-signal grid 和参数 tune：

- `_linear_sweep_api.py`
- `_linear_sweep_core.py`
- `run_grid.py`
- `run_grid_common.py`
- `run_grid_fixed.py`
- `tune/parser.py`
- `tune/report.py`
- `tune/spec.py`
- `tune_runner.py`

公共的 grid 支持函数已经迁入 `portfolio-backtester`。剩余命令实现只由 internal research CLI 调用。workspace、strategy-app、strategy-research、alpha-research 和 portfolio-backtester 当前都没有 active consumer，也没有 production 配置或 CI 依赖这些 internal CLI。

## 处理方式

这批代码标记为 `archive`，不迁入公共 `strategy-pipeline`，也不继续作为 workspace active 命令维护。完整实现和测试保留在
`retirement-freeze-20260905-r1`，供历史研究复核使用。

恢复时必须从冻结 tag 创建独立恢复分支，重新核对 `alpha-research`、`portfolio-backtester` 和
`market-data-platform` 的 owner API 版本，并执行 `tests/test_run_grid.py`、`tests/test_tune.py`、`tests/test_cli_research.py` 和完整的 owner 检查。恢复结果不能自动成为 production 或 workspace active consumer。
