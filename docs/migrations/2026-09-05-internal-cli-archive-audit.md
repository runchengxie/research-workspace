# internal CLI 归档审计

## 审计结论

internal CLI 包含 `common.py`、`core.py`、`liveops.py`、`research.py` 和包入口。当前唯一注册的 `strategy` 命令属于 internal 自身的 `pyproject.toml`，workspace、定时任务和 owner 仓库没有调用这些入口。

公共 `strategy-pipeline` 已提供公开控制面 CLI。workspace production release 的 contract smoke 已验证 `strategy-pipeline export-targets`，执行侧入口由 `quant-execution-engine` 提供。

## 处理方式

internal CLI 标记为 `archive`，不再作为 workspace active entrypoint 维护。实现和对应测试保留在
`retirement-freeze-20260905-r1`，供历史研究复核和恢复使用。

恢复时必须从冻结 tag 创建独立恢复分支，重新核对 CLI 依赖和各 owner 版本，并执行 internal CLI、公共 pipeline CLI、workspace contract smoke 以及 owner 检查。恢复结果不能自动重新注册为 workspace 或 production 的 active 命令。
