# Macro Context Shadow

`macro_context_shadow_v1` 验证宏观、产业和公司暴露是否为 A 股横截面预测带来稳定增量。实验处于 `exploration`，禁止生产发布。

实验固定比较 C0 至 C3 四组特征，并使用 5、20、60 个交易日标签，其中 20 日是唯一主选择周期。宏观序列必须来自 `cn_context` current contract，股票数据来自 `a_share` current contract。实验只组合 `market-data-platform`、`alpha-research` 和 `portfolio-backtester` 的公开 API，不在此目录复制通用实现。

没有可靠 `available_at`、`source_retrieved_at`、vintage 或公司暴露的数据会拒绝进入 promotion-safe 运行。探索模式可以记录 reconstructed 历史，但任何依赖 reconstructed 数据的结论都不能晋级。

失败条件包括：PIT 可见性不完整、上下文数据过期、C2/C3 没有样本外增量、增量仅由 reconstructed 数据产生、成本后优势消失、行业或风格暴露漂移超限。真实运行前必须先完成 final OOS、CPCV/PBO、换手成本、容量和 regime 稳定性证据。

运行入口：

```bash
python -m macro_context_shadow.run_contextual_alpha_shadow --data-root "$DATA_PLATFORM_ROOT" --dry-run
```
