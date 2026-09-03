# strategy-pipeline-internal 退役实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `strategy-pipeline-internal` 的活跃能力连同测试、配置和文档迁移到明确的 owner 仓库，最终让 `research-workspace` 在没有 internal checkout、凭证或权限的环境中正常运行，并冻结 internal。

**Architecture:** 采用按领域拆分的垂直切片，每个切片同时迁移实现、测试、配置、文档和 workspace 集成证据。公共 `strategy-pipeline` 只承载无领域知识的控制面，数据、研究证据、策略应用、回测组合和执行能力分别由 owner 仓库维护。每个切片合并后立即更新归属清单和依赖关系，最后再移除 internal 的剩余编排层。

**Tech Stack:** Python 3.11+、uv、pytest、Markdown、Git submodule、GitHub Actions、`gh` CLI。

**Spec:** `docs/superpowers/specs/2026-09-03-strategy-pipeline-internal-retirement-design.md`

## Global Constraints

- 公共仓库不得包含策略名称、策略阈值、模型选择、研究结论、provider SDK 初始化、凭证、真实数据路径或私有运行配置。
- 每个切片必须同时完成实现、测试、配置、fixture、schema、运行命令和文档的 owner 归属。
- 不通过扩大测试排除范围来掩盖未迁移功能。
- 历史材料必须保留来源、时间和恢复说明，并明确标注不可作为当前运行入口。
- 所有仓库变更遵循建立 worktree、实现与验证、创建 PR、合并 main、删除分支、删除 worktree 的流程。
- 每个 PR 合并后重新生成代码、文档、依赖和 artifact lineage 清单。
- 每个阶段都必须使用合成 fixture 和 clean-room 检查，禁止依赖私有凭证或真实数据路径。

---

## 文件和边界总览

| 仓库 | 主要修改位置 | 责任 |
| --- | --- | --- |
| `research-workspace` | `docs/ownership/`、`docs/contracts/`、`docs/migrations/`、`tests/`、`pyproject.toml`、`.gitmodules`、CI 配置 | 跨仓契约、归属清单、兼容矩阵、集成测试和最终退役记录 |
| `market-data-platform` | provider、PIT、资产发布模块及其测试、配置和文档 | 数据源、provider、PIT 和平台资产 |
| `alpha-research` | AFML、特征、模型、信号、诊断和证据模块及其测试和文档 | alpha 与研究证据语义 |
| `portfolio-backtester` | allocation、backtest、cost、capacity、exposure、positions 模块及其测试和文档 | 组合与回测语义 |
| `quant-execution-engine` | targets、risk、order、broker、execution audit 模块及其测试和文档 | 执行交接和审计 |
| `strategy-app` | DailyWatch20、Hotsector、StyleReplica、D11-H5、policy、campaign 和应用入口 | 策略应用与决策解释 |
| `strategy-research` | experiment runner、研究配置、试验账本和历史研究材料 | 研究实验生命周期 |
| `strategy-pipeline` | `src/strategy_pipeline/control_plane/`、公共 API 文档和 clean-room fixture | 无领域知识的 request、artifact、receipt、publication、handoff |
| `strategy-pipeline-internal` | 迁移期间的兼容层，最后只保留临时组合逻辑和归档说明 | 过渡层，不产生新的领域能力 |

每个 owner PR 都必须引用 internal 中的原路径、迁移后的路径、删除或归档路径，以及对应的测试和文档证据。不得用只导出旧模块的 facade 代替实际迁移。

## 依赖顺序

1. 先在 `research-workspace` 建立 manifest、contract 和集成测试基线。
2. 迁移数据与研究证据，因为后续回测和策略应用依赖它们的字段与 lineage。
3. 迁移组合、回测和执行交接，固定 `targets.json`、positions 和报告的 producer、consumer 与 schema。
4. 迁移策略应用和研究实验，确保策略专属逻辑离开公共控制面。
5. 收敛 internal 的临时编排和兼容路径。
6. 最后让 workspace 脱钩，完成敏感信息审计、冻结标签和只读归档。

