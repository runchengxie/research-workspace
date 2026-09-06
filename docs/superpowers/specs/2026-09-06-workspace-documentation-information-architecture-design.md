# Workspace Documentation Information Architecture Design

> status: proposed
> owner: workspace
> last_verified: 2026-09-06
> source_of_truth: yes
> audience: human and agent

## 目标

重构 `research-workspace` 顶层仓库和八个子模块的文档体系，使人能够按任务找到最短阅读路径，使 AI 编码工具能够按模块和文档类型加载最小必要上下文。

本次工作包含文档移动、正文重写、入口瘦身、重复主题归集、历史材料分层和旧路径兼容指针。代码接口、数据格式、公开路径和历史证据语义不因文档整理而改变。

## 范围

纳入以下仓库：

| 层级 | 仓库 | 文档职责 |
| --- | --- | --- |
| 顶层 | `research-workspace` | 跨仓边界、契约、组合版本、工作区治理和发布流程 |
| 子模块 | `market-data-platform` | 数据资产、数据质量、采集发布和消费方式 |
| 子模块 | `deep-learning-tick-data-prediction` | tick/L2 数据、模型、训练运行和实验记录 |
| 子模块 | `alpha-research` | 特征、模型、信号、稳健性和 alpha 证据 |
| 子模块 | `portfolio-backtester` | 组合、回测、成本、容量、风险和执行模拟 |
| 子模块 | `strategy-research` | 策略身份、投资假设、生命周期、实验和证据导航 |
| 子模块 | `strategy-app` | 策略专用计算、冻结合同和研究应用操作 |
| 子模块 | `strategy-pipeline` | 运行编排、artifact、publication、receipt 和 `targets.json` |
| 子模块 | `quant-execution-engine` | 预演、风控、券商执行、对账和交易审计 |

不纳入本次范围：生产目录中的历史快照、外部 `market-intel` 卫星仓、源代码 API 重构、大型研究产物、凭证和数据目录内容。数据目录只在需要时补充入口链接，不复制其说明正文。

## 设计原则

### 一个主题一个权威入口

当前做法、当前状态、契约字段和操作命令各自只保留一个权威正文。其他文档只保留摘要、上下文和链接。机器可读事实继续由 JSON、YAML、schema、catalog、manifest 或生成脚本维护，Markdown 负责解释和导航。

### 按阅读任务分层

每个仓库的根 `README.md` 只回答项目定位、边界、最短安装或验证路径和文档入口。每个 `docs/README.md` 只承担本仓库的导航。详细正文按主题分类，不把当前说明、研究结果、迁移记录和历史计划混在同一层。

### 按生命周期隔离上下文

默认入口只指向 `active` 文档。稳定参考、证据快照、历史记录、设计和执行计划分别进入明确的 reference、evidence、archive 和 superpowers 路径。入口不会把这些目录中的每个文件平铺列出。

### 移动不破坏旧链接

正文迁移到新路径后，旧路径保留一页短兼容指针，包含新路径、原主题和文档状态。指针不复制正文，不作为新的权威入口。内部链接、测试和外部引用在迁移期间继续可解析。

### 子模块独立负责

每个子模块的文档由该子模块仓库提交和审阅。顶层只维护跨仓库事实和子模块文档入口，不把子模块内部命令、参数和实现说明复制到顶层。顶层在所有子模块提交完成后只更新 gitlink 和跨仓链接。

## 统一信息架构

顶层和子模块可以按实际需要省略空目录，但使用以下语义：

```text
README.md                 项目定位和最短入口
AGENTS.md                 AI/维护者协作规则和阅读顺序
docs/
  README.md               本仓库文档导航
  architecture/           边界、设计、ADR 索引和稳定架构参考
  concepts/               当前概念、术语和方法说明
  guides/                 面向读者的使用和接入指南
  operations/             安装、运行、检查、发布和故障处理
  reference/              API、配置、字段、产物和兼容性参考
  research/               当前研究问题、实验方法和结果入口
  governance/             质量、所有权、生命周期和维护规则
  archive/                历史记录、冻结材料和已结束迁移
  evidence/               带日期、哈希或机器生成的证据
  superpowers/
    specs/                已确认的设计文档
    plans/                实施计划
```

