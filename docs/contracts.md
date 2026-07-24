# 工作区文件约定

本页只说明顶层工作区中跨模块交接的文件约定。各子项目内部格式、业务参数和完整命令说明，仍以各自 README 和 docs 为准。

## 顶层可以依赖什么

顶层仓库只依赖两类稳定入口：

- 公开命令行：例如 `marketdata ...`、`marketdata migration hydrate-hk`、`strategy ...`、`qexec ...`。
- 文档化的文件输出：例如当前数据清单、数据资产索引、研究输出和标准格式的 `targets.json`。

顶层仓库的边界：

- 不导入子模块内部 Python 实现。
- 不把子模块临时工作目录当作正式数据来源。
- 不维护覆盖所有模块参数的总配置文件。
- 不默认触发真实券商交易。
- 不替子模块重新定义 lint、type check、coverage 或内部架构规则。

## 正式来源

| 文件或目录 | 生产方 | 消费方 | 用途 |
| --- | --- | --- | --- |
| `DATA_PLATFORM_ROOT` | 操作环境或顶层未跟踪 `.env` | 数据平台、研究系统 | 共享资产根目录 |
| `metadata/frozen_markets/hk.json` | `market-data-platform` | 人工审计、顶层 doctor | 港股已移入冷存储时的 freeze marker |
| `metadata/current_assets/a_share_current.json` | `market-data-platform` | 下游研究或数据消费者 | A 股当前可用数据清单 |
| `metadata/dataset_registry.csv` | `market-data-platform` | 人工审计、研究系统 | 已发布数据资产索引 |
| 版本化数据资产目录 | 数据维护模块 | 研究系统 | 实际数据资产 |
| `summary.json` | `strategy-pipeline` | 人工审计、后续导出 | 研究运行摘要 |
| `signals.parquet`、`signals.meta.json` | `alpha-research` | 评估、组合构造、回测、导出前审计 | 权威打分信号产物和 metadata |
| `factor_diagnostics_summary.json` | `alpha-research` | 人工审计、顶层 optional evidence | top features 的稳定性、风格暴露、市值段、行业、中性化后 信息系数（IC） 和冗余画像摘要 |
| `strategy_outputs/style-factors/<name>/` | `style_factor_attribution.py` → `style_factors` | 策略研究 | 全市场 9 因子多空日收益、逐年分解、相关性矩阵、策略归因 JSON 和逐年策略归因 CSV |
| `positions_by_rebalance.csv`、`positions_current*.csv` | `portfolio-backtester` | `strategy export-targets` | 回测持仓和已保存的目标持仓候选 |
| `targets.json` | `strategy export-targets` | `quant-execution-engine` | 标准格式的执行目标输入 |
| `targets.json.lineage.json` | `strategy export-targets` | 审计、复现 | 记录输入、配置和运行信息的审计文件 |
| `strategy_outputs/watchlist20/latest/watchlist_20.csv`、`watchlist_20.json` | `strategy watchlist20 run` | `market-intel` 晨报 | 内部严格 A4/B16（DailyWatch20 内部两袖：A 袖 4 只、B 袖 16 只） 的 20 股研究 artifact。JSON companion 必须与 CSV 的股票、袖、排名和权重一致，执行以 CSV 为准。客户 renderer 统一展示 20 股且不暴露内部袖、分数或权重 |
| `strategy_outputs/watchlist20/latest/selection_receipt.json` | `strategy watchlist20 run` | `market-intel` 晨报准入与审计 | 记录日期、模型、分钟特征、构造门禁、lineage 和 artifact 哈希 |
| `strategy_inputs/watchlist20/news_heat/latest/` | `market-intel news-heat-export` | `strategy watchlist20 run` | 严格 source date 的稀疏热点正样本。未出现股票表示未知而非零热度 |
| 订单审计和验证输出 | `quant-execution-engine` | 人工审计 | 执行系统自己的审计证据 |

## 跨模块 artifact 契约

机器可读清单见 [`artifact-contracts.yml`](artifact-contracts.yml)，清单加载和校验入口在 [`src/research_contracts`](../src/research_contracts/) 薄包中。`src/research_contracts` 由顶层仓库直接追踪，不登记为子模块。后续如果把 契约 实现抽到正式共享包，这份清单就是跨仓库 artifact 契约 的迁移基准。顶层只校验清单和文件交接，不导入子模块运行时内部实现。

### 可选 artifact envelope v2

