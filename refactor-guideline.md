## 总体判断

你的直觉基本是对的：**这个项目不是“烂”，但已经明显进入了“个人工程能力撑起来，团队维护会很难受”的阶段**。人类常见悲剧：代码还能跑，文档也很多，于是大家假装它很健康，直到新人打开第一个 2000 行文件开始怀疑职业选择。

我把你上传的四个仓库一起看了：

| 仓库                       |                            大致定位 | 我的判断                            |
| ------------------------ | ------------------------------: | ------------------------------- |
| `market-data-platform`   |   数据平台、港股/A 股数据、资产构建、RQData 工具链 | **债务最重，港股拆分主战场**                |
| `cross-sectional-trees`  |      研究、回测、组合、live/export 研究侧逻辑 | 结构方向清楚，但历史港股和研究脚本残留多            |
| `quant-execution-engine` | 执行引擎、broker、preflight、rebalance | 相对最好，但 CLI 和 LongPort 适配层需要继续收敛 |
| `research-workspace`     |               多仓集成、治理文档、归档/发布辅助 | 不应该承载业务逻辑，目前定位基本合理              |

我做了这些检查：项目结构、`pyproject.toml`、Ruff/Pyright 配置、维护文档、AST 级别的大文件/长函数统计、导入循环、港股相关代码分布、一次性脚本、兼容入口、配置生命周期，以及仓库自带的治理脚本。四个仓库 `compileall` 都通过，语法层面没有明显损坏。

限制也说清楚：我没有在当前环境完整 `uv sync` 后跑全量 Ruff / Pyright / pytest，因为依赖环境没有完整同步。下面判断主要来自静态分析、项目自带维护脚本和源码结构。够判断维护风险，但不能替代一次正式 CI 审计。

---

# 结论一：仓库级设计还可以，模块级维护债务明显

这套项目的**大方向设计其实不差**：

* `market-data-platform` 管数据生产、数据资产、行情/基础数据接入。
* `cross-sectional-trees` 管研究、回测、信号、组合、导出。
* `quant-execution-engine` 管执行、broker、preflight、rebalance。
* `research-workspace` 管集成、治理、版本映射、归档。

这个边界是合理的。问题主要出在仓库内部：很多模块承担了太多职责，历史兼容代码和新主线代码还混在一起，lint/typing 覆盖靠排除项维持体面。说得不客气一点：**文档治理很强，但债务没有因为被写进文档就自动消失**。现实世界真是冷酷，连 YAML 都拯救不了大函数。

---

# 结论二：Ruff / Pyright 检查确实不够细致，尤其是 MDP 和 CST

## `market-data-platform`

这是维护风险最高的仓库。

当前数据平台大概有：

* Python 文件：160 个
* Python 代码行：约 63,892 行
* `src` 代码行：约 55,151 行
* `hk_assets`：44 个文件，约 25,901 行
* `hk_depth`：25 个文件，约 7,770 行
* `release_tools`：约 5,028 行

当前质量覆盖大致是：

| 检查         |    当前覆盖 |
| ---------- | ------: |
| Ruff 覆盖    | 约 60.3% |
| Pyright 覆盖 | 约 36.7% |

这说明一个很直接的问题：**最需要检查的复杂港股代码，很多还在 exclude 或半 exclude 状态里**。

几个明显热点文件：

| 文件                                                                   |   行数 | 问题                        |
| -------------------------------------------------------------------- | ---: | ------------------------- |
| `src/market_data_platform/hk_assets/asset_health.py`                 | 2791 | 体积过大，健康检查、模型、渲染、报告混在一起    |
| `src/market_data_platform/release_tools/hk_asset_workflow.py`        | 1938 | workflow 太厚，计划、执行、修复、报告耦合 |
| `src/market_data_platform/hk_assets/audit_assets.py`                 | 1819 | audit 逻辑过重，检查和输出耦合        |
| `src/market_data_platform/hk_depth/downloader.py`                    | 1760 | 下载、状态、quota、存储、CLI 适配混在一起 |
| `src/market_data_platform/cli.py`                                    | 1627 | CLI 聚合过大                  |
| `src/market_data_platform/hk_assets/mirror_financial.py`             | 1613 | 单文件业务流程过长                 |
| `src/market_data_platform/hk_assets/mirror_workflow.py`              | 1538 | workflow 层继续膨胀            |
| `src/market_data_platform/providers/tushare_a_share_fundamentals.py` | 1502 | A 股 provider 侧也有复杂度风险     |

