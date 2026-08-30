# 研究探索归档（2026-08-31）

本页记录本地 worktree 和非 `main` 分支中尚未进入生产主线的研究探索。
这些内容没有直接并入运行时主线：它们主要用于验证研究假设、数据口径和诊断方法，
尚未形成稳定的 owner-native API 或完整的生产证据链。

## 处置原则

- 已被当前 `main` 等价吸收的代码，只保留结论和提交线索，不保留重复 worktree。
- 仍有研究价值但代码量较大的实验，记录研究问题、数据边界、实现范围和后续入口，
  不把实验实现强行变成生产依赖。
- 文档不宣称实验已经产生可交易或生产结论。如需重跑，应重新核对当前 submodule
  gitlink、数据快照和依赖版本。

## 探索清单

| 原分支 / worktree | 研究内容 | 规模 | 处置 |
| --- | --- | ---: | --- |
| `feat/shibor-regime-exploration` | Shibor regime、基金因子 PIT 审计、清洁窗口敏感性、M0 组合诊断 | 约 1,065 行差异 | 归档为文档，不进入生产主线 |
| `feat/turnover-anatomy-deconfounding` | 换手率去混杂、size-turnover 双排序、诊断与测试 | 约 956 行差异 | 归档为文档，不进入生产主线 |
| `feat/quality-compatibility` | Level-2 数据质量与兼容层 | 约 459 行差异 | 归档为文档，不进入生产主线 |
| `microcap-workspace-252` | microcap robustness、容量阶梯、控制组和研究规范 | 约 1,958 行差异 | 归档为文档，删除临时 worktree |
| `microcap-workspace-253` | microcap characteristic decomposition、横截面推断和验证 | 约 3,170 行差异 | 归档为文档，删除临时 worktree |
| `feat/fundamental-family-shadow` | 旧版治理 baseline、roadmap、gitlink 和边界文档 | 2 个独立提交 | 当前主线已有更新版本，可删除 |
| `feat/sclt-execution-research` | Level-2 / 小盘执行研究的旧版实现 | 3 个独立提交 | 核心文件已在 strategy-research 主线，删除重复分支 |

## Shibor 与基金因子探索

原分支：`feat/shibor-regime-exploration`，最后提交 `fa485b30`。

探索过程包括：

- 建立基金因子 context shadow，并保留 PIT 数据审计。
- 记录历史基金重复数据冲突及其处理口径。
- 增加 clean-window sensitivity，检查历史重复/污染窗口对结果的影响。
- 增加 M0 benchmark-relative、HAC active-return、capacity、final-OOS 和 regime
  相关诊断。
- 将数据质量修复和 owner gitlink 通过提交固定下来。

这些内容适合未来继续做研究复核，但当前不是稳定的生产策略入口。删除代码后，
不能直接从本文恢复完整 runner。若重新开展，应从该分支提交记录中重建，并重新锁定
market-data-platform 数据版本。

## 换手率去混杂探索

原分支：`feat/turnover-anatomy-deconfounding`，最后提交 `b325c73d`。

探索重点是把 size、turnover 和流动性暴露拆开观察，包含：

- `turnover_anatomy` 诊断模块。
- size-turnover double-sort 的扩展。
- 小盘低换手实验的诊断增强。
- 对应的双排序、换手率 anatomy 和实验测试。

这是一套研究诊断工具，不是已批准的生产因子。删除后会失去直接重跑这些诊断的
代码，但不会影响当前 main 的生产回测接口。

## Level-2 质量兼容探索

原分支：Deep Learning 项目的 `feat/quality-compatibility`，最后提交 `8feb97d`。

该分支增加了共享 L2 quality compatibility layer，覆盖：

- `ticknet.simulator.quality` 质量检查。
- `quality_compat` 兼容适配。
- opening ledger 的小幅调整。
- L2 quality 和 compatibility 测试。
- Colab / 项目状态文档更新。

它保留的是 tick/L2 研究管线的质量语义，不是 research-workspace 当前运行时依赖。
如果未来重新启用 L2 研究，应把质量契约重新对齐当前数据源和 simulator API。

## Microcap robustness 与 decomposition

两个临时 worktree 是同一轮 microcap 探索的不同阶段：

- `microcap-workspace-252`（`3ab76d39`）：robustness runner、容量限制、filtered
  controls、加权 long-only 研究、数据 fingerprint 和研究规范。
- `microcap-workspace-253`（`6fba47af`）：在另一条演进线上增加 PIT characteristics、
  cross-sectional inference、characteristic decomposition、statsmodels 依赖和更完整
  的验证测试。

两者有大量重叠，但不是简单的线性包含关系。它们记录了 microcap 控制组、容量、
特征分解和推断口径的探索过程。没有把未经最终证据门禁确认的结果提升为生产策略。
删除 worktree 后，本文保留研究范围和恢复线索，但不保留可直接执行的实验代码。

## Fundamental family shadow

原分支的两个独立提交是 `c3672364` 和 `362e032a`，主要涉及旧版：

- maintainability baseline 和 roadmap 对齐。
- hash helper ownership、script lifecycle、owner-native manifest。
- workspace doctor、gitlink 和迁移路径文档。

当前主线已经包含更新后的治理文档、LOC 工具登记、manifest 和 baseline，
因此该分支没有需要单独保留的功能代码。

## SCLT / 执行研究

原分支的关键提交为 `a9f83c8`、`dfa088f`、`08a95dc`。它涉及：

- A-share Level-2 event 和 archive 适配。
- order-book replay、small-cap execution model、tick-data audit。
- execution cash ledger 的实验实现及测试。

其中 ledger 实现与当前 owner-native portfolio settlement facade 存在实现冲突，
没有重复并入。相关研究文件和测试已在 strategy-research 主线的既有合并链中可见。
保留该分支不会增加当前生产能力，只保留一条旧实现演进线，因此清理分支。

## 恢复建议

若未来要重启某项研究，优先顺序建议为：

1. 重新从当前 `main` 创建研究分支。
2. 先恢复数据契约和 PIT/fingerprint 测试。
3. 再逐个恢复 runner 或诊断模块。
4. 通过 owner-native、质量、类型和 evidence gates 后，才考虑合入运行时主线。
