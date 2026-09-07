# 十年 D11-H5 分层比较实施计划

> 面向智能体的执行说明：必须使用 `superpowers:executing-plans`，逐项执行本计划。

目标：在统一的组合条件下，对基本面、DailyWatch20、D11-H5 及其分层组合进行长期历史比较，并完成验证。该比较仅用于研究。

架构：复用现有的 D11-H5 排名器和分数阶梯格式。扩展封存模型帧和原始模型帧的准备流程，使其覆盖更早历史区间并支持严格的滚动样本外评分。随后，在共同的月度建仓日期上，将生成的分数阶梯与现有基本面和 DailyWatch20 阶梯合并。比较结果属于离线研究产物，不改变已发布的策略状态和生产目标。

技术栈：Python、pandas、Parquet、现有的 `strategy-pipeline` D11-H5 排名器、现有组合回放工具、pytest。

规格依据：`strategy-research/research/experiments/fundamental_state_forecasting/README.md`，以及 `strategy-research/research/experiments/long_term_fundamental_v2/20260902_results.md` 中当前的分层比较记录。

## 全局约束

- 所有分数必须满足点时条件，只能用于研究。
- 训练标签的结束时间不得晚于每个重新拟合日期。
- 每个策略分支必须使用相同的建仓日期、股票池、持仓数量、交易成本和价格资产。
- 已有发布的 D11-H5 状态在可用时具有权威性。重建的历史数据必须单独审计。
- 本实验不得推动任何生产发布。
- 缺失日期或股票必须报告，不能静默向前填充。

## 任务 1：隔离工作区并审计覆盖范围

文件：

- 创建：本计划文件
- 检查：`strategy-research/research/experiments/fundamental_state_forecasting/reconstruct_d11_h5_historical.py`
- 检查：`/home/richard/data/market-data-platform/research/fundamental_state_forecasting/` 下已有的研究产物

- [ ] 确认功能分支已隔离，基础检出目录干净。
- [ ] 记录模型帧、DailyWatch20 阶梯、价格和基本面分数的覆盖范围。
- [ ] 找出当前模型帧支持的最早日期，以及从原始日线数据中理论上可以支持的最早日期。

## 任务 2：生成历史 D11-H5 阶梯

文件：

- 修改：`strategy-research/research/experiments/fundamental_state_forecasting/reconstruct_d11_h5_historical.py`
- 测试：如果接口发生变化，修改 `strategy-research/research/experiments/fundamental_state_forecasting/test_reconstruct_d11_h5_historical.py`

- [ ] 为重建流程增加更早模型帧和明确评估区间的参数。
- [ ] 保留 504 个日期的训练窗口和标签结束时间样本外规则。
- [ ] 输出每个日期精确的 Top-800 阶梯、重新拟合回执，以及包含最早有效日期和覆盖缺口的审计结果。
- [ ] 使用可恢复或按区块执行的方式，使长时间运行可以检查，并且不会丢失已完成的区块。

## 任务 3：验证分数并对齐共同日期

文件：

- 创建或修改：`strategy-research/research/experiments/long_term_fundamental_v2/` 下的历史比较运行器
- 修改：`strategy-research/research/experiments/long_term_fundamental_v2/20260902_results.md`

- [ ] 在重叠日期上，将重建的 D11-H5 分数与已发布分数比较，指标包括秩相关系数和 Top-20 重叠率。
- [ ] 定义所有阶梯共同的严格月度建仓日期交集。
- [ ] 当某个阶梯缺少股票或日期时，直接失败或生成单独的诊断结果。

## 任务 4：统一回放六个或七个策略分支

文件：

- 复用或修改：现有月度回放运行器和 `portfolio-backtester` 接口
- 创建：`/home/richard/data/market-data-platform/research/fundamental_state_forecasting/` 下带日期的研究产物目录

- [ ] 运行基本面单层、DailyWatch20 单层、D11-H5 单层、基本面加 DailyWatch20、基本面加 D11-H5、三者融合，以及 DailyWatch20 加 D11-H5 控制组。
- [ ] 所有分支使用相同的 Top-K、换手迟滞、价格来源、交易成本和样本外日期规则。
- [ ] 为每个分支保存持仓、收益、汇总指标、暴露和审计回执。

## 任务 5：证据、风险诊断和准入检查

文件：

- 修改：`strategy-research/research/experiments/long_term_fundamental_v2/20260902_results.md`
- 修改：`strategy-research/research/experiments/long_term_fundamental_v2/production_gate_audit_20260903.json`
- 必要时创建：带日期的覆盖范围和比较审计文件

- [ ] 报告总收益、年化收益、夏普比率、最大回撤、换手率、成本、样本数量和共同区间覆盖率。
- [ ] 在数据可用时，补充规模、行业、换手、集中度和缺失数据诊断。
- [ ] 将严格可比的结果与部分覆盖或重建得到的诊断结果分开。
- [ ] 只有在所有现有准入条件都得到明确验证时，才允许生产资格为真。
- [ ] 在宣称完成前，运行专项测试、语法检查和产物完整性检查。
