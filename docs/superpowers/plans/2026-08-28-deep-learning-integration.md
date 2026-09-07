# 计划：将 deep-learning 接入为独立研究卫星

## 目标

在 `research-workspace` 中注册 `deep-learning-tick-data-prediction`，将其作为独立发布的 Git 子模块，并定义向 `alpha-research` 和 `portfolio-backtester` 交接的稳定资产接口。L2 数据、检查点、实验输出和仓库专属实现保留在顶层仓库之外。

## 任务

1. 将 deep-learning 仓库注册为 Git 子模块。
   - 在 `.gitmodules` 中更新公开 HTTPS 仓库地址。
   - 将子模块固定到上游已经推送的 `main` 提交。
   - 顶层仓库不复制源码、数据、检查点或生成输出。

2. 为新子模块增加委托质量检查。
   - 在 `scripts/submodule_checks.json` 中增加 smoke、lint、test、type、release-typecheck 和 full 配置。
   - 扩展清单测试和子模块列表测试，避免注册信息静默漂移。

3. 记录集成边界。
   - 说明 deep-learning 是负责 L2 事件流审计和模型产物的研究卫星。
   - 将交接定义为版本化预测资产，alpha 证据由 `alpha-research` 负责，组合和执行语义由 `portfolio-backtester` 负责。
   - 记录在完成差分一致性验证前，原生事件级模拟器仍是正确性基准。

4. 验证联邦式工作区。
   - 运行覆盖 Git 子模块和委托检查清单的顶层测试。
   - 运行新的子模块 smoke 检查和工作区 doctor。
   - 报告结果前检查最终差异和子模块状态。