迁移期间，现有 v1 artifact 和 reader 保持有效。producer 可以在 metadata 或 lineage sidecar 中以
`artifact_envelope` 键选择性写入 `research.artifact-envelope.v2`。该 envelope 只记录跨仓库可复现信息：

- artifact、run 和 producer 身份。
- producer commit/version 与 backend provenance。
- timezone-aware 创建时间。
- artifact、配置和上游 lineage 的 SHA-256。
- 对执行目标可选的 validity、portfolio/account scope、policy reference 和 幂等 scope。

envelope 不包含数据加载、路径解析、模型训练或组合计算 helper。Qlib、vn.py 和 LEAN 对象不得进入 envelope。v2 writer 在各 owner 仓库完成 parity 前保持 opt-in。未携带 envelope 的 v1 metadata 继续由兼容 reader 原样读取。

| Artifact | 契约 | Owner | 代码入口 | 最小稳定字段 |
| --- | --- | --- | --- | --- |
| `signals.parquet` | `alpha_research.signals` | `alpha-research` | `alpha_research.signal_artifact` | `signal_date`、`symbol`、`raw_pred`、`signal_eval`、`signal_backtest`、`signal_direction`、`rank`、`model_version`、`feature_set_id`、`eligible_for_backtest`、`eligible_for_live` |
| `signals.meta.json` | `alpha_research.signals metadata` | `alpha-research` | `signal_artifact_summary` | 契约 name、schema version、文件路径、行数、required columns |
| `positions_by_rebalance.csv` | `portfolio_backtester.positions_by_rebalance` | `portfolio-backtester` | `portfolio_backtester.contracts` | `rebalance_date`、`symbol`、`weight`。常见字段包括 `entry_date`、`side`、`signal`、`rank` |
| `targets.json` | `quant-execution-engine.targets/v2` | `quant-execution-engine` 解析，`strategy-pipeline` 导出 | `quant_execution_engine.targets`、`strategy export-targets` | `targets[]`，每项包含 `symbol`、`market` 和 `target_weight` 或 `target_quantity` |
| `targets.json.lineage.json` | target export lineage | `strategy-pipeline` | `strategy export-targets` | run id、输入持仓文件、配置、质量检查和导出时间 |
| `signals_style_replica.parquet` | `alpha_research.signals`（style_replica variant） | `alpha-research` | `alpha_research.style_replica.signal_generator` | 在 `signals.parquet` 基础上附加 `score_a`、`score_b`、`leg`、`theme`、`industry`、`selected_reason` |
| `signals_style_replica.meta.json` | `alpha_research.signals metadata` | `alpha-research` | `StyleReplicaSignalGenerator.write` | 契约 name、schema version、model_version、config（a/b slots、theme quotas） |
| `watchlist_20.csv` | `daily_watch20.selection.v1` | `strategy-pipeline` | `strategy_pipeline.daily_watch20_publish` | `source_date`、`signal_date`、沪深 `symbol`、`sleeve`、袖内 `rank`、四类分数、解释、模型和 feature-set 身份 |
| `selection_receipt.json` | `daily_watch20.selection.v1 receipt` | `strategy-pipeline` | `strategy_pipeline.daily_watch20_publish` | passed/quality 状态、A4/B16/20唯一计数、权重、分钟 required-date/as-of/lag、多周期标签、模型复用、热点输入、构造门禁和 artifact 哈希 |

`signals.parquet` 的 canonical owner 仍是 `alpha-research`，但 `market-intel/hot-sector-screener`
也可以作为外部 producer 生成同一 `alpha_research.signals` 契约的每日热点候选信号。该外部信号只表示
候选池排序。是否构造成组合由 `strategy-pipeline` 的 `external_signals` / `hotsector_overlay`
显式处理，是否导出执行目标由 `strategy export-targets` 显式处理。
外部热点信号可携带 `daily_confirm_score`、`confidence_score`、`confidence_label`
等可选解释列。这些列不属于最小稳定契约。默认 `hotsector_overlay` 仍使用等权 Top-K，
需要比较信号加权组合时显式使用 `hotsector_signal_weighted_overlay`。