我还发现一个内部导入循环：

```text
market_data_platform.providers.tushare_a_share_clean
  -> market_data_platform.providers.tushare_a_share_quality
  -> market_data_platform.providers.tushare_a_share_clean
```

这个循环不一定马上炸，但它是维护臭味。Provider 质量检查和清洗逻辑应该拆一个共同的纯函数/模型模块出来，避免互相引用。

### 对 MDP 的判断

MDP 现在最需要做的是：

1. **先拆大模块，再提高 lint/typing 覆盖。**
2. **先把港股边界冻结，再拆 repo。**
3. **不要现在直接删兼容入口。**

直接删会制造事故。港股这部分已经有很多历史入口，例如：

* `hkdata`
* `rqdata-hk-depth`
* `rqdata-tick`
* `rqdata-hk-assets`
* `src/hk_data_platform/**`

这些应该先进入“兼容层”，保留薄 wrapper，然后用治理脚本确认两轮发布周期没有真实依赖，再删。工程世界里，“感觉没人用”通常等价于“某个凌晨两点的批处理正在用”。

---

## `cross-sectional-trees`

这个仓库的 repo-level 方向清楚，但研究代码历史负担明显。

大致情况：

* Python 文件：239 个
* Python 代码行：约 71,409 行
* `src/scripts/tests` 统计：226 个 Python 文件，约 69,116 行
* 超过 800 行的文件：17 个
* 超过 1200 行的文件：4 个
* 超过 100 行的函数：101 个
* 超过 250 行的函数：5 个
* C901 复杂度 file-level ignore：9 个

主要热点文件：

| 文件                                        |   行数 | 问题                             |
| ----------------------------------------- | ---: | ------------------------------ |
| `src/cstree/execution_sim.py`             | 2329 | 仿真逻辑过大，需要拆模型、撮合、报告、状态          |
| `tests/test_pipeline_e2e.py`              | 1857 | E2E 测试过厚，失败定位会很痛苦              |
| `src/cstree/pipeline/eval.py`             | 1570 | 评估、报告、窗口逻辑耦合                   |
| `src/cstree/research/summarize_runs.py`   | 1280 | 研究汇总代码过长                       |
| `src/cstree/commands/tune.py`             | 1064 | CLI command 承担太多 orchestration |
| `src/cstree/pipeline/config.py`           |  980 | 配置模型和兼容逻辑风险较高                  |
| `src/cstree/pipeline/train_eval_stage.py` |  943 | stage 逻辑可拆                     |
| `src/cstree/portfolio.py`                 |  852 | 组合逻辑复杂度需要继续压缩                  |

几个长函数也比较刺眼：

| 函数                                                |  行数 |
| ------------------------------------------------- | --: |
| `commands/run_grid.py::run`                       | 332 |
| `pipeline/runner.py::prepare_research_context`    | 328 |
| `commands/linear_sweep.py::run`                   | 318 |
| `commands/tune.py::run`                           | 317 |
| `pipeline/eval.py::_evaluate_walk_forward_window` | 293 |

### CST 的港股状态

CST 里港股已经明显属于 legacy / archive / compatibility 状态。

配置 catalog 里：

| 分类                    | 数量 |
| --------------------- | -: |
| HK 配置                 | 91 |
| A 股配置                 | 13 |
| `legacy_research`     | 72 |
| `archived_provenance` | 15 |
| HK active-ish         |  0 |

这说明主线已经切到 A 股，港股研究基本应该被冻结。继续把港股历史研究配置放在主路径里，会让新维护者误判项目方向。

CST 里明显应该进入归档或拆出的港股代码包括：

```text
src/cstree/liveops/alloc_hk*.py
src/cstree/research/hk_*.py
configs/variants/*hk*
configs/sweeps/*hk*
```

其中 `cstree alloc-hk` 已经是 deprecated compatibility command，代码里也提示应该迁移到：

```text
cstree alloc
cstree export-targets
```

所以这个入口应该保留一段时间，但不能继续发展新功能。

---

## `quant-execution-engine`

这个仓库整体相对健康，至少相比前两个更像“可以被团队维护”的工程。

