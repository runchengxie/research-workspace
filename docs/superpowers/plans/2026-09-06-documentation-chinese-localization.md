# 文档中文化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成四个量化项目的 Markdown 文档中文化，覆盖现行说明、研究记录、历史归档、设计稿和执行计划，同时保留代码接口和历史证据的可复现性。

**Architecture:** 以仓库为边界拆分翻译工作，每个仓库使用独立 worktree、分支和 PR。先建立机器可读的语言审计清单，再按入口、现行文档、历史归档和设计记录分层翻译。`research-workspace` 只维护跨仓库索引和治理说明，具体项目文档由对应仓库维护。

**Tech Stack:** Markdown、Git、GitHub PR、Shell、Python 文档审计脚本、现有文档风格测试和链接检查工具。

**Spec:** [`docs/evidence/documentation-language-audit-2026-09-06.md`](../evidence/documentation-language-audit-2026-09-06.md)

## Global Constraints

- 中文是面向人的说明正文的默认语言。
- 仓库名、包名、Python 命名空间、CLI、路径、配置键、schema 字段、协议名称、代码块和许可证原文保留英文。
- 每次翻译必须同时校正文档中的 owner、当前状态、source of truth 和 superseded 关系。
- 历史归档保留原始日期、结论、证据路径和文件名，不重写历史事实。
- 文档正文使用中文标点，避免中英混排造成的多余空格、英文分号、英文引号和破折号。
- 避免模板化的“不是……而是……”句式、翻译腔和无意义的强调格式。
- 每个仓库单独建立 worktree、提交分支和 PR。合并到 `main` 后删除远端分支、本地分支和 worktree。
- 多个 agent 并行时按仓库和目录分配文件，不允许两个 agent 同时修改同一份文档。

---

### Task 1: 建立全量语言审计清单

**Files:**
- Create: `scripts/audit_documentation_language.py`
- Create: `docs/evidence/documentation-language-inventory-2026-09-06.json`
- Modify: `tests/test_documentation_language_audit.py`

- [ ] **Step 1: 定义扫描范围**

扫描 Git 已跟踪的 `README.md`、`AGENTS.md` 和所有 `.md` 文件，排除 `.git`、`.venv`、`.pytest_cache`、构建目录和 Git 子模块工作树。记录仓库、相对路径、文档类别、字符统计、语言分类和是否包含状态元信息。

- [ ] **Step 2: 增加可重复的分类规则**

分类至少包括 `entry`、`index`、`active`、`evidence`、`archive`、`plan`、`spec`。语言状态至少包括 `chinese-primary`、`mixed`、`english-primary` 和 `code-heavy`，避免单纯按英文字符数量误判代码示例较多的中文文档。

- [ ] **Step 3: 编写测试**

测试临时 Markdown 文件的分类、代码块忽略、中文正文识别、归档路径识别和 JSON 输出字段完整性。

- [ ] **Step 4: 生成基线**

运行 `python scripts/audit_documentation_language.py --json docs/evidence/documentation-language-inventory-2026-09-06.json`，并把审计摘要同步到语言审计报告。

- [ ] **Step 5: 提交**

提交信息使用 `docs: add documentation language inventory`。

### Task 2: 统一文档语言规范和自动检查

**Files:**
- Create: `docs/documentation-language-style.md`
- Modify: `tests/test_documentation_entrypoints.py`
- Modify: 相关仓库已有的文档风格测试

- [ ] **Step 1: 写明翻译规则**

明确正文语言、术语首次出现方式、代码块保留规则、中文标点、链接文本、历史文档元信息和英文技术名词规则。

- [ ] **Step 2: 扩展入口文档检查**

入口文档检查中文标题、中文简介、迁移状态、owner、阅读路径和有效链接。检查应只约束面向新人和维护者的入口，不要求历史英文证据文件立即达到相同阈值。

- [ ] **Step 3: 增加禁用样式检查**

检查正文中的英文分号、英文引号、孤立的英文状态句、连续多个英文说明段，以及未经说明的 `source of truth`、`owner`、`status` 等元信息。代码块、表格中的字段名和链接目标不参与检查。

- [ ] **Step 4: 在四个仓库分别运行**