### Task 1: 建立可追踪的迁移基线

**Files:**
- Create: `docs/migrations/strategy-pipeline-internal-migration-manifest.md`
- Create: `docs/migrations/strategy-pipeline-internal-dependency-map.md`
- Create: `tests/test_strategy_pipeline_internal_migration_manifest.py`
- Modify: `docs/superpowers/specs/2026-09-03-strategy-pipeline-internal-retirement-design.md`
- Modify: `docs/README.md`

**Interfaces:**
- Consumes: internal `docs/internal/documentation-ownership-inventory.md`、`pyproject.toml`、`src/strategy_pipeline_internal/`、`tests/`、`scripts/` 和 `configs/` 的当前树。
- Produces: 机器可读的模块、文档、脚本、配置和依赖记录，字段包含 `source_path`、`owner_repo`、`target_path`、`status`、`test_evidence`、`doc_evidence`、`archive_reason` 和 `removal_condition`。

- [ ] **Step 1: 编写失败测试**

  测试读取 manifest，验证每条记录都有合法状态和 owner，`planned` 必须有目标路径，`complete` 必须同时填写测试与文档证据，且不存在重复的 active owner。

- [ ] **Step 2: 运行测试确认基线不通过**

  Run: `uv run pytest tests/test_strategy_pipeline_internal_migration_manifest.py -q`

  Expected: FAIL，因为 manifest 和校验器尚未创建。

- [ ] **Step 3: 创建清单和校验逻辑**

  从 internal 当前 main 生成全量清单，覆盖 197 个 Python 源文件、180 个测试文件、34 个脚本、21 个配置文件和 114 份 ownership 文档。对现有 `planned`、`private`、`archive` 项逐条补充判断，不改变仍受保护的策略内容。

- [ ] **Step 4: 运行基线测试和清单检查**

  Run: `uv run pytest tests/test_strategy_pipeline_internal_migration_manifest.py -q`

  Expected: PASS，且输出未解释的 `planned`、缺少 owner 的 active 项和重复 producer 数量。

- [ ] **Step 5: 提交**

  ```bash
  git add docs/migrations docs/superpowers/specs docs/README.md tests/test_strategy_pipeline_internal_migration_manifest.py
  git commit -m "docs: establish internal migration manifest"
  ```

### Task 2: 迁移数据、PIT、provider 和研究证据

**Files:**
- Modify: `market-data-platform/src/`、`market-data-platform/tests/`、`market-data-platform/docs/`
- Modify: `alpha-research/src/`、`alpha-research/tests/`、`alpha-research/docs/`
- Modify: `research-workspace/docs/contracts/`、`research-workspace/tests/`
- Remove or archive after replacement: internal `src/strategy_pipeline_internal/` 下的 provider、RQData、PIT、AFML、signal、feature、model 和 evidence 实现及对应 active 入口

**Interfaces:**
- Consumes: Task 1 的 manifest，以及 internal 中 `data_interface`、provider、PIT、AFML、研究协议和平台资产相关模块的现有签名。
- Produces: owner 仓库中的真实实现、合成 fixture、版本化 schema 和 lineage 记录。数据 producer 输出 owner 与版本，alpha consumer 读取稳定字段，workspace 测试验证二者兼容。

- [ ] **Step 1: 为每个迁移模块写行为测试**

  在目标仓库用合成数据覆盖 provider 选择、PIT 时间边界、字段缺失、AFML 输入输出和研究证据引用。测试名称必须带原 internal 模块名，便于清单追溯。

- [ ] **Step 2: 运行 owner 测试确认缺少实现**

  Run: `uv run pytest <target-repo>/tests -q`

  Expected: 新增的迁移测试因目标接口尚未实现而失败，失败信息包含具体模块和字段。