大致情况：

* Python 文件：75 个
* Python 代码行：约 23,442 行
* `src` 代码行：约 13,842 行
* Ruff/Pyright 覆盖比另外两个好
* 内部导入循环：0

主要热点：

| 文件                                                        |      行数 | 问题                           |
| --------------------------------------------------------- | ------: | ---------------------------- |
| `src/quant_execution_engine/cli.py`                       |    1421 | CLI 太厚                       |
| `src/quant_execution_engine/cli_parser.py::create_parser` | 314 行函数 | parser 巨大，但复杂度低，可拆命令注册       |
| `src/quant_execution_engine/broker/longport.py`           |    1042 | LongPort 适配器需要继续隔离 SDK/异常/转换 |
| `project_tools/smoke_operator_harness.py`                 |    1036 | smoke harness 应该逐渐产品化为包内模块   |
| `src/quant_execution_engine/renderers/table.py`           |     885 | 渲染层可继续拆                      |

这里有一些 `noqa` / `type: ignore`，但总体没到失控程度。`broker/base`、`execution_service`、`rebalance`、`preflight` 这些关键层的抽象方向是对的。

### 重要建议

**LongPort / 港股 broker 适配不要拆去港股业务 repo。**

它应该留在 execution engine 里，作为 broker plugin / adapter。港股数据平台和港股研究代码可以拆，但 broker adapter 属于执行系统。把 LongPort 搬到港股 repo 会让执行边界变脏，以后接别的市场或 broker 会更麻烦。

---

## `research-workspace`

这个仓库目前主要是：

* integration workspace
* submodule version map
* governance docs
* archive / demo / export scripts

这个定位是合理的。它不应该继续长业务逻辑。

我看到 `workspace_doctor.py` 在当前 zip 解压环境里会报子模块名字缺失，例如找不到 `market-data-platform`、`cross-sectional-trees`、`quant-execution-engine`。这个主要是 zip 解压目录名和真实 workspace 子模块布局不一致导致的，不代表项目本身坏了。

`research-workspace` 应该继续当“项目治理和冻结入口”，别让它变成第四个业务仓库。人类很喜欢把 workspace 变成垃圾抽屉，这正是文明衰败的微小证据之一。

---

# 是否符合 PEP 8 / SOLID / 高内聚低耦合？

## 仓库级别：基本符合

大方向上，职责分配合理：

* 数据平台负责数据
* 研究仓负责研究
* 执行引擎负责交易执行
* workspace 负责集成治理

这符合高层的单一职责和 bounded context 思路。

## 模块级别：不太符合

真正的问题在模块内部：

### 1. 单一职责不足

这些文件明显承担太多事情：

```text
market-data-platform:
  hk_assets/asset_health.py
  hk_assets/audit_assets.py
  release_tools/hk_asset_workflow.py
  hk_depth/downloader.py
  cli.py

cross-sectional-trees:
  execution_sim.py
  pipeline/eval.py
  pipeline/runner.py
  commands/tune.py
  commands/run_grid.py
  commands/linear_sweep.py

quant-execution-engine:
  cli.py
  cli_parser.py
  broker/longport.py
  project_tools/smoke_operator_harness.py
```

推荐拆分方式很清楚：

```text
模型 / DTO
检查逻辑
执行计划
外部 provider/client
状态管理
报告渲染
CLI adapter
```

CLI 文件最好只做参数解析和调用 service，不要塞业务流程。

---

### 2. 依赖倒置做得不均匀

`quant-execution-engine` 的 broker 抽象比较好，这是加分项。

`market-data-platform` 已经有一些 contract / manifest / registry / paths / artifact seam，但 HK 代码仍然大量引用平台内部 helper。拆 repo 前必须收敛这些依赖，否则拆出去之后会变成“新 repo 还要偷偷依赖旧 repo 内脏”，这就很有开源项目常见诈骗感。

`cross-sectional-trees` 也直接引用了不少 MDP 内部能力，例如：

```text
market_data_platform.data_providers
market_data_platform.rqdata_runtime
market_data_platform.symbols
```

这在当前多仓内可以接受，但对“冻结港股 repo”来说，需要明确哪些是稳定 API，哪些只是历史实现细节。

---

### 3. Open/Closed 原则一般