文档只放入最能表达其主要读者和维护责任的目录。一个页面同时涉及多个主题时，保留一个权威页面，其他主题页链接到它，不复制段落。

## 文档元信息

所有索引页、入口页、兼容指针和权威状态页使用短状态块：

```text
> status: active | reference | archived | superseded
> owner: <repository or workspace>
> audience: human | agent | both
> last_verified: YYYY-MM-DD
> source_of_truth: yes | no
> superseded_by: n/a | <relative path>
```

普通概念页、操作页和参考页不重复维护动态状态字段。它们由所属目录的 README 导航，正文中的事实必须能从代码、测试或对应机器文件核对。

## 各仓库目标结构

### 顶层 `research-workspace`

顶层 `docs/` 按跨仓主题重组：

- `architecture/`：`ARCHITECTURE.md` 的详细边界、ADR 索引和模块拆分记录
- `operations/`：bootstrap、workspace maintenance、platform workflow、release checklist、production update 和 runbook
- `contracts/`：跨仓 artifact、数据路径、数据质量和文件契约
- `governance/`：质量治理、版本矩阵、所有权、文档生命周期、维护性和废弃入口
- `research/`：跨仓研究方法、研究规格、证据门槛和当前研究导航
- `reference/`：术语表、框架支持矩阵和稳定技术参考
- `archive/`、`evidence/`、`superpowers/`：保持生命周期隔离，不进入默认阅读路径

根 `README.md` 和 `AGENTS.md` 压缩为定位、边界、阅读顺序和检查入口。`docs/README.md` 改成按任务导航的短索引，每个分类目录增加局部 README。

### `alpha-research`

保留 `concepts/` 作为研究方法入口，将模型选择、模型版图、过拟合控制、特征协议、AFML、风格因子和后端说明按概念归类；将研究模板放入 `guides/`；将信号和研究输出契约归入 `reference/`；将测试、安装和开发门禁归入 `operations/`。迁移和命名空间变更记录进入 `archive/` 或保留短 reference 指针。

### `deep-learning-tick-data-prediction`

将当前运行和项目现状集中到 `operations/`，将模型与数据边界放入 `architecture/` 和 `concepts/`，将次日预测运行指南放入 `guides/nextday/`，将研究议程、实验日志和专题结论放入 `research/`，将论文笔记继续放入 `reference/`。FI-2010 和退休 notebook 只从 archive 入口访问，不进入主线默认上下文。

### `market-data-platform`

按数据使用任务重组为数据资产与契约、采集与发布、质量与审计、开发与运维、集成参考。资产状态、schema、路径和 provider 事实继续以 manifest 或代码为准；研究 profile、迁移记录和一次性审计放入 reference、evidence 或 archive。

### `portfolio-backtester`

将回测和组合概念、会计与执行语义、成本/容量/风险说明分开；将接入、运行、检查和报告流程放入 `guides/` 与 `operations/`；将公开 API、配置和产物字段放入 `reference/`；已完成路线图和历史审计变为 reference 或 archive，避免与当前能力页并列表达状态。

### `strategy-research`

这是优先级最高的迁移对象。保持 `research/strategies/`、`research/experiments/` 和证据资产的业务结构，不按生命周期新增目录。`docs/` 只保留仓库架构、生命周期规则、证据画像、实验规范、运行产物和治理入口；策略正文留在对应 `research/strategies/<id>/README.md`，实验结果留在对应 experiment 目录，历史材料进入 `research/archive/` 或 `research/evidence/`。根 README 只保留策略地图和最短阅读路径，完整机器状态以 `catalog.json` 为准。

### `strategy-app`

将应用目录、owner 边界和迁移说明放入 `architecture/` 或 `reference/`，质量门禁和每周运行分工放入 `operations/`，A 股与港股操作流程放入 `guides/`，DailyWatch20 和 Hotsector 的具体发布说明按“输入、计算、产物、边界、验证”拆成专题目录。已结束迁移和历史回放保留兼容指针并归档。

### `strategy-pipeline`