- [ ] **Step 3: 迁移实现和配置**

  将 provider 初始化、PIT 资产生产和数据恢复逻辑放入 `market-data-platform`，将 AFML、特征、模型、信号和证据语义放入 `alpha-research`。配置只读取环境变量或显式参数，合成测试不得访问私有服务。

- [ ] **Step 4: 迁移文档并建立链接测试**

  将 `docs/concepts/data-sources.md`、`pit-coverage.md`、`shared-hk-data-platform.md`、`providers.md` 归入 `market-data-platform`，将 `afml-lineage.md`、`research-protocols.md` 归入 `alpha-research`。workspace 保留原路径索引和 schema 链接。

- [ ] **Step 5: 运行测试与 lineage 检查**

  Run: `uv run pytest <target-repo>/tests -q` and `uv run pytest research-workspace/tests -q`

  Expected: owner 测试、workspace contract 测试和 producer→consumer lineage 检查全部 PASS。

- [ ] **Step 6: 分别提交 owner PR**

  每个仓库单独提交实现、测试、配置和文档，PR 合并后更新 Task 1 manifest，再删除 internal 中已经没有 active consumer 的原入口。

### Task 3: 迁移回测、组合和执行交接

**Files:**
- Modify: `portfolio-backtester/src/`、`portfolio-backtester/tests/`、`portfolio-backtester/docs/`
- Modify: `quant-execution-engine/src/`、`quant-execution-engine/tests/`、`quant-execution-engine/docs/`
- Modify: `research-workspace/docs/contracts/`、`research-workspace/tests/`
- Remove or archive after replacement: internal allocation、selection、turnover、capacity、exposure、positions、targets、risk、order、broker 和 execution audit active 模块

**Interfaces:**
- Consumes: Task 2 的数据字段和 lineage contract。
- Produces: `portfolio-backtester` 的组合与回测 API，`quant-execution-engine` 的 targets/risk/order/execution API，以及 workspace 可验证的 `targets.json`、positions、lineage 和回测报告 schema。

- [ ] **Step 1: 编写迁移行为测试**

  用固定合成行情和目标文件测试 allocation、turnover、cost、capacity、exposure、positions、targets 消费、风险拒绝、订单生成和执行审计。每个测试断言 producer、schema version 和 lineage 字段。

- [ ] **Step 2: 运行失败测试**

  Run: `uv run pytest <portfolio-backtester>/tests <quant-execution-engine>/tests -q`

  Expected: 新增测试先因目标 API 或 schema 尚未存在而失败。

- [ ] **Step 3: 实现 owner API**

  组合计算和回测报告只进入 `portfolio-backtester`，targets 消费、风险、订单、券商适配和执行审计只进入 `quant-execution-engine`。公共包仅复用通用 handoff 类型，不引入这些领域语义。

- [ ] **Step 4: 更新 workspace contract 和 smoke**

  在 workspace 写明 `targets.json`、positions、lineage 和 report 的字段、版本、生产方和消费方，并增加无 internal checkout 的端到端 smoke。

- [ ] **Step 5: 运行验证**

  Run: `uv run pytest <portfolio-backtester>/tests <quant-execution-engine>/tests research-workspace/tests -q`

  Expected: owner 测试和 workspace 集成 smoke PASS，且全仓搜索不再发现执行模块从 internal 导入。

- [ ] **Step 6: 分别创建、合并并清理 PR**

  按仓库分别提交并合并 PR，更新 manifest 和 dependency map，确认旧 consumer 已切换后删除对应 internal 模块或标记为历史归档。

### Task 4: 迁移策略应用和研究实验

**Files:**
- Modify: `strategy-app/src/`、`strategy-app/tests/`、`strategy-app/docs/`
- Modify: `strategy-research/src/`、`strategy-research/tests/`、`strategy-research/docs/`
- Modify: `research-workspace/docs/`、`research-workspace/tests/`
- Remove or archive after replacement: internal `daily_watch20_*`、`hotsector_*`、`d11_h5_*`、`style_replica_*`、`policy_*`、`promotion_*`、campaign spec 和策略研究入口