DailyWatch20（每日观察的 20 只 A 股名单，由 strategy-pipeline 产出给 market-intel） 是独立的晨报研究 artifact。`alpha-research` 拥有 XGBRanker、默认
50%/30%/20% 权重的 1/3/5 日 时间点（point-in-time）（PIT） 标签和
feature 实现，`portfolio-backtester` 拥有 A4/B16 约束选择，`strategy-pipeline` 负责读取已发布数据、
同日完整性门禁、增量分钟缓存、周期重训/每日打分、滚动 样本外（OOS） 消融和原子发布。`market-intel`
生产严格时点化热点输入，并分别生成客户统一 20 股展示和内部审计展示。
MVP 的 `eligible_for_live=false`，不会生成
`targets.json`，也不得被晨报脚本隐式转换为交易目标。

热点输入目录固定包含 `news_heat.csv`、`news_heat_receipt.json` 和
`news_heat_schema.json`。它由工作区之外的 `market-intel` 管理，因此只记录在人工跨项目合同中，
不加入只允许 pinned 子模块 owner 的 `artifact-contracts.yml`。

## A 股资产状态

A 股正式数据入口使用 `metadata/current_assets/a_share_current.json`。研究侧迁移候选入口是 `strategy-pipeline` 的 `strategy run --config default_next` / `configs/presets/default_next.yml`，但在没有更高权限数据源或券商账户资源前，顶层约定只把下列能力视为可稳定交接：

- TuShare 5000 积分账户可覆盖的 raw/clean 日线类资产：`stock_basic`、`trade_cal`、`daily`、`adj_factor`、`daily_basic`、`stk_limit`，以及由这些输入生成的 `daily_clean`。
- `daily_clean` 可以包含复权价格、估值字段、涨跌停标记、ST 标记、停牌或零成交标记、上市天数和板块粗分类。发布前先执行 `marketdata tushare validate-a-share-daily-clean ... --profile baseline --out <report.json>`，研究就绪度检查再执行带交易日历的 `--profile research`。当前 ST 标记来自 latest instruments 快照，说明时应标注为最新快照口径。
- price-only A 股研究可以先消费 `daily_clean`、`instruments`、静态股票池或人工维护的 by-date 股票池。

以下能力需要对应资产可用后才能进入正式研究或执行验收：

- PIT universe：CSI300/500/800 或全 A 动态成分需要 point-in-time 成分来源。如果 TuShare 账户权限不足，应使用已授权 RQData/指数供应商资产或人工归档的历史成分资产。当前成分只适合当前截面说明。
- PIT fundamentals：需要披露日、报告期、公告延迟和字段映射。仅有最新财报快照不满足无未来函数研究。
- `daily_basic` 的 PE、市净率（PB）、市值和换手率属于逐日估值 overlay。财务报表 PIT 口径需要单独的披露日和报告期链路。
- 平台原生财报链路必须按 raw -> normalized -> PIT 分层，并在 validation 通过后才发布
  `normalized_fundamentals`、`pit_fundamentals` current-contract key 和 registry row。
- 行业 overlay：申万/中信行业最好保留历史变更。只有当前行业标签时，只适合当前截面说明。历史回测应使用历史行业标签。
- A 股深度交易规则：T+1、ST、停牌、涨跌停、新股上市 N 日和不同板块涨跌幅可作为研究侧过滤/标记。真实成交约束仍由执行系统和券商接口验证。
- 真实券商 CN 能力：当前工作区只要求 `targets.json` 解析和基础 dry-run 证据。真实账户权限、券商接口、港股通或 A 股账户能力必须单独验证。`strategy export-targets` 可以把 `.SH`、`.SZ`、`.BJ`、`.XSHG`、`.XSHE` A 股后缀映射为 `market: CN`，并保留或标准化执行目标里的交易所后缀。券商后端的中国大陆市场真实报单能力以执行仓库的券商证据为准。

扩大 A 股下载范围前，先按 [data-transition-playbook.md](data-transition-playbook.md) 完成 `DATA_PLATFORM_ROOT`、current 契约、registry、`daily_clean` 质量门禁和 `default` smoke 验证。`default_next` 作为同一 A 股路径的兼容别名保留。旧称 `metadata/current_assets/cn_current.json` 只用于历史兼容 alias 说明，新流程的权威入口是 `metadata/current_assets/a_share_current.json`。

## 港股生命周期边界