很多新增市场、新增 provider、新增 workflow 的方式，看起来仍然是去大函数、大 parser、大 workflow 里加分支。

典型症状：

* CLI parser 巨大
* workflow 函数巨大
* health/audit 构建过程巨大
* provider 和质量检查互相引用
* 配置兼容逻辑集中在少数大模块里

后续应该向 registry / plugin / protocol / dataclass config object 靠拢。

---

### 4. Interface Segregation 不够

MDP 的 public facade 暴露数量偏多，函数参数也偏多：

* MDP 有约 50 个 public facade exports
* 函数参数超过 10 个的函数有 50 个
* 最大参数数量达到 29 个

这类函数维护起来非常痛苦。建议逐步改成：

```python
@dataclass(frozen=True)
class BuildOptions:
    ...
```

或者拆成：

```text
Request
Plan
Result
Report
```

不要继续让函数签名像报关单。

---

# 一次性脚本和不必要功能

## CST 的一次性脚本最明显

这些脚本看起来更像研究探针或阶段性实验：

```text
scripts/a_share_500k_round_lot_probe.py
scripts/a_share_live_executable_oos_topk_probe.py
scripts/a_share_live_executable_variant_top10_probe.py
scripts/a_share_live_industry_cap_top10_probe.py
scripts/a_share_live_risk_control_grid.py
scripts/a_share_small_capital_robustness.py
```

建议分三类处理：

| 类别        | 处理方式                                 |
| --------- | ------------------------------------ |
| 已经沉淀为主线能力 | 移入 `src/cstree/research` 或 CLI 子命令   |
| 只是实验记录    | 移到 `docs/archive/research/`，保留输入输出说明 |
| 无复现价值     | 删除，但要在 changelog / manifest 记录       |

根目录 `scripts/` 不应该长期堆研究脚本。否则新人会以为它们都是正式入口，然后快乐地踩进沼泽。

---

## MDP 的 legacy CLI 不要马上删

这些入口已经进入 deprecated / blocked pending audit 状态：

```text
hkdata
rqdata-hk-depth
rqdata-tick
rqdata-hk-assets
src/hk_data_platform/**
```

建议流程：

1. 先做 usage inventory。
2. 保留 wrapper。
3. wrapper 打 deprecated warning。
4. 文档标注替代命令。
5. 两个 release 后再删除。
6. 删除时保留 migration note。

这类入口通常外部脚本、cron、CI、历史 notebook 会偷偷用。直接删很容易换来一场人类熟悉的“周一早上事故”。

---

## CST 的 HK 历史配置应该冷冻

HK 配置太多了，而且绝大多数已经是 legacy。建议只在主仓保留：

```text
configs/presets/hk.yml       # 明确 opt-in / restore reference
configs/catalog.csv          # 保留索引
docs/archive/hk-configs/...  # 历史说明
```

其余 legacy HK variants / sweeps 应该进入 archive 或 HK legacy repo。

---

## 小的陈旧命名

我看到 `artifacts/README.md` 里还有 `CSML` 旧命名。这个不严重，但应该修。旧名残留会让维护者怀疑“到底哪个包才是主线”，然后大家开始 Slack 考古，文明再次倒退。

---

# 我认为最需要优化的 P0 / P1 / P2

## P0：先把边界锁住

这一步比重构更重要。

### 1. 锁定 HK split boundary

MDP 已经有 `docs/hk-split-boundary.yml`，这很好。建议把它升级为 CI gate：

```text
任何新增 HK 代码必须进入 hk boundary manifest
任何非 HK 代码不得 import hk_assets / hk_depth
任何 HK 代码不得 import 非 seam 的 platform 内部模块
```

可以用：

* 自定义 AST import checker
* `import-linter`
* repo 自带 architecture governance script

目标是让边界变成机器检查，而不是靠人类记忆。靠人类记忆维护边界，等价于把仓库交给天气。

---

### 2. 冻结 deprecated 入口

冻结这些入口：

```text
hkdata
src/hk_data_platform/**
rqdata-hk-depth
rqdata-tick
rqdata-hk-assets
cstree alloc-hk
```

规则：

```text
只允许 bugfix / security / compatibility
不允许新 feature
不允许新 downstream dependency
不允许新增业务分支
```

---

