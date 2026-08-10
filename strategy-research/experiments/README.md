# 探索实验

一次性的量化回测和数据分析，每个子目录是一个自包含的实验。不进入生产 pipeline，仅供记录思路和结论。

## 目录

| 目录 | 说明 | 状态 |
|------|------|------|
| `next_open_to_high/` | A股次日开盘到日内高点 XGBoost 预测 | 探索完成 |
| `daily_watch20_fundamental_shadow/` | DailyWatch20 基本面 shadow 验证 | 探索完成 |
| `slow_volume_verification/` | slow-volume campaign 产出校验与对账 | 一次性验证 |
| `style_factors/` | 风格因子全历史约束验证、市场状态、价值周期等 | 探索文档 |
| `hotsector/` | Hotsector DeepSeek/Numeric 预注册与结果文档 | 实验记录 |
| `strategy_direction/` | 周度 vs 日度策略方向探索 | 探索完成 |
| `reproducibility/` | D11-H5 打包辅助、stateful-staggered 复现 | 一次性工具 |
| `qlib_pilot/` | qlib XGBModel 训练/评估可行性验证 | 进行中 |
| `adhoc/` | 旧探索入口脚本（概念 ML、ETF 回测、hotsector 转换、HK 导出等） | 归档 |
| `archive/` | 过期/一次性脚本存档 | 归档 |

## 规则

- 新增实验在 `experiments/` 下建目录，不需走 strategy-pipeline 的 CI 和测试
- 每个实验目录建议放一个 README.md 记录结论，方便以后查阅
- 有明确结论的实验建议补一份 `research_spec.json` 实验说明书，格式与校验见
  [docs/research-spec.md](../../docs/research-spec.md)
- 实验结果好、决定上生产时，再完整重构到对应子仓库
- 不要引入跨实验的隐式依赖；可复用工具沉淀到各子仓库的正式包里
