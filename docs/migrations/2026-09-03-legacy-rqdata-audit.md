# legacy RQData 代码审计

> status: active
> owner: workspace
> last_verified: 2026-09-03

## 审计结论

internal 的 `legacy_rqdata_runtime.py` 仍属于当前运行路径，暂时不能删除，也不应直接复制到公共仓库。
它包含 RQData 客户端初始化、历史本地 RQData 文件读取、RQData 调整价格兼容补丁和 HK 历史符号转换。
这些内容与公共 `strategy-pipeline` 的 clean-room 边界不一致。

当前核对的 internal main 为 `df444be`。公共 `strategy-pipeline` main 为 `c2a13e75`，公共仓库没有
`strategy_pipeline.legacy_rqdata_runtime` 模块。

## 当前 active 引用

| 引用位置 | 使用内容 | 后续处理 |
| --- | --- | --- |
| `cli/common.py` | RQData 初始化配置和运行时初始化 | 随 CLI 迁移，删除 RQData 初始化入口 |
| `liveops/alloc_market_data.py` | RQData 符号格式转换 | 改用 execution owner 的 broker symbol API |
| `liveops/holdings.py` | HK 历史持仓符号标准化 | 先确认 execution owner 的 HK 规范，再替换 |
| `pipeline/support.py` | HK 历史符号标准化 | 迁移 pipeline 支持层时移除历史 RQData 依赖 |
| `legacy_rqdata_runtime.py` | RQData 和本地历史文件实现 | 完成上述调用方迁移后归档并删除 |

## 删除条件

下列条件全部满足后，才能把该模块标记为 `archive` 并从 active source tree 删除：

1. internal CLI 不再导入 RQData 初始化函数。
2. liveops 不再调用 RQData 符号格式转换。
3. pipeline 支持层改用 owner API，且 HK 历史兼容逻辑有明确归属。
4. internal 测试不再覆盖 RQData 运行时和本地 RQData 读取实现。
5. clean-room 扫描确认公共仓库没有 provider SDK、凭证字段或私有策略内容。

## 当前判断

这部分代码的最终处理方向是归档和删除，不迁移到公共 `strategy-pipeline`。其中需要保留的通用符号规范
应先由 `quant-execution-engine` 或 `market-data-platform` 提供 owner API，internal 只在过渡期保留兼容调用。