中国香港市场 provider 生产面已从活跃 `market-data-platform` 主线归档。活跃数据平台只保留 `marketdata migration freeze-hk` / `hydrate-hk` 恢复控制面和 `metadata/frozen_markets/hk.json` 检查。`strategy-pipeline` 不再保留显式港股 provider/research preset 入口，港股策略研究在当前工作区中定位为恢复专用历史研究线。工作区内公开演示路线和独立港股研究线已退役，清理记录见 [`hk-public-split-manifest.yml`](hk-public-split-manifest.yml) 和 [`archive/hk/README.md`](archive/hk/README.md)。其中 `quant-execution-engine` 的标准 `targets.json`、FX、broker adapter、风控和审计逻辑始终保留在执行仓库。需要港股历史复现时，先运行 `marketdata migration hydrate-hk` 恢复资产，并从 freeze tag 或恢复专用归档取回旧 provider / config 实现。

## 数据资产交接

数据资产通过当前数据清单和版本化资产目录交接：

```text
$DATA_PLATFORM_ROOT/
  assets/
  metadata/
    current_assets/
      a_share_current.json
    frozen_markets/
      hk.json
    dataset_registry.csv
  reports/
```

约定：

- `current_assets/*.json` 指向当前推荐读取的数据资产版本。
- `frozen_markets/hk.json` 表示港股已按计划移出活跃根目录，并保留冻结状态说明。
- `dataset_registry.csv` 用于查找和审计已发布资产。
- 下载、镜像、健康检查、current 契约 refresh、registry 构建和数据资产发布都由 `market-data-platform` 负责。
- 顶层仓库不提交数据本体、缓存、下载中间态或报告产物。
- 子模块工作目录里的临时输出只能用于本地排查。

## 研究到执行交接

研究系统通过 `strategy export-targets` 生成标准格式的 `targets.json`：

```text
signals.parquet
  -> named StrategySpec
  -> positions_by_rebalance.csv / strategy-pipeline 已保存持仓
  -> strategy export-targets
  -> targets.json
  -> quant-execution-engine 预演 / 模拟盘 / 实盘门禁流程
```

约定：

- `strategy export-targets` 只生成目标文件和审计附属文件。
- 导出命令不连接券商、不预演订单、不提交订单。
- `qexec rebalance <targets.json>` 负责券商连接、执行前检查、模拟盘和实盘门禁。
- 顶层脚本不得默认追加 `--execute`，也不得绕过 `QEXEC_ENABLE_LIVE=1` 等执行系统门禁。

## 研究诊断证据

`alpha-research` 的诊断逻辑可以在 `strategy-pipeline` 编排的每次 run 后输出 `factor_diagnostics_*` 画像产物。顶层仓库只把这类报告当作人工审计和 optional evidence，不直接导入研究仓库内部实现，也不让执行仓库重新解释因子。

可选 evidence 示例见 [`evidence/a-share-factor-diagnostics-20260621.json`](evidence/a-share-factor-diagnostics-20260621.json)。第一阶段该 evidence 不属于 `production_strategy_evidence` 硬门禁。稳定后再评估是否合并进 feature evidence 或 promotion gate。

## 缓存、别名和临时文件

以下内容可以存在，适合作为本地排查或迁移辅助：

- 子项目内部 `artifacts/`、`outputs/`、`.pytest_cache/`、`.ruff_cache/`。
- 为迁移保留的别名、软链接和本地报告。
- 人工临时导出的 CSV / JSON。

如果某份文件需要被其他模块稳定消费，应提升为：

1. 子项目文档化的输出。
2. 当前数据清单或资产索引可发现的资产。
3. 明确版本号的发布或归档产物。

## 顶层检查

顶层检查脚本只验证工作区层面的约定：

```bash
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
```

这些脚本只做轻量检查。子项目测试、业务参数验证和真实交易验证仍在对应子项目中完成。

`workspace_doctor.py` 还会检查 `scripts/*.py` 是否直接导入了子模块 Python 包，并阻止顶层 `_shared/*.py` 这类裸共享库回流。顶层脚本应通过公开 命令行（CLI） 或文档化文件进行交接。可复用 Python 应用程序接口（API） 应进入有明确 owner 的子模块或正式共享 package。

如果需要从顶层发起子项目自己的质量检查，使用委托式入口：

```bash
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile lint
python scripts/run_submodule_checks.py --profile test
python scripts/run_submodule_checks.py --profile type
python scripts/run_submodule_checks.py --profile full
```

委托检查的命令定义在 [../scripts/submodule_checks.json](../scripts/submodule_checks.json)。顶层只负责调度和汇总结果，不解析子模块内部源码，也不把 SOLID 或内聚耦合做成顶层评分。
其中 `lint` profile 包含子仓库自己定义的边界和维护债 gate。例如数据平台的港股拆分边界检查和策略编排的 maintainability ratchet。