保留公共控制面的核心概念和 contract 说明，按 `concepts/`、`guides/`、`operations/`、`reference/` 分开控制面 API、owner 接入、运行编排、配置解析、质量闸门、CLI 和目标文件导出。公共仓库不接纳具体策略、私有 provider、凭证或私有运行手册。

### `quant-execution-engine`

按风险边界将执行模型、目标解析和审计概念放入 `architecture/` 或 `concepts/`；将本地预演、broker smoke、发布和运行恢复放入 `operations/`；将 CLI、配置、targets 和能力矩阵放入 `reference/`；将已完成的 readiness、迁移和兼容记录归档。高风险操作页必须明确 dry-run、保护开关、凭证位置和可回滚步骤。

## 重写规则

正文迁移时按以下顺序重写：

1. 删除重复的项目定位、模块职责、当前状态和命令清单，改为链接唯一入口。
2. 把动态数字、提交号、资产数量、测试数量和运行状态移回机器文件或生成命令。
3. 把当前做法与带日期的结论分开。当前做法进入 active，阶段结论进入 evidence 或 archive。
4. 每页开头增加一句范围说明，明确页面负责什么、不负责什么以及事实来源。
5. 每个长页面按“目的、前置条件、输入、步骤、输出、边界、验证、相关入口”重排。
6. 保留命令、路径、配置键、API 名称和字段原文；命令必须用 `--help`、代码或测试核对。
7. 旧路径只保留兼容指针，指针使用 `status: superseded` 和 `superseded_by`。

## AI 上下文规则

所有仓库的 `AGENTS.md` 统一声明以下读取顺序：

1. 读取当前仓库根 README。
2. 读取当前仓库 `docs/README.md`。
3. 根据任务只读取一个相关分类目录的 README 和目标页面。
4. 只有任务涉及历史、证据、设计或实施计划时，才读取对应生命周期目录。
5. 不递归读取全部 Markdown，不把 archive、evidence、plans 和 specs 当作当前实现说明。

分类 README 使用任务表，不平铺所有子页面。每个页面只推荐下一级必要阅读，不形成长链路循环。

## 实施与提交边界

实施顺序固定为：

1. 顶层新增统一文档规则、迁移指针模板和链接/元信息检查。
2. 整理顶层 workspace 文档并验证跨仓链接。
3. 整理 `strategy-research`，再按数据、研究、回测、应用、编排、执行顺序整理其余七个子模块。
4. 每个子模块在自己的仓库和分支中提交文档移动与重写，运行该仓库检查并推送合并。
5. 顶层更新 submodule gitlink、入口链接和跨仓事实，运行顶层检查。

每个模块的单独提交应包含正文移动、旧路径兼容指针、局部索引、相关 README/AGENTS 更新和该模块的文档检查。不得把未完成的子模块路径写成顶层当前入口。

## 验证标准

每个子模块完成迁移后至少验证：

- 根 README、`AGENTS.md` 和 `docs/README.md` 的链接全部可解析
- 新目录 README 能从任务描述导航到当前权威正文
- 旧路径兼容指针存在，且不包含重复正文
- active 文档不直接把 archive、evidence、plans 或 specs 当作当前入口
- 命令、路径、配置键和 API 名称与代码或测试一致
- 文档风格检查通过
- 该子模块原有测试和质量门禁通过

顶层合并前再验证：

- 顶层和所有已迁移子模块的 Markdown 相对链接可解析
- 八个子模块入口、职责和 gitlink 一致
- 跨仓契约、版本矩阵和发布文档没有重复或过期状态
- `tests/test_docs_links.py`、`tests/test_documentation_entrypoints.py`、工作区 doctor 和文档相关检查通过
- 默认入口的推荐阅读集合不包含历史证据、旧计划和已废弃正文

## 不变事项

- 不删除历史材料，只移动到生命周期目录或用兼容指针替代正文入口。
- 不改变 `catalog.json`、artifact schema、`targets.json`、生产路径和公开 Python API。
- 不把私有仓库内容或真实数据复制进公共 `strategy-pipeline`。
- 不为“统一”而改写已哈希绑定的证据、发布收据和历史记录。
- 不在顶层重复维护子模块内部实现细节。