### 3. 禁止新增 C901 ignore 和 Pyright exclude

CST 已经有 9 个 C901 file-level ignore。可以暂时接受历史债务，但必须加规则：

```text
no new C901 ignore
no new broad pyright exclude
no new compatibility wrapper without deprecation issue
```

否则“阶段性忽略”会变成“祖传忽略”。人类项目史上，这个结局非常稳定。

---

## P1：拆大文件

优先拆这些：

### MDP

```text
hk_assets/asset_health.py
  -> hk_assets/health/model.py
  -> hk_assets/health/checks.py
  -> hk_assets/health/render.py
  -> hk_assets/health/report.py

hk_assets/audit_assets.py
  -> hk_assets/audit/model.py
  -> hk_assets/audit/checks.py
  -> hk_assets/audit/render.py

release_tools/hk_asset_workflow.py
  -> release_tools/hk_asset_workflow/planning.py
  -> release_tools/hk_asset_workflow/execution.py
  -> release_tools/hk_asset_workflow/repair.py
  -> release_tools/hk_asset_workflow/reporting.py
  -> release_tools/hk_asset_workflow/state.py

hk_depth/downloader.py
  -> hk_depth/downloader/client.py
  -> hk_depth/downloader/state.py
  -> hk_depth/downloader/storage.py
  -> hk_depth/downloader/quota.py
  -> hk_depth/downloader/cli_adapter.py
```

### CST

```text
pipeline/eval.py
  -> pipeline/eval/metrics.py
  -> pipeline/eval/reporting.py
  -> pipeline/eval/orchestration.py

pipeline/train_eval_stage.py
  -> pipeline/train_eval/stage.py
  -> pipeline/train_eval/state.py
  -> pipeline/train_eval/outputs.py

execution_sim.py
  -> execution_sim/model.py
  -> execution_sim/engine.py
  -> execution_sim/fills.py
  -> execution_sim/reporting.py

commands/tune.py / run_grid.py / linear_sweep.py
  -> command layer only
  -> orchestration moved into service modules
```

### QExec

```text
cli.py
  -> cli/commands/*.py

cli_parser.py
  -> cli/parsers/base.py
  -> cli/parsers/rebalance.py
  -> cli/parsers/preflight.py
  -> cli/parsers/broker.py

broker/longport.py
  -> broker/longport/client.py
  -> broker/longport/mapper.py
  -> broker/longport/errors.py
  -> broker/longport/config.py
```

---

## P2：提高 lint / typing 覆盖

### 推荐目标

| 仓库        | 当前问题                                  | 下一阶段目标                     |
| --------- | ------------------------------------- | -------------------------- |
| MDP       | Ruff 约 60.3%，Pyright 约 36.7%          | Ruff ≥ 75%，Pyright ≥ 50%   |
| CST       | Ruff select 很窄，Pyright 只 include 稳定子集 | 先扩大 Ruff 规则，再模块级扩大 Pyright |
| QExec     | 相对较好                                  | 对核心模块启用更严格 Pyright         |
| Workspace | 顶层简单                                  | 保持轻量，不扩业务                  |

### Ruff 建议

CST 当前 Ruff select 偏保守，建议逐步扩到：

```toml
select = [
  "E",
  "F",
  "I",
  "UP",
  "B",
  "C4",
  "RET",
  "SIM",
  "RUF",
  "C90",
]
```

不要一次全仓硬切，会炸。建议按目录推进：

```text
第一批：纯模型、utils、contracts
第二批：pipeline 非 IO 模块
第三批：CLI / workflow
第四批：legacy HK / archive only
```

MDP 也类似，先把低风险 HK seam 模块纳入检查：

```text
hk_depth/storage.py
hk_depth/symbols.py
hk_assets/contracts.py
hk_assets/manifest.py
hk_assets/paths.py
hk_assets/registry.py
```

然后再处理 pandas-heavy / provider-heavy 文件。

### Pyright 建议

建议采用“ratchet”模式：

```text
每次 PR 不允许降低 Pyright included lines %
每次 release 至少提高一个小模块覆盖
新模块必须进入 Pyright include
legacy 模块只能减少 exclude，不能增加 exclude
```

QExec 可以对这些模块先开 strict：

```text
targets
risk
preflight
rebalance
execution_state
broker/base
execution_service
cli command service
```

