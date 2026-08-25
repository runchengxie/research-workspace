# 从 research-workspace 撤回重复牛门线实现

## 目标

让 `research-workspace` 不再承载牛门线的早期重复实现和策略登记，保留独立 `niu-men-line-strategy` 作为牛门线研究代码与 Dashboard 快照的唯一来源，同时不改写 Git 历史、不影响其他策略和工作区治理能力。

## 当前重复内容

工作区中存在两层牛门线内容：

1. 顶层 `strategy-research` 登记：策略目录、假设、策略规格、实验说明和 catalog 条目，来自提交 `2dd943b6`。
2. `strategy-app` 子模块实现：`strategy_app.niu_men_line` 的指标、事件研究、合同、测试和应用目录说明，来自提交 `8b78981`，后续提交还包含其他无关改动。

当前独立仓库 `niu-men-line-strategy` 已经提供更完整的策略研究、全市场 OOS 和 `research_snapshot.v2` 导出能力。保留两套实现会造成策略规格、研究入口和维护门禁重复。

## 决策

- `niu-men-line-strategy` 是牛门线策略研究和 Dashboard 快照的唯一代码来源。
- `research-workspace` 删除牛门线的当前策略登记和顶层研究入口。
- `strategy-app` 删除牛门线早期实现、专属测试和当前应用目录说明。
- 不回退 `strategy-app` 整个 gitlink，因为该时间段包含 DailyWatch20 等其他有效改动。
- 不删除历史提交、不修改外部 `niu-men-line-strategy`、不修改研究结论文件的 Git 历史。
- `research-workspace` 中的通用策略治理、其他策略和数据/回测/执行边界保持不变。

## 修改范围

### strategy-app

- 删除 `src/strategy_app/niu_men_line/` 四个实现文件。
- 删除 `tests/test_niu_men_line.py`。
- 从 `README.md` 和 `docs/application-catalog.md` 删除牛门线当前应用族及研究项说明。
- 保留 `docs/quality-gates.md` 中关于历史 baseline 的记录，并新增撤回说明，避免篡改历史事实。
- 重新运行维护性基线和完整门禁，确认删除不会造成其他指标增长。

### research-workspace

- 删除 `strategy-research/strategies/niu_men_line/` 下的说明、假设和规格文件。
- 删除 `strategy-research/experiments/niu_men_line/README.md`。
- 从 `strategy-research/README.md` 和 `strategy-research/catalog.json` 删除牛门线条目。
- 从 `tests/test_strategy_research_catalog.py` 的期望集合删除 `niu_men_line`。
- 更新 `strategy-app` gitlink 到删除 NML 后的提交。
- 在跨仓库文档中记录独立 `niu-men-line-strategy` 是外部研究来源，不把它加入现有 workspace submodule 图。

## 验收标准

- `strategy-app` 源码、测试和当前应用目录不再引用 `strategy_app.niu_men_line`。
- `research-workspace` 当前 catalog 和策略地图不再列出牛门线。
- workspace catalog 测试通过，其他策略条目保持原样。
- `strategy-app` 的完整本地门禁通过，或在依赖/环境阻塞时给出明确证据。
- `research-workspace` 的相关质量检查通过。
- 独立 `niu-men-line-strategy` 仓库和 `research_snapshot.v2` 不被修改。

## 不在本次范围

- 不删除任何 Git 历史提交或远端分支。
- 不修改独立 Niu Men 的指标、信号、回测、OOS 和快照 schema。
- 不修改 T0 Dashboard 的前端实现，本次撤回只更新 workspace 归属。
- 不把独立 Niu Men 新增为 `research-workspace` 子模块。