运行各仓库既有测试，再运行文档审计和链接检查。发现规则与历史证据冲突时，在审计清单中记录例外，不直接删除历史内容。

### Task 3: 翻译 `research-workspace` 当前入口和治理文档

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `ARCHITECTURE.md`
- Modify: `docs/README.md`
- Modify: `docs/governance/README.md`
- Modify: `docs/quality-governance.md`
- Modify: `docs/version-matrix.md`
- Modify: `docs/migrations/*.md`
- Modify: `docs/evidence/*.md` 中仍作为当前依据的文件

- [ ] **Step 1: 先校正工作区当前定位**

统一写明 `research-workspace` 处于 sunset 过渡期，只负责集成、版本锁定、兼容性检查、契约冒烟测试和迁移导航。新功能进入 `market-data-platform`、`quant-platform` 或 `quant-research`。

- [ ] **Step 2: 翻译当前治理和迁移文档**

保留仓库名、命令和路径，翻译 owner、发布、回滚、兼容性和开发流程说明。

- [ ] **Step 3: 校正旧子模块说明**

每个旧子模块文档都标明当前 owner、迁移目标、是否仍是权威来源和替代文档路径。

### Task 4: 翻译 `market-data-platform` 文档

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/README.md`
- Modify: `docs/l2-ingestion-gate.md`
- Modify: `docs/l2-special-event-semantics.md`
- Modify: `docs/operations/*.md`
- Modify: `docs/superpowers/plans/*.md`
- Modify: `docs/superpowers/specs/*.md`
- Modify: `docs/archive/**/*.md`
- Modify: `scripts/systemd/README.md`

- [ ] **Step 1: 翻译数据平台入口和操作说明**

先完成新人路径、数据契约、数据生命周期、质量治理、凭证、备份、发布和分钟数据操作文档。

- [ ] **Step 2: 翻译 L2 和分钟数据技术文档**

保留事件字段、交易所术语、数据源名和命令，翻译处理流程、质量判断和故障恢复步骤。

- [ ] **Step 3: 翻译计划、设计和归档**

在每份历史计划和设计稿顶部补充中文状态，说明它是已完成、已取代、仍有效还是仅保留为审计记录。

### Task 5: 翻译 `quant-platform` 文档

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/README.md`
- Modify: `docs/data/**/*.md`
- Modify: `docs/alpha/**/*.md`
- Modify: `docs/concepts/**/*.md`
- Modify: `docs/execution/**/*.md`
- Modify: `docs/microstructure/**/*.md`
- Modify: `docs/orchestration/**/*.md`
- Modify: `docs/superpowers/plans/*.md`
- Modify: `docs/superpowers/specs/*.md`

- [ ] **Step 1: 翻译平台边界和新人路径**

说明公开通用能力、私有研究边界、数据平台依赖、回测、组合、风险、执行模拟和产物契约。

- [ ] **Step 2: 翻译回测和组合技术文档**

统一 benchmark、tracking error、turnover、sleeve、overlay、optimizer 等术语的中文解释，并保留英文术语作为代码和接口检索关键词。

- [ ] **Step 3: 翻译 alpha、微观结构和编排文档**

重点处理现金流发布、因子风险模型、模型选择、信号漂移、研究产物和质量门禁。