**Interfaces:**
- Consumes: Task 2 的 alpha/research evidence contract，以及 Task 3 的组合和执行 contract。
- Produces: `strategy-app` 可独立调用的策略应用入口与决策解释，`strategy-research` 可独立运行的 experiment runner、研究配置和试验账本。

- [ ] **Step 1: 为每类策略写迁移测试**

  覆盖 DailyWatch20、Hotsector、StyleReplica 和 D11-H5 的输入、配置校验、输出 schema、解释字段和失败行为。测试使用合成 fixture，不复制私有阈值或研究结论到公共仓库。

- [ ] **Step 2: 运行失败测试**

  Run: `uv run pytest <strategy-app>/tests <strategy-research>/tests -q`

  Expected: 新增测试在 owner 入口未完成前失败。

- [ ] **Step 3: 迁移实现和配置**

  将策略专属 policy、campaign、决策解释放入 `strategy-app`，将实验 runner、研究配置和账本放入 `strategy-research`。涉及 alpha 方法的函数调用 `alpha-research` 的公开 owner API。

- [ ] **Step 4: 迁移 16 份 planned 文档**

  将 `a-share-baseline.md`、`hk-selected.md`、`research/README.md`、四份 strategy research 说明和 `strategy-catalog.md` 迁入 `strategy-app`，将跨仓 metric 与 full reference 归入 workspace，将数据和 AFML 文档按 Task 2 归入对应 owner。每份原文保留来源索引、状态和新链接。

- [ ] **Step 5: 运行独立入口和 workspace smoke**

  Run: `uv run pytest <strategy-app>/tests <strategy-research>/tests research-workspace/tests -q`

  Expected: 两个 owner 的入口不再从 internal 导入，workspace smoke 在没有 internal checkout 时 PASS。

- [ ] **Step 6: 合并 PR 并更新迁移证据**

  每个 owner 仓库独立 PR，合并后更新 manifest、文档 ownership 和 dependency map，删除已切换的 internal active 入口。

### Task 5: 收敛 internal 临时编排层和公共边界

**Files:**
- Modify: `strategy-pipeline/src/strategy_pipeline/control_plane/`
- Modify: `strategy-pipeline/tests/`、`strategy-pipeline/README.md`
- Modify: internal `pyproject.toml`、`README.md`、`src/strategy_pipeline_internal/cli/`、`commands/`、`pipeline/`、`configs/`、`tests/`
- Modify: `research-workspace/docs/migrations/`、`research-workspace/tests/`

**Interfaces:**
- Consumes: Tasks 2–4 中已经合并的 owner API 和 workspace contracts。
- Produces: 公共包只保留 request、artifact reference、receipt、publication、handoff 和通用 runner，internal 只剩明确的组合调用、run 目录创建和配置读取。

- [ ] **Step 1: 生成剩余 active 模块报告**

  按 `src/strategy_pipeline_internal` 的每个模块记录 owner、迁移 commit、测试、文档和删除条件，报告中把 archive 与 active 分开。

- [ ] **Step 2: 增加边界测试**

  在公共包测试中断言不出现策略名、provider 初始化、真实路径、私有 URL、凭证和领域阈值。workspace 测试断言公共 CLI 使用 `strategy-pipeline`，内部 CLI 不作为公共入口。

- [ ] **Step 3: 删除重复实现和旧分支**

  删除已经迁移的 internal facade、旧 CLI 分支和重复配置，收紧 `pyproject.toml` 依赖到仍被剩余编排实际使用的 owner API。公共包不添加任何 internal 依赖。

- [ ] **Step 4: 运行全量边界验证**

  Run: `uv run pytest strategy-pipeline/tests research-workspace/tests -q` and `rg -n "strategy_pipeline_internal|strategy-pipeline-internal" strategy-pipeline research-workspace --glob '!docs/migrations/**'`

  Expected: 公共包 clean-room 测试 PASS，active 代码和配置中没有 internal 依赖，迁移报告中的剩余项都有 owner 与删除条件。

