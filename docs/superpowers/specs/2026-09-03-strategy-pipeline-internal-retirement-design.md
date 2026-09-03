# strategy-pipeline-internal 退役迁移设计

## 目标

将 `strategy-pipeline-internal` 中仍有价值的代码、测试、配置和文档按职责迁移到对应 owner 仓库或公共 `strategy-pipeline`，使 `research-workspace` 不再依赖 internal，完成 clean-room、历史敏感信息和消费者审计，最后冻结并正式下线 internal。

本设计不把“公共仓库可以安装”当作完成条件。完成条件是：原 internal 的活跃功能已经有新的唯一维护位置，workspace 和运行入口不再需要 internal，历史材料仍有明确归档位置，且删除 internal 不会留下未覆盖的运行、测试或文档入口。

## 当前基线

以 `strategy-pipeline-internal` 当前 main 的归属清单和源码树为准：

- internal 当前 main 有 194 个 Python 源文件、180 个测试文件、34 个脚本和 21 个配置文件。
- 文档归属清单覆盖 114 份文档，其中 8 份已完成迁移、58 份仍保留在 internal、16 份标记为 `planned`、32 份属于归档材料。
- 公共 `strategy-pipeline` 当前只提供 18 个 Python 文件，职责集中在 request、artifact reference、receipt、publication、handoff 和通用 runner。
- internal 的默认依赖仍包含 `alpha-research`、`market-data-platform`、`portfolio-backtester`、`strategy-app` 和 workspace 内的 `research-contracts`。
- internal 当前仍包含 `strategy_pipeline_internal` 下的研究策略、pipeline、liveops、CLI、配置和发布工具。

这些数字是迁移起点，不是最终预算。每个垂直切片合并后都要重新生成清单和依赖图。

## 目标架构

```text
market-data-platform  -> 发布数据资产、provider、PIT 和 current contract
alpha-research         -> alpha、特征、模型、诊断、信号和研究证据
portfolio-backtester   -> 组合构造、回测、成本、容量、暴露和组合报告
strategy-app           -> 策略专属 policy、冻结实验、研究应用和决策解释
strategy-research      -> 实验 runner、研究配置、试验账本和历史研究材料
quant-execution-engine -> targets 消费、风控、订单、券商执行和审计
research-workspace     -> 跨仓 contract、版本锁定、集成测试和治理
strategy-pipeline      -> 无领域知识的控制面和 handoff 原语
```

`strategy-pipeline-internal` 在迁移期间可以作为临时编排层存在。最终它不再是任何上述能力的唯一 owner，也不再出现在 workspace 的安装依赖、submodule、运行脚本或生产维护流程中。

## 迁移分类

### 公共控制面

仅允许迁移以下内容：

- 与领域无关的 request、artifact reference、receipt 和 handoff 类型
- 注入 owner 和 publisher 后的确定性执行顺序
- publication、handoff 和安全失败分类
- 合成 fixture、公共 API 文档和无私有依赖的 clean-room 测试

公共仓库不得包含策略名称、策略阈值、模型选择、研究结论、provider SDK 初始化、凭证、真实数据路径或私有运行配置。

### Owner 业务逻辑

以下内容必须迁移到领域 owner，不能留在公共仓库：

- `daily_watch20_*`、`hotsector_*`、`d11_h5_*` 和 `style_replica_*`
- `policy_*`、`promotion_*`、研究方法、实验阈值和策略解释
- AFML、信号、特征、模型和晋升证据语义
- allocation、selection、turnover、capacity、exposure 和执行成本语义
- provider、RQData、PIT 资产生产和数据恢复逻辑

迁移后的原实现、测试、配置和方法说明必须在同一垂直切片内完成 owner 归属。只迁移入口或 re-export 不算完成。

### Workspace 共享契约

跨仓库的 artifact schema、版本组合、路径约定、集成 smoke、文档归属清单和退役审计由 `research-workspace` 维护。生产方维护自己写出的字段，消费方维护自己的读取方式，workspace 维护发现入口和兼容矩阵。

### 历史归档

港股、一次性 probe、旧运行回执和已停止实验可以继续保留在 internal 或迁入明确的历史归档仓库。归档材料必须：

- 标注不可作为当前运行入口
- 保留来源、时间和恢复说明
- 不被 active CLI、CI、默认配置或 workspace 测试引用
- 不再作为迁移未完成项计数

## 垂直迁移顺序

### 阶段一：契约和文档基线

