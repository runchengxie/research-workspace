# 文档审阅记录

审阅日期：2026-09-02

审阅范围是当前 `research-workspace` 工作区、当前子模块中的入口文档，以及 `~/data` 的
数据说明。`production/releases/` 下的历史快照不在本次修改范围内。

## 已完成的调整

- 根 `README.md` 收缩为工作区定位、仓库职责、数据边界、快速开始、检查命令和文档入口。
- 根 `AGENTS.md` 修正为八个子模块，并确认 `strategy-research` 的子模块身份。
- `docs/README.md` 改为按使用场景和主题导航，不再维护动态资产数量和运行状态。
- 新增 `docs/documentation-style.md`，统一中文表达、标点、事实来源和审阅步骤。
- `docs/data-path-migration-map.md` 补充根目录 `challenger_entry*` 已移除、代码直接读取规范目录的当前事实。
- `~/data` 增加 artifacts、staging、archive 和 strategy-pipeline 的中文入口说明。
- `~/data/deep-learning-tick-data-prediction/.venv` 已移到 `/home/richard/code/.venvs/`，
  源码项目的 `.venv` 入口继续可用。

## 审阅范围与处理方式

当前 `docs/` 有 121 个 Markdown 文件，其中 62 个属于 active 文档，其他文件属于 archive、
证据、计划或设计记录。active 文档逐项检查了入口、链接、路径、命令和明显的中文表达问题。

历史记录保留原有日期、状态和证据语义。代码示例、JSON、YAML、命令、路径、配置键和 API
名称保留必要的英文标点，避免为了统一中文标点而改动可执行内容。

## 风格扫描结果

针对 active Markdown 文件的初步扫描结果：

| 项目 | 文件数 |
| --- | ---: |
| active Markdown | 61 |
| 含 ASCII 双引号 | 13 |
| 含分号 | 6 |
| 含加粗格式 | 0 |
| 含破折号 | 0 |
| 命中先否定再转折句式 | 1 |
| `last_verified` 早于 2026-08-31 | 18 |

双引号和分号大多位于代码示例、配置片段或历史引用中。带日期的 `last_verified` 需要在
相应事实重新核对后再更新，不能只为统一日期而批量改写。

## 后续维护规则

- 新增当前做法时更新 active 入口，并把阶段记录放入 archive 或 evidence。
- 动态状态写入 manifest、catalog、receipt 或机器清单，README 只解释如何查找和使用。
- 修改路径、命令或配置时，同时搜索代码、服务、测试和文档引用。
- 每次文档改动后检查相对链接和关键路径，不修改历史 release 快照。