MDP 的 strict 不要一上来压到 pandas / provider 重模块，会浪费大量时间在类型推断噪音里。先收 seam 和纯函数。

---

# 港股业务代码独立 repo：我建议拆成两个层次

你说“最终将港股部分相关的业务代码独立出来，并冻结成一个独立 repo”。这里要先拆清楚“港股业务代码”到底有两类。

## 第一类：港股数据平台代码

这是 MDP 里的：

```text
src/market_data_platform/hk_assets/**
src/market_data_platform/hk_depth/**
src/market_data_platform/hk_workflows.py
src/market_data_platform/release_tools/hk_asset_workflow*.py
```

这部分适合拆成：

```text
market-data-platform-hk
```

它是“港股数据资产 / 深度行情 / 发布工作流 / restore tooling”的 repo。

## 第二类：港股研究 / 分配 / 策略历史代码

这是 CST 里的：

```text
src/cstree/liveops/alloc_hk*.py
src/cstree/research/hk_*.py
configs/variants/*hk*
configs/sweeps/*hk*
historical HK research docs / outputs manifest
```

这部分不建议混进 `market-data-platform-hk`，除非你的目标是做一个完整的“港股历史项目冷冻仓”。

更干净的方式是：

```text
market-data-platform-hk      # 港股数据生产和资产工具
hk-research-legacy           # 港股研究、allocation、历史配置、复现说明
```

如果你坚持只要一个 repo，那这个 repo 应该叫类似：

```text
hk-legacy-stack
```

里面再分：

```text
data/
research/
configs/
docs/
tests/
```

但我不太推荐。数据平台和研究逻辑混在一起，未来维护边界会更糊。一个冷冻仓可以这么做，一个还想长期维护的仓库最好别这么做。

---

# 我建议的 HK repo 拆分方案

## 推荐目标结构：`market-data-platform-hk`

```text
market-data-platform-hk/
  pyproject.toml
  README.md
  FREEZE.md
  MAINTENANCE.md
  uv.lock

  src/
    market_data_platform_hk/
      __init__.py

      assets/
        health/
        audit/
        mirror/
        build/
        coverage/
        contracts.py
        manifest.py
        paths.py
        registry.py

      depth/
        downloader/
        storage.py
        symbols.py
        reconcile.py
        release_assets.py
        health.py

      workflows/
        asset_workflow/
          planning.py
          execution.py
          repair.py
          reporting.py
          state.py

      contracts/
        artifacts.py
        paths.py
        manifest.py
        provider_protocols.py

      cli/
        main.py
        assets.py
        depth.py
        health.py

  tests/
    unit/
    integration/
    fixtures/

  docs/
    split-boundary.md
    restore.md
    operations.md
    deprecations.md

  configs/
    hk/
      assets.yml
      depth.yml
      release.yml
```

### 包名建议

新包名建议用：

```text
market_data_platform_hk
```

不要继续把新 repo 的主包叫：

```text
market_data_platform.hk_assets
```

原因很简单：新旧包名重叠会让 import resolution 和 editable install 变得恶心。Python packaging 已经够像地雷阵了，没必要再加艺术性。

旧仓库可以保留 compatibility facade：

```python
# market_data_platform/hk_assets/__init__.py

try:
    from market_data_platform_hk.assets import ...
except ImportError as exc:
    raise ImportError(
        "HK asset tooling has moved to market-data-platform-hk. "
        "Install market-data-platform-hk or use the frozen legacy tag."
    ) from exc
```

这样老入口还能给出明确错误，不会安静地坏掉。

---

## CLI 命名建议

新 repo 主 CLI 建议：

```text
marketdata-hk
```

旧 CLI 只保留兼容：

```text
hkdata              # compatibility alias
rqdata-hk-depth     # compatibility alias
rqdata-hk-assets    # compatibility alias
rqdata-tick         # compatibility alias
```

新文档统一写：

```bash
marketdata-hk assets ...
marketdata-hk depth ...
marketdata-hk health ...
marketdata-hk release ...
```

旧命令只出现在 migration doc 里。

---

# HK 拆 repo 的具体步骤

## Step 1：先冻结版本

在现有三个主仓打 tag：