完成 16 份 `planned` 文档的逐文件判断，补充目标页面、原路径索引和链接测试。同步更新代码 ownership manifest、文档 ownership manifest、artifact contract 和 dependency registry。

验收证据：manifest 无未解释的 `planned`，每条 `complete` 同时有代码、测试、文档和集成证据。

### 阶段二：数据和研究证据

把数据源、PIT、provider、AFML、研究协议和平台资产字段分别迁入 `market-data-platform`、`alpha-research` 和 `research-workspace`。internal 只保留读取配置和运行侧导航。

验收证据：无 provider 私有实现留在 pipeline，artifact producer、owner 和 consumer 可由 schema、测试和文档互相追溯。

### 阶段三：回测、组合和执行交接

把 portfolio allocation、backtest、cost、capacity、exposure 和 positions 语义迁入 `portfolio-backtester`。把 targets 消费、risk、order、broker 和 execution audit 语义迁入 `quant-execution-engine`。公共仓库只保留通用 handoff 原语。

验收证据：`targets.json`、lineage、positions 和回测报告有唯一 producer、consumer、schema、测试和运行 smoke。

### 阶段四：策略应用和研究实验

把 DailyWatch20、Hotsector、StyleReplica、D11-H5 及其 policy、campaign spec、实验 runner、证据解释迁入 `strategy-app` 或 `strategy-research`。涉及 alpha 方法的部分归 `alpha-research`。

验收证据：strategy-app 和 strategy-research 可以独立运行各自入口，实验配置和研究测试不再从 internal 导入。

### 阶段五：收敛临时编排层

删除已经迁移的 internal 模块、兼容 facade、旧 CLI 分支和重复配置。剩余编排只负责组合 owner API、读取配置、创建 run 目录和调用公共控制面。

验收证据：internal 中没有无法归类的 active 模块，剩余内容全部有退役日期、owner 和删除条件。

### 阶段六：workspace 脱钩和退役

移除 internal 的 workspace 依赖、gitlink、默认安装来源、生产维护命令和 active 文档入口。运行完整测试、clean-room 安装、历史敏感信息扫描和消费者扫描，随后冻结 internal 并保留只读归档说明。

验收证据：在没有 internal checkout、私有凭证和私有 GitHub 权限的环境中，公共包和 workspace 的公共测试仍能完成。全仓搜索不存在 active internal import、命令或依赖。

## 每个切片的完成门槛

一个切片只有同时满足以下条件才允许标记为 `complete`：

1. 新 owner 中存在实际实现，不是只有说明或空 facade。
2. 原 internal 测试已迁移、重写或明确归档，并且新测试通过。
3. 原配置、fixture、schema 和运行命令已经有新归属。
4. 原文档已经迁移、改写为索引或标记为历史归档。
5. workspace 集成测试覆盖新入口和 artifact lineage。
6. 全仓搜索确认没有 active consumer 仍依赖旧路径。
7. PR 合并后更新所有 gitlink、版本清单和迁移 manifest。

## 最终退役门槛

只有以下条件全部满足，才允许冻结并下线 internal：

- 文档归属清单没有 `planned` 或无解释的 `private` active 项。
- internal 源码中的每个 active 模块都有 owner、迁移 commit、测试和文档证据。
- workspace 的 `pyproject.toml`、锁文件、submodule、脚本和 CI 不再引用 internal。
- 公共 `strategy-pipeline` 的 clean-room 安装和合成测试通过。
- 各 owner 仓库的完整测试和 workspace 集成测试通过。
- internal 历史和当前树完成敏感信息、私有策略标记、凭证、私有 URL 和真实数据路径审计。
- active consumer 搜索连续两个维护周期没有发现 internal 入口调用。
- internal 的冻结标签、只读归档位置、恢复说明和最终 owner 已记录在 workspace 文档中。

## 交付流程

所有仓库变更遵循：

```text
建立 worktree
  -> 编写失败测试或事实清单
  -> 实现代码、测试、配置和文档
  -> 运行仓库门禁与 workspace 集成检查
  -> 创建 PR
  -> 合并 main
  -> 删除远端和本地分支
  -> 删除 worktree
```

每个垂直切片单独提交，避免把迁移、删除和归档混在一个无法审阅的大 PR 中。

## 非目标

- 不把策略思想、研究结论或私有配置搬进公共仓库。
- 不为了降低文件数而删除仍有恢复价值的历史材料。
- 不通过扩大测试排除范围来掩盖未迁移功能。
- 不在 internal 尚有 active consumer 时直接改仓库可见性或删除仓库。
