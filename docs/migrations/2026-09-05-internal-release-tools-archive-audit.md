# internal release tools 归档审计

## 审计结论

`strategy_pipeline_internal.release_tools` 包含历史 run 打包、manifest 构造和 GitHub Release 上传工具，共 5 个实现文件：

- `_package_runs_api.py`
- `_package_runs_core.py`
- `package_runs_args.py`
- `package_runs_manifest.py`
- `release_runs.py`

截至 internal `44fd1bae`，workspace、strategy-research、strategy-app、alpha-research、portfolio-backtester、quant-execution-engine 和 market-data-platform 都没有 active consumer。workspace 当前也没有依赖这些模块的安装配置、CI、脚本或 production 入口。

## 处理方式

这批代码标记为 `archive`，不迁入公共 `strategy-pipeline`，也不继续扩展为 workspace active 发布入口。实现和历史测试保留在
`retirement-freeze-20260905-r1`，供需要恢复历史 run 打包流程时使用。

恢复时必须从冻结 tag 创建独立恢复分支，重新安装其依赖，并重新执行 `tests/test_run_release_scripts.py` 和 owner 依赖检查。恢复结果不能自动成为 workspace 或 production 的 active consumer。
