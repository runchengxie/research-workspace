# Public / Private 内容边界矩阵

> status: active
> owner: workspace
> audience: human and agent
> last_verified: 2026-09-06
> source_of_truth: yes
> superseded_by: n/a

本页定义工作区内容在公开仓库、私有研究环境和生产运行环境之间的默认边界。它是内容分级清单，不改变各子仓库的代码归属、发布权限或数据合同。

## 判定规则

按以下顺序判定目录或产物的可见性：

1. 公开后只暴露机制、不暴露 edge，标记为 `PUBLIC_CORE`。
2. 含真实策略、特征组合、标签、模型选择、生产参数或 provider 的内容，标记为 `PRIVATE_RESEARCH` 或 `PRIVATE_RUNTIME`。
3. 只负责锁版本、契约和集成检查的内容，标记为 `INTEGRATION_ONLY`。
4. 无法确认时，暂按 `PRIVATE_RESEARCH` 处理，并在后续边界审查中补充证据。

其中，`edge` 指能反推出具体投资优势、研究结论、生产配置、数据供应商或交易执行细节的内容。目录标记不等同于单个文件的最终发布许可，发布前仍需检查其中的配置、样本、日志和生成产物。

## 分类定义

| 标记 | 含义 | 默认可公开内容 |
| --- | --- | --- |
| `PUBLIC_CORE` | 可复用机制、稳定接口和不含业务 edge 的实现 | 通用代码、算法机制、脱敏示例和公开文档 |
| `PRIVATE_RESEARCH` | 研究知识、实验过程、策略逻辑和可能形成竞争优势的内容 | 仅公开抽象机制，不公开真实研究内容 |
| `PRIVATE_RUNTIME` | 生产环境、凭证、provider、交易和运行参数 | 不公开真实配置、密钥、日志和生产数据 |
| `INTEGRATION_ONLY` | 跨仓库组合、版本锁定、契约和门禁 | 可公开边界、格式和检查结果，不公开内部实现 |

## 工作区关键目录

| 路径 | 分类 | 边界说明 |
| --- | --- | --- |
| `docs/` | `INTEGRATION_ONLY` | 只记录跨仓库协作、契约、版本和发布治理；研究正文、运行配置和历史材料按下表处理 |
| `docs/adr/` | `INTEGRATION_ONLY` | 记录稳定的架构决策、职责边界和跨模块约束 |
| `docs/contracts/`、`docs/contracts.d/` | `INTEGRATION_ONLY` | 记录跨仓库文件格式、字段和兼容契约 |
| `docs/governance/`、`docs/operations/` | `INTEGRATION_ONLY` | 记录质量、版本、维护、发布和工作区操作门禁 |
| `docs/research/`、`docs/evidence/` | `PRIVATE_RESEARCH` | 研究笔记、实验证据和可推导策略 edge 的材料 |
| `docs/archive/` | `PRIVATE_RESEARCH` | 历史研究、恢复材料和可能包含真实业务上下文的归档；除非另有审查，不作为公开内容 |
| `src/research_contracts/` | `INTEGRATION_ONLY` | 工作区级稳定契约和契约烟测，不承载真实策略或生产参数 |
| `scripts/` | `INTEGRATION_ONLY` | 工作区 doctor、质量检查和跨仓库委托；脚本内若含 provider 或生产参数，按运行时规则处理 |
| `.github/`、`.gitmodules` | `INTEGRATION_ONLY` | CI、仓库组合和版本锁定；不得包含凭证或私有服务地址 |

## 子仓库关键目录

| 路径 | 分类 | 边界说明 |
| --- | --- | --- |
| `market-data-platform/src/` | `PUBLIC_CORE` | 数据资产的通用生产、质量和读取机制；真实数据集、provider 和凭证另行保护 |
| `market-data-platform/config/`、运行数据和缓存 | `PRIVATE_RUNTIME` | 数据源配置、生产参数、缓存和真实数据供应商信息 |
| `deep-learning-tick-data-prediction/src/` | `PRIVATE_RESEARCH` | 事件流处理、标签、模型输入和评估可能暴露研究 edge |
| `deep-learning-tick-data-prediction/configs/`、`legacy/` | `PRIVATE_RESEARCH` | 模型选择、实验配置、标签和历史研究实现，未逐项审查前按私有处理 |
| `alpha-research/src/`、`research/` | `PRIVATE_RESEARCH` | 特征、模型、信号、研究评估和真实策略组合 |
| `portfolio-backtester/src/` | `PUBLIC_CORE` | 通用组合、成本、容量、暴露和风险计算机制 |
| `portfolio-backtester/config/`、回测产物 | `PRIVATE_RESEARCH` | 真实策略参数、样本、组合权重和研究结论 |
| `strategy-research/src/`、`research/` | `PRIVATE_RESEARCH` | 策略身份、投资假设、生命周期、实验和证据导航 |
| `strategy-app/src/` | `PUBLIC_CORE` | 不含策略 edge 的纯计算机制和稳定接口；策略规格与真实参数除外 |
| `strategy-pipeline/src/` | `PRIVATE_RUNTIME` | 编排、外部调用、运行目录、发布控制和 provider 适配可能暴露生产运行细节 |
| `strategy-pipeline/config/`、`targets.json` 及运行产物 | `PRIVATE_RUNTIME` | 生产参数、数据路径、发布目标和执行交接内容 |
| `quant-execution-engine/src/` | `PRIVATE_RUNTIME` | 风控、券商适配、订单执行、对账和审计运行时 |
| `quant-execution-engine/config/`、日志和凭证 | `PRIVATE_RUNTIME` | provider、生产参数、交易审计和凭证，禁止公开 |

## 例外与复核

- 单个文件同时包含多类内容时，按更严格的分类处理；例如同时含通用机制和真实参数时，整体按 `PRIVATE_RESEARCH` 或 `PRIVATE_RUNTIME` 保护。
- `README`、契约字段和 API 文档可以公开，但不得通过默认值、示例数据、日志片段或路径泄露 edge。
- 新增目录在完成审查前默认标记为 `PRIVATE_RESEARCH`，并在本矩阵补充路径、分类和依据。
- 公开发布前应同时检查密钥、真实数据、provider 名称、标签、特征组合、模型选择、生产参数和交易审计信息。
