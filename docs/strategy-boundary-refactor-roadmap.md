# 策略边界重构路线图

> status: reference
> owner: workspace
> last_verified: 2026-08-17
> source_of_truth: no
> superseded_by: roadmap.md

本页保存 [ADR-0006](adr/0006-strategy-knowledge-and-runtime-boundaries.md) R0 至 R6 的实施记录和验收标准。
阶段状态已经全部完成。工作区剩余项目和优先级统一见[工作区路线图](roadmap.md)。

## 当前基线

已经完成：

- 原 `research-apps` 仓库和 Python 包已经分别改名为 `strategy-app` 与 `strategy_app`。
- `strategy-research` 已登记七个策略或策略族，并成为策略身份、生命周期和证据导航的权威位置。
- 根工作区已经采用新的子模块名称，并增加三层边界和回归测试。
- `strategy-pipeline` 的依赖、导入、锁文件和活动文档已切换至 `strategy-app` 0.2.x 与 `strategy_app` 命名空间（R2 已完成）。

完成后的维护项：

- 跨仓库调用仍有少量私有符号依赖，后续按[工作区路线图 B1](roadmap.md#b1只通过公开-owner-api-跨仓调用)提升为公开 owner API。
- pipeline 的跨仓库 contract 说明、综合指标文档和输出参考继续按[文档归集清单](documentation-consolidation.md)去重。
- 大文件、长函数和复杂度热点继续由 `maintainability-refactor-roadmap.yml` 的预算棘轮约束。
- 策略生命周期证据继续由 `strategy_evidence_gate.py` 独立验收，代码归位完成不代表策略证据已经完成。

历史行数是 2026-08-16 的盘点基线，不是目标配额。后续以公开接口稳定、职责纯度和预算收敛为目标。

## 目标状态

```text
strategy-research
  人类可读策略规格、生命周期和证据入口
          |
          v
strategy-app
  策略特有纯计算和冻结合同
          |
          v
strategy-pipeline
  外部调用、运行目录、操作控制、发布门禁和 targets.json
```

数据资产归 `market-data-platform`，特征、标签、模型和通用统计归 `alpha-research`，组合构造、成本、换手、容量和回放归 `portfolio-backtester`，交易执行归 `quant-execution-engine`。`strategy-app` 中出现两个策略可复用的能力时，应直接迁入对应 owner 仓。

## 实施阶段

| 阶段 | 状态 | 主要工作 | 完成标准 |
| --- | --- | --- | --- |
| R0 仓库改名 | 已完成 | `research-apps` 改为 `strategy-app`，移除旧 Python 包兼容层 | 新 wheel 只包含 `strategy_app`，历史回执 schema 保持不变 |
| R1 策略目录 | 已完成 | 建立七个策略族的权威目录、生命周期字段和 ADR-0006 | 人可从 `strategy-research` 找到策略、代码、证据和迁移债务 |
| R2 pipeline 改名切换 | 已完成 | 更新依赖、Git pin、导入、类型配置、wheel smoke、活动文档和测试名称 | clean clone 只安装 `strategy-app` 0.2.x，活动代码不再导入 `research_apps` |
| R3 调用方改向 | 已完成 | 46 个 delegating public wrapper 已删除，调用方改向 owner API，provenance 升级 v2 | 策略 owner wrapper 清零，`daily_watch20_fundamental_shadow` 保留为研究实现，不新增替代兼容层 |
| R4 通用能力归位 | 已完成 | `date_utils` 已委托 `alpha-research`，DailyWatch20 全家族、红利成长、D11-H5、热点板块全子批次已迁 owner，通用统计（`metrics.py`）已在 #66 下沉 `alpha-research`，benchmark 区间收益已在 #67 下沉 `portfolio-backtester`，候选 OOS 职责已下沉 owner（`daily_watch20_candidate_oos.py` 重构为 `pipeline/final_oos_stage.py` 纯编排壳，特征/滚动评分/策略比较分别在 `market-data-platform`、`alpha-research`、`strategy-app`），`style_factors` 切片 7 已收口：因子计算内核迁 `alpha-research.style_factors`（阶段①，alpha-research `2f34930`，根仓 gitlink `405f712`），分位数多空回测内核迁 `portfolio_backtester.style_factors_backtest`（阶段②，portfolio-backtester `18d20c8`，根仓 gitlink `1428a72`），呈现/研究层整包迁 `strategy-research/style_factors`（阶段③，根仓 `ac02bbbc`），根仓 `src/style_factors` 已删除 | pipeline 不再维护模型、通用统计、组合会计、成本或执行回放 |
| R5 重复内容清理 | 已完成 | 13 个重复研究脚本、9 份冻结研究文档副本已删除，pipeline 的 `metrics.md`、`full-reference.md`、`benchmark-protocol.md` 已改为 owner 索引 | 每个活动脚本或说明只有一个维护位置，owner 文档为权威，历史哈希与回执仍可验证 |
| R6 控制面收口 | 已完成 | import/source 边界已收紧，体量基线、版本清单和发布证据已刷新，catalog 迁移债务已清理，strategy-app 类型门禁已恢复全绿（2026-08-16），benchmark 抽离已在 #67 合并（pipeline 无 benchmark 运行时实现），`style_factors` 切片 7 已收口（阶段①/②/③，提交 2f34930/18d20c8/ac02bbbc），根仓库 gitlink 已对齐六子模块 `origin/main`（无漂移，含 #66/#67/#68 与 style_factors 迁移的 alpha-research/portfolio-backtester 提交）。验收缺口已在本轮修复：研究层 `strategy-research` 已建 `pyproject.toml`、本地 owner sources 与 `uv.lock`，可独立运行，根 `run_pre_push_checks` 直接调用该 project（不再手工设置 `PYTHONPATH`）并新增 `research-layer-tests`/`research-layer-quality` 门（43 个测试 + ruff/format/ty/CLI smoke 全绿），关键回归测试已补回（compute_factors/winsorize/行业缺失/PIT/逐年报告/图表/归因），重复 `helpers` 已删并改引用 `alpha_research` owner，活动文档 `src/style_factors` 引用已更新为 `alpha_research.style_factors`/`portfolio_backtester.style_factors_backtest`/`strategy-research/style_factors`。三 owner 仓（alpha-research 285、portfolio-backtester 396、strategy-research 43）与根工作区（含研究层）门禁全绿。远端功能分支 `github/feat/r6-gitlink-governance-sync` 与 `strategy-pipeline/origin/fix/r4-benchmark-owner` 按 pre-push guard 审计保留政策保留（guard 禁止删除远端功能分支） | pipeline 只剩控制面职责，全工作区严格门禁通过 |

## R2：先完成 pipeline 改名切换

该阶段当时作为第一个实施步骤，因为后续调用方迁移都依赖新包名。

1. 将 `strategy-pipeline/pyproject.toml` 和 `uv.lock` 的依赖切换到 `strategy-app` 已合并提交。
2. 将活动源码和测试导入从 `research_apps` 改为 `strategy_app`。
3. 更新 wheel smoke、namespace boundary、README、AGENTS 和当前维护文档。
4. 保留历史 ADR、版本快照、冻结回执中的旧仓库名，以及 `research_apps.hotsector.deepseek_v4_paired_replay.v1` schema。
5. 不发布 `research_apps` 兼容包，也不在 pipeline 内嵌 fallback。

验收时对活动路径执行旧名称扫描。允许命中历史证据，禁止命中运行时代码、当前依赖和当前操作文档。

## R3 与 R4：按垂直切片迁移

每个切片都按同一依赖顺序推进：

```text
owner 仓补齐公开 API
        -> strategy-app 改用 owner API
        -> strategy-pipeline 调用方改向
        -> 同批删除旧实现和 facade
        -> 根工作区更新 gitlink 与版本证据
```

建议切片顺序如下：

| 顺序 | 切片 | 目标归属 | 主要遗留 |
| --- | --- | --- | --- |
| 1 | 已有 owner wrapper | `alpha-research`、`market-data-platform`、`portfolio-backtester`、`strategy-app` | 已完成：46 个 delegating wrapper 删除，provenance v2 |
| 2 | DailyWatch20 | `strategy-app` 加现有 data、alpha、portfolio API | 已完成：策略计算迁 owner，pipeline 只保留运行、发布和状态汇总 |
| 3 | 热点板块 | `strategy-app` 加 `portfolio-backtester`，外部候选继续文件耦合 | 已完成：three-arm、v4-month、numeric-v2、holdings-overlay、session-challenger、evidence-bundle 迁入 strategy-app |
| 4 | 次日开盘到最高价 | 模型进 `alpha-research`，回放与成本进 `portfolio-backtester`，策略组合进 `strategy-app` | 已完成：脚本已迁 `strategy-research/experiments/next_open_to_high/`，pipeline 无残留 |
| 5 | D11-H5 | 模型与信号进 `alpha-research`，目标构造与袖套回放进 `portfolio-backtester` | 已完成：owner 负责计算与合同，pipeline 保留 shadow runner 编排壳 |
| 6 | 红利与成长 ETF 动量 | 通用回测进 `portfolio-backtester`，策略配置与报告组合进 `strategy-app` | 已完成：四模块迁入 strategy-app，研究 runner 改向 |
| 7 | StyleReplica | 行业平衡袖套组合构造已迁入 `portfolio-backtester`。因子计算内核迁 `alpha-research.style_factors`，分位数多空回测内核迁 `portfolio_backtester.style_factors_backtest`，呈现/研究层整包迁 `strategy-research/style_factors` | 已完成：根仓 `src/style_factors` 已删除，调用方（qlib_pilot 等）改向子模块内核，R4 切片 7 收口 |

迁移一个切片时同时迁移测试。pipeline 只保留 runner、provider adapter、操作员门禁、运行目录、原子发布与 `targets.json` 生成测试。

## R5：脚本、文档和 contract 去重

- `strategy-research` 保存策略说明、研究结论、实验入口和证据导航，不成为生产进程依赖。
- `strategy-app` 保存策略特有的可执行协议和冻结实验合同。
- owner 仓保存通用算法及其 API 文档。
- pipeline 只保存 provider 调用、运行和发布操作说明。
- 跨仓库稳定字段由生产方维护，顶层 `research_contracts` 与 `docs/contracts.md` 维护发现入口和组合校验。
- 已被回执或 provenance 哈希绑定的内容不改写。需要升级时发布新的版本化 manifest，旧版本进入历史证据。

已完成：13 个 `scripts/research/` 重复脚本和 9 份冻结研究文档副本已删除，对应测试迁入工作区 `tests/` 并指向权威脚本。pipeline 的 `docs/metrics.md`、`docs/reference/outputs/full-reference.md` 和 `docs/concepts/benchmark-protocol.md` 已改为跨仓库索引，指标解读与产物契约分别归 `alpha-research`（预测质量、CPCV、PBO、特征重要度）和 `portfolio-backtester`（回测、成本、暴露、benchmark ladder）。

## R6：最终收口标准

以下条件全部满足后，ADR-0006 的实施才算完成：

- `strategy-pipeline` 的活动依赖和源码中不存在旧包名。
- 策略 owner facade 组的活动记录和文件都已移除。
- catalog 中没有把 `strategy-pipeline` 列为策略计算 owner，只作为 `control_plane_owner`。
- pipeline 没有通用数据、alpha、统计、组合、成本和执行实现。
- 重复研究脚本与当前说明已经清理，冻结历史证据仍可按原哈希验证。
- pipeline 的 Python 行数、巨型文件、长函数和复杂度预算随真实删除同步下调。
- 六个子模块和根工作区的 lint、类型、单测、wheel smoke、严格契约冒烟与 workspace doctor 全部通过。
- 每个 owner PR、pipeline PR 和根 gitlink PR 都已经合并。远端功能分支按 pre-push guard 审计保留政策保留（guard 禁止删除远端功能分支），本地 worktree 与临时分支已清理。

## 约束与非目标

- 不以一次大搬家完成全部迁移，每轮只处理一个可回滚的垂直切片。
- 不通过新的 re-export、别名包或 `PYTHONPATH` fallback 延长兼容期。
- 不为统一当前名称而改写历史 ADR、冻结证据、回执 schema 或旧版本矩阵。
- 不把外部策略仓库强行变成子模块。外部实现继续通过版本化文件接入，并在策略目录登记身份。
- 不以达到某个任意行数为完成标准。控制面职责纯度、单一所有权和重复实现清零优先于数字。

## 完成后的维护起点

R4 和 R6 已完成。`metrics.py` 已在 #66 下沉 `alpha-research`，`benchmarking.py` 已在 #67 删除并改向 `portfolio-backtester`，候选 OOS 职责已分别归入 `market-data-platform`、`alpha-research` 和 `strategy-app`。`style_factors` 的计算、回测和表现层也已归入三个明确 owner。后续恢复工作先读取[工作区路线图](roadmap.md)，再依据当前代码、机器账本和远端 `main` 复核，不沿用本页的历史计数判断剩余工作。