```text
market-data-platform: hk-freeze-YYYYMMDD
cross-sectional-trees: hk-freeze-YYYYMMDD
quant-execution-engine: hk-freeze-YYYYMMDD
research-workspace: hk-freeze-YYYYMMDD
```

同时写一个 version matrix：

```text
market-data-platform commit
cross-sectional-trees commit
quant-execution-engine commit
research-workspace commit
Python version
uv.lock hash
data artifact manifest hash
known restore commands
known smoke commands
```

这一步很重要。没有 freeze tag，拆 repo 后你会失去“到底从哪里来的”这个事实依据。然后大家开始靠记忆争论，像围着篝火讲神话。

---

## Step 2：把 HK surface 做成机器可验证 manifest

MDP 已经有 `docs/hk-split-boundary.yml`，workspace 也有 `hk-public-split-manifest.yml`。建议合并成一个权威 manifest：

```yaml
hk_split:
  private_data_platform:
    move:
      - src/market_data_platform/hk_assets/**
      - src/market_data_platform/hk_depth/**
      - src/market_data_platform/hk_workflows.py
      - src/market_data_platform/release_tools/hk_asset_workflow*.py

  legacy_research:
    archive_or_move:
      - cross-sectional-trees/src/cstree/liveops/alloc_hk*.py
      - cross-sectional-trees/src/cstree/research/hk_*.py
      - cross-sectional-trees/configs/**/*hk*

  compatibility:
    keep_temporarily:
      - src/hk_data_platform/**
      - hkdata
      - rqdata-hk-depth
      - rqdata-hk-assets
      - rqdata-tick
      - cstree alloc-hk

  execution:
    keep_in_quant_execution_engine:
      - quant_execution_engine/broker/longport.py
```

然后 CI 检查：

```text
manifest 里的 move 路径必须存在
新增 hk 路径必须注册
compat 路径必须有 deprecation owner
public-safe 路径不得包含真实 provider key、私有路径、真实标的池、真实交易记录
```

---

## Step 3：处理 seam 依赖

拆之前必须处理这些依赖：

```text
config_utils
data_providers
intraday_paths
pit_feature_stats
rebalance
release_tools
rqdata_cli_common
rqdata_runtime
symbols
```

对每个依赖做三选一：

| 类型      | 处理方式                                             |
| ------- | ------------------------------------------------ |
| 稳定通用能力  | 放到 `contracts/` 或 `platform_common/`             |
| HK 专属能力 | 移入 `market-data-platform-hk`                     |
| 原平台能力   | 让 HK repo 依赖 `market-data-platform>=x.y` 的公开 API |

我更建议新 HK repo 尽量少依赖旧 MDP。既然目标是“冻结”，依赖越少越好。

### seam API 最小化

建议只保留这些稳定 seam：

```text
ArtifactManifest
DatasetPathResolver
ProviderProtocol
TradingCalendarProtocol
SymbolNormalizer
ReleaseManifest
HealthReport
```

其余实现细节不要暴露。

---

## Step 4：先复制抽取，不要一上来重构到失控

拆 repo 时分两阶段：

### 阶段 A：mechanical extraction

用 `git filter-repo` 或 `git subtree split` 保留历史：

```text
只移动路径
只修 import
只修 package name
只修 pyproject / tests
不做业务逻辑重构
```

目标是得到一个可运行的 frozen repo。

### 阶段 B：内部重构

等 repo 独立跑通后，再拆：

```text
asset_health.py
audit_assets.py
hk_asset_workflow.py
downloader.py
```

不要把“拆 repo”和“重写业务逻辑”混在同一个 PR。那样 review 会变成一场宗教战争。

---

## Step 5：旧仓保留薄兼容层

在原 `market-data-platform` 里：

```text
market_data_platform/hk_assets/*
market_data_platform/hk_depth/*
hk_data_platform/*
```

应该变成薄 wrapper：

```text
import from market_data_platform_hk
emit DeprecationWarning
raise actionable ImportError when package missing
```

`pyproject.toml` 里的旧 console scripts 可以先保留：

```text
hkdata
rqdata-hk-depth
rqdata-tick
rqdata-hk-assets
```

但它们只调用新 CLI。

---

## Step 6：CST 里的港股研究单独处理

CST 的港股逻辑建议分两类：

### 冷冻保留

```text
src/cstree/research/hk_*.py
configs/variants/*hk*
configs/sweeps/*hk*
historical reports
```

