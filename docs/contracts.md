# 工作区文件约定

本页只说明顶层工作区中跨模块交接的文件约定。各子项目内部格式、业务参数和完整命令说明，仍以各自 README 和 docs 为准。

## 顶层可以依赖什么

顶层仓库只依赖两类稳定入口：

- 公开命令行：例如 `marketdata ...`、`cstree ...`、`rqdata-hk-depth ...`、`qexec ...`。
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
| `DATA_PLATFORM_ROOT` | 操作环境 | 数据平台、研究系统 | 共享资产根目录，由运行环境提供 |
| `metadata/current_assets/hk_current.json` | `market-data-platform` / 过渡期中国香港市场数据流程 | `cross-sectional-trees` | 中国香港市场当前可用数据清单 |
| `metadata/current_assets/a_share_current.json` | `market-data-platform` | 下游研究或数据消费者 | A 股当前可用数据清单 |
| `metadata/dataset_registry.csv` | `market-data-platform` | 人工审计、研究系统 | 已发布数据资产索引 |
| 版本化数据资产目录 | 数据维护模块 | 研究系统 | 实际数据资产 |
| `summary.json` | `cross-sectional-trees` | 人工审计、后续导出 | 研究运行摘要 |
| `positions_current*.csv` | `cross-sectional-trees` | `cstree export-targets` | 已保存的目标持仓候选 |
| `targets.json` | `cstree export-targets` | `quant-execution-engine` | 标准格式的执行目标输入 |
| `targets.json.lineage.json` | `cstree export-targets` | 审计、复现 | 记录输入、配置和运行信息的审计文件 |
| 订单审计和验证输出 | `quant-execution-engine` | 人工审计 | 执行系统自己的审计证据 |

## A 股等价支持的资产状态

A 股正式数据入口使用 `metadata/current_assets/a_share_current.json`。研究侧迁移候选入口是 `cross-sectional-trees` 的 `cstree run --config default_next` / `configs/presets/default_next.yml`，但在没有更高权限数据源或券商账户资源前，顶层约定只把下列能力视为可稳定交接：

- TuShare 5000 积分账户可覆盖的 raw/clean 日线类资产：`stock_basic`、`trade_cal`、`daily`、`adj_factor`、`daily_basic`、`stk_limit`，以及由这些输入生成的 `daily_clean`。
- `daily_clean` 可以包含复权价格、估值字段、涨跌停标记、ST 标记、停牌/零成交标记、上市天数和板块粗分类；质量门禁由 `marketdata tushare validate-a-share-daily-clean ...` 执行。
- price-only A 股研究可以先消费 `daily_clean`、`instruments`、静态股票池或人工维护的 by-date 股票池。

以下能力不能假装已经等价落地，必须在对应资产可用后才进入正式研究或执行验收：

- PIT universe：CSI300/500/800 或全 A 动态成分需要 point-in-time 成分来源；如果 TuShare 账户权限不足，应使用已授权 RQData/指数供应商资产或人工归档的历史成分资产，不能用当前成分回填历史。
- PIT fundamentals：需要披露日、报告期、公告延迟和字段映射；仅有最新财报快照不满足无未来函数研究。
- 行业 overlay：申万/中信行业最好保留历史变更；只有当前行业标签时只能作为当前截面说明，不应回填历史回测。
- A 股深度交易规则：T+1、ST、停牌、涨跌停、新股上市 N 日和不同板块涨跌幅可作为研究侧过滤/标记；真实成交约束仍由执行系统和券商接口验证。
- 真实券商 CN 能力：当前工作区只要求 `targets.json` 解析和基础 dry-run 证据；真实账户权限、券商接口、港股通或 A 股账户能力必须单独验证。`cstree export-targets` 可以把 `.SH`、`.SZ`、`.BJ`、`.XSHG`、`.XSHE` A 股后缀映射为 `market: CN`，并保留/标准化执行目标里的交易所后缀；但这只代表研究到执行文件契约可交接，不代表任一券商后端已经具备中国大陆市场真实报单能力。

## 港股生命周期边界

中国香港市场数据资产继续由 `market-data-platform` 生产、检查、发布和归档；`cross-sectional-trees` 只读消费。港股策略研究在当前工作区中定位为 legacy research lane：保留历史复现、跨市场 sanity check、少量明确资金/模拟盘/人工跟踪需求和 provenance，不再作为新增研究默认入口。港股专项 `alloc-hk` 属于 frozen-active 兼容能力；除非存在明确港股跟踪或复现需求，不应把它扩展成 A 股主线能力。

## 数据资产交接

数据资产通过当前数据清单和版本化资产目录交接：

```text
$DATA_PLATFORM_ROOT/
  assets/
  metadata/
    current_assets/
      hk_current.json
      a_share_current.json
    dataset_registry.csv
  reports/
```

约定：

- `current_assets/*.json` 指向当前推荐读取的数据资产版本。
- `dataset_registry.csv` 用于查找和审计已发布资产。
- 下载、镜像、健康检查、current contract refresh、registry 构建和数据资产发布都由 `market-data-platform` 负责。
- 顶层仓库不提交数据本体、缓存、下载中间态或报告产物。
- 子模块工作目录里的临时输出只能用于本地排查。

## 研究到执行交接

研究系统通过 `cstree export-targets` 生成标准格式的 `targets.json`：

```text
cross-sectional-trees 已保存持仓
  -> cstree export-targets
  -> targets.json
  -> quant-execution-engine 预演 / 模拟盘 / 实盘门禁流程
```

约定：

- `cstree export-targets` 只生成目标文件和审计附属文件。
- 导出命令不连接券商、不预演订单、不提交订单。
- `qexec rebalance <targets.json>` 负责券商连接、执行前检查、模拟盘和实盘门禁。
- 顶层脚本不得默认追加 `--execute`，也不得绕过 `QEXEC_ENABLE_LIVE=1` 等执行系统门禁。

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
python scripts/smoke_contracts.py
```

这些脚本只做轻量检查。子项目测试、业务参数验证和真实交易验证仍在对应子项目中完成。

`workspace_doctor.py` 还会检查 `scripts/*.py` 是否直接导入了子模块 Python 包。顶层脚本应通过公开 CLI 或文档化文件进行交接，不应写成对子模块内部实现的 import 依赖。

如果需要从顶层发起子项目自己的质量检查，使用委托式入口：

```bash
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile lint
python scripts/run_submodule_checks.py --profile test
python scripts/run_submodule_checks.py --profile type
python scripts/run_submodule_checks.py --profile full
```

委托检查的命令定义在 [../scripts/submodule_checks.json](../scripts/submodule_checks.json)。顶层只负责调度和汇总结果，不解析子模块内部源码，也不把 SOLID 或内聚耦合做成顶层评分。