- [ ] **Step 5: 合并并清理 PR**

  公共包、internal 和 workspace 分别创建 PR，按依赖顺序合并，合并后删除远端和本地分支及对应 worktree。

### Task 6: workspace 脱钩、敏感信息审计和 internal 退役

**Files:**
- Modify: `pyproject.toml`、`uv.lock`、`.gitmodules`、`scripts/`、`.github/workflows/`、`tests/`
- Modify: `docs/migrations/strategy-pipeline-internal-migration-manifest.md`
- Create: `docs/migrations/strategy-pipeline-internal-retirement-record.md`
- Modify: `docs/README.md` 和相关 owner 链接索引
- Archive only: internal 根目录 README、恢复说明、冻结标签记录和历史材料索引

**Interfaces:**
- Consumes: Task 5 的剩余模块报告、所有 owner PR commit、workspace contract 和完整测试结果。
- Produces: 不依赖 internal 的 workspace 安装与运行流程、敏感信息审计报告、冻结标签、只读归档位置和最终 owner 记录。

- [ ] **Step 1: 写退役前失败检查**

  增加测试，扫描 `pyproject.toml`、锁文件、submodule、脚本、CI、active docs 和 imports，发现 internal 入口时失败。增加历史敏感信息扫描规则，区分 active code、archive 和合成 fixture。

- [ ] **Step 2: 运行检查确认仍有引用**

  Run: `uv run pytest tests -q`

  Expected: 在 internal 依赖尚未完全移除前，检查准确列出文件、行号和引用类别。

- [ ] **Step 3: 移除 workspace 依赖和运行入口**

  更新 `pyproject.toml`、`uv.lock`、`.gitmodules`、脚本和 CI，删除 internal 安装来源、gitlink、默认命令和 active 文档入口。保留迁移 manifest 和退役记录中的历史链接。

- [ ] **Step 4: 执行 clean-room 与完整测试**

  Run: `uv sync --locked --all-groups`，`uv run pytest tests -q`，各 owner 仓库完整测试，公共包 clean-room 安装测试，以及 `rg -n "strategy_pipeline_internal|strategy-pipeline-internal" . --glob '!docs/migrations/**' --glob '!docs/archive/**'`

  Expected: workspace、所有 owner 和公共包测试 PASS，active 文件无 internal 引用，扫描报告无凭证、私有 URL、真实数据路径或策略敏感信息。

- [ ] **Step 5: 写冻结和恢复记录**

  在 `strategy-pipeline-internal-retirement-record.md` 记录冻结日期、最后可用 commit、只读归档位置、最终 owner、恢复步骤、测试结果、敏感信息扫描结果和连续两个维护周期的 consumer 搜索结果。

- [ ] **Step 6: 创建最终退役 PR 并完成流程**

  创建 workspace 和 internal 的最终 PR，合并 main，创建冻结 tag，将 internal 设置为只读归档，删除远端与本地开发分支及 worktree。仓库可见性变更必须在 active consumer 清零且敏感信息审计通过后单独执行。

## 阶段验收清单

- [ ] manifest 中没有未解释的 `planned` 或 active `private` 项。
- [ ] 每个 active internal 模块都有 owner、迁移 commit、测试证据和文档证据。
- [ ] 每个 artifact 都有唯一 producer、consumer、schema 和 lineage 测试。
- [ ] 公共 `strategy-pipeline` 没有领域知识和私有依赖。
- [ ] `research-workspace` 的安装、CI、submodule、脚本和 active docs 不再引用 internal。
- [ ] clean-room、全仓测试、历史敏感信息扫描和连续两个维护周期的 consumer 搜索均通过。
- [ ] internal 有冻结 tag、只读归档说明和恢复路径。
