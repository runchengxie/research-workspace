# 研究回测和执行边界实施计划

目标：将 StyleReplica 策略规则、组合构造和信号研究职责迁移到各自的规范仓库。

架构：`alpha-research` 负责信号和 alpha 诊断，`strategy-app` 负责 StyleReplica 规则，`portfolio-backtester` 负责通用袖套选择和持仓构造，`strategy-pipeline` 负责编排和导出。`quant-execution-engine` 保持不变，从 `targets.json` 开始工作。

验证：每个仓库都在独立 worktree 中修改，通过 PR 提交，合并后再更新下游固定版本，最后删除 worktree。

## 已完成的仓库顺序

- [x] `portfolio-backtester` PR #49: generic sleeve portfolio owner API.
- [x] `strategy-app` PR #48: StyleReplica policy owner.
- [x] `alpha-research` PR #39: remove final portfolio construction and add signal churn semantics.
- [x] `strategy-app` PR #49: pin merged alpha boundary owner.
- [x] `strategy-pipeline` PR #90: compose canonical owners and refresh immutable pins.
- [ ] 更新顶层仓库的 gitlink 和治理台账。
- [ ] 运行工作区契约、doctor 和委托子模块检查。