### Task 6: 翻译 `quant-research` 当前研究文档

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/README.md`
- Modify: `docs/dev/**/*.md`
- Modify: `docs/governance/**/*.md`
- Modify: `docs/research/**/*.md`
- Modify: `docs/daily-watch20-*.md`
- Modify: `research/evidence/*.md`
- Modify: `research/experiments/**/*.md` 中仍被当前 catalog 或报告引用的文件

- [ ] **Step 1: 翻译仓库入口和开发流程**

写清策略身份、实验、模型选择、私有配置、产物交接和 `market-intel` 的消费边界。

- [ ] **Step 2: 翻译现金流和 DailyWatch20 文档**

统一现金流指数、PIT、ML ranking、benchmark-relative overlay、Top-K、等权、D11-H5 和分批调仓的中文解释。

- [ ] **Step 3: 翻译当前证据和研究结论**

保留实验日期、样本区间、数据版本、指标名称和结果文件名，翻译研究目的、方法、结论、限制和下一步。

- [ ] **Step 4: 处理继承文档的归属**

`docs/market-data-platform/`、`docs/alpha-research/`、`docs/strategy-app/` 和 `docs/strategy-research/` 中的文件逐份标记为当前文档、兼容性副本、历史归档或待迁移文档。只有仍由 `quant-research` 维护的内容继续在本仓库翻译和更新。

### Task 7: 翻译全部历史 archive 文档

**Files:**
- Modify: 四个仓库所有 `archive/`、`research/experiments/**/archive/` 和历史证据目录中的 Markdown 文件
- Create: 各仓库对应的历史文档索引或状态清单

- [ ] **Step 1: 建立历史文档清单**

记录文件路径、日期、原始语言、原 owner、当前 owner、当前状态、替代文档和是否含有不可改写的审计证据。

- [ ] **Step 2: 先写中文摘要**

每份文件先补充完整中文摘要和当前有效性，再决定是否翻译全文。这样可以先保证新人能理解历史背景，也能降低大批旧文档同时改写的风险。

- [ ] **Step 3: 翻译仍有引用价值的全文**

对仍被当前 README、catalog、报告或测试引用的文件完成全文翻译。纯历史草稿保留原文，并补充中文摘要和归档状态。

- [ ] **Step 4: 清理历史文档中的失效链接**

链接失效时保留原始路径并添加当前替代链接，不修改历史结果中的文件名、commit hash 或数据版本。

### Task 8: 统一术语、链接和状态元信息

**Files:**
- Create: `docs/glossary.md` 或各仓库对应的术语表
- Modify: 四个仓库的文档索引和交叉链接
- Modify: 重复的 `docs/*/README.md`

- [ ] **Step 1: 建立术语表**

统一 PIT、as-of、point-in-time、benchmark、overlay、tracking error、turnover、sleeve、artifact、receipt、owner、source of truth、superseded 等术语。

- [ ] **Step 2: 统一文档状态**

使用中文说明文档状态，代码和自动化需要读取的字段保持稳定。每份索引页标注当前入口、历史入口和已取代入口。

- [ ] **Step 3: 检查交叉仓库链接**

确保旧路径能跳转到当前仓库文档，新增链接使用稳定的仓库相对路径或明确的 GitHub 链接。

### Task 9: 分仓库验证、提交和发布

**Files:**
- Modify: 各仓库文档测试和 CI 配置
- Create: 各仓库翻译完成报告

- [ ] **Step 1: 为每个仓库创建独立 worktree**

使用分支 `docs/chinese-localization-<repo>`，agent 只修改对应仓库的文件。

- [ ] **Step 2: 运行文档检查**

执行语言审计、Markdown 链接检查、现有文档测试和仓库既有质量门禁。对历史文件的例外记录在清单中，不通过删除文件绕过检查。

- [ ] **Step 3: 提交独立 PR**

每个仓库一个或多个按主题拆分的 PR，PR 描述列出翻译范围、保留英文范围、历史文档处理方式和测试结果。

- [ ] **Step 4: 合并后清理**

PR 合并到 `main` 后删除远端分支、本地分支和 worktree。回到 `research-workspace` 更新文档索引和审计基线。

- [ ] **Step 5: 生成最终报告**

重新运行全量审计，报告英文主导文件、混合文件、允许保留英文文件和未处理例外，确保所有入口文档达到中文优先要求。

## 完成标准

- 四个仓库的根目录 `README.md`、`AGENTS.md` 和 `docs/README.md` 均以中文说明为主。
- 当前有效的操作、架构、研究、回测、组合、风险、执行和数据契约文档均完成中文正文。
- 所有 archive 文档至少有中文摘要、状态和当前参考链接。
- 所有仍被当前代码、catalog、README 或报告引用的历史文档完成全文翻译或明确标注保留英文的理由。
- 代码标识、命令、路径、schema、证据文件名和许可证原文保持可执行、可检索和可复现。
- 语言审计、链接检查和各仓库原有测试通过。
- 每个仓库的改动都通过独立 worktree、PR 和 `main` 合并流程完成。