这些可以进：

```text
hk-research-legacy
```

或者进入 archive tarball，加 manifest 和 restore instructions。

### 兼容但不发展

```text
src/cstree/liveops/alloc_hk*.py
cstree alloc-hk
```

这些应该明确：

```text
deprecated
bugfix only
no new capital allocation feature
no new HK data dependency
```

最终迁移到：

```text
cstree alloc
cstree export-targets
```

---

## Step 7：QExec 保持独立

`quant-execution-engine` 里的 LongPort 适配器留在原仓。

只需要导出这些给 HK legacy repo 参考：

```text
execution target schema
rebalance target schema
broker capability docs
paper/live safety docs
smoke command examples
```

不要把 broker SDK adapter 搬走。

---

# 拆分后的测试门槛

新 `market-data-platform-hk` 至少要有这些 gate：

```bash
python -m compileall -q src tests
ruff check src tests
pyright
pytest tests
marketdata-hk --help
marketdata-hk assets --help
marketdata-hk depth --help
```

还要有 dry-run 级别测试：

```text
不需要真实 RQData 凭据
不访问真实私有路径
使用 synthetic fixtures
验证 manifest / paths / report 输出
```

保留真实 provider 测试，但标记为：

```text
@pytest.mark.provider
@pytest.mark.private
```

默认 CI 不跑。

---

# 我会如何排序执行

## 第一周：只做冻结和边界

1. 打 `hk-freeze-YYYYMMDD` tag。
2. 生成 HK split manifest。
3. CI 加 import boundary check。
4. 所有 HK legacy CLI 加 warning。
5. 禁止新增 HK 功能进入主仓。
6. 修掉明显陈旧命名，例如 `CSML` 残留文档。

## 第二阶段：先拆 MDP HK

1. 抽出 `hk_assets`、`hk_depth`、`hk_workflows`、HK release workflow。
2. 新建 `market_data_platform_hk` 包。
3. 旧 MDP 保留 compatibility facade。
4. 让新 repo 独立 compile / lint / test。
5. 写 `FREEZE.md` 和 `MAINTENANCE.md`。

## 第三阶段：处理 CST HK research

1. 把 HK configs 从 active config tree 移到 archive。
2. 保留一个明确 opt-in 的 `hk.yml` restore reference。
3. `alloc_hk*.py` 冻结。
4. `hk_*.py` 研究脚本进入 `hk-research-legacy` 或 archive。
5. 主 CST 的默认路径彻底 A 股化。

## 第四阶段：逐步还质量债

优先顺序：

```text
MDP hk_asset_workflow.py
MDP asset_health.py
MDP hk_depth/downloader.py
CST pipeline/eval.py
CST execution_sim.py
CST commands/tune.py / run_grid.py / linear_sweep.py
QExec cli.py / cli_parser.py
```

---

# 最终建议

你这个项目的优化空间很明确：

1. **不要先追求“删代码爽感”。**
   先冻结、打 tag、建 manifest、加 boundary gate。删错 legacy 入口比保留一层薄 wrapper 更危险。

2. **港股数据平台先拆，港股研究历史后拆。**
   `market-data-platform-hk` 和 `hk-research-legacy` 最好分开。数据生产和策略研究混一个 repo，长期会继续变重。

3. **Ruff / Pyright 用 ratchet，不要全仓一次硬切。**
   MDP 先把 Ruff 从约 60% 拉到 75%，Pyright 从约 37% 拉到 50%。CST 先扩大 Ruff select，再扩大 Pyright include。

4. **大文件拆服务层，CLI 只做入口。**
   当前很多 CLI / workflow / health / audit 文件承担了太多业务职责，这是团队维护难的核心原因之一。

5. **QExec 留作执行边界，不要被港股拆分污染。**
   LongPort 属于 broker adapter，不属于 HK data/research repo。

6. **workspace 继续做治理，不要长业务。**
   它适合放 version matrix、split manifest、archive gate、readiness report，不适合继续塞业务脚本。

一句话判断：**这套项目值得救，而且已经有不错的治理基础；但它现在确实还带着很多“个人项目时代”的结构痕迹。先冻结港股边界，再拆 MDP HK repo，再归档 CST HK research，最后按模块还 lint/typing 和大文件债务。**
