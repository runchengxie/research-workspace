# 策略卫星项目

> status: active
> owner: workspace
> last_verified: 2026-06-22
> source_of_truth: yes

本工作区核心链路依次经过 `market-data-platform`、`alpha-research`、
`portfolio-backtester`、`strategy-pipeline` 和
`quant-execution-engine`。以下项目是策略卫星，通过文件契约接入数据平台、
研究 universe、信号或目标持仓交接点，不作为 workspace submodule。

各卫星项目是独立 git 仓库，路径相对于 `~/code/`。适配脚本见 `scripts/` 目录。

## 全景数据流

```text
a-share-factor-core (共享 library, vendor submodule)
    ├── vendor'd by guan-etf-rotation-v3
    └── vendor'd by hot-sector-screener

guan-etf-rotation-v3
    │  ETF 横截面轮动 + 行业聚合信号
    │  输出: artifacts/signals/<run>/industry_signal.csv
    │
    │  ┌─ scripts/publish_etf_industry_signal.py ─┐
    │  │  复制到 DATA_PLATFORM_ROOT 标准位置       │
    │  └──────────────────────────────────────────┘
    ↓
hot-sector-screener
    │  消费: 数据湖热点数据 + ETF 行业轮动信号
    │  输出: outputs/<YYYYMMDD>/candidate_universe.{csv,json}
    │
    │  ┌─ scripts/hotsector_to_cstree_universe.py ─┐
    │  │  转换为 cstree research_universe 格式      │
    │  └───────────────────────────────────────────┘
    ↓
market-data-platform (core submodule)
    │  发布: strategy_outputs/.../cstree_universe.csv
    ↓
alpha-research (core submodule)
    │  消费: research dataset / research_universe.by_date_file
    │  输出: signals.parquet + signals.meta.json
    ↓
portfolio-backtester (core submodule)
    │  消费: signal artifact + pricing / tradability data
    │  输出: positions_by_rebalance.csv + backtest evidence
    ↓
strategy-pipeline (core submodule)
    │  消费: candidate universe → research_universe.by_date_file
    │  编排: alpha-research + portfolio-backtester
    │  输出: targets.json + targets.json.lineage.json
    ↓
quant-execution-engine (core submodule)
    消费: targets.json → dry-run / 执行
```

## guan-etf-rotation-v3

| 属性 | 值 |
| --- | --- |
| 路径 | `~/code/guan-etf-rotation-v3` |
| 角色 | ETF 横截面轮动 + 行业聚合信号生成 |
| Python | >=3.10 |
| 模型 | LightGBM |
| CLI | `uv run etf-rotation ...` |
| 子模块 | `vendor/a-share-factor-core` |
| 输出目录 | `artifacts/signals/<run>/` |
| 关键输出 | `industry_signal.csv`（列: rank, industry, weight, weighted_score, symbol_count, signal_date） |

### 行业信号输出格式

```csv
rank,industry,weight,weighted_score,symbol_count,signal_date
1,电子,0.25,0.85,12,2026-06-20
2,计算机,0.18,0.72,8,2026-06-20
...
```

### 发布到标准位置

ETF 信号写在本仓库 `artifacts/signals/` 下。hot-sector-screener 期望从
`$DATA_PLATFORM_ROOT/strategy_outputs/etf_rotation_v3/<run>/` 读取。
使用 `scripts/publish_etf_industry_signal.py` 发布：

```bash
python scripts/publish_etf_industry_signal.py \
  --src ~/code/guan-etf-rotation-v3/artifacts/signals/<run> \
  --dst "$DATA_PLATFORM_ROOT/strategy_outputs/etf_rotation_v3/<run>"
```

## hot-sector-screener

| 属性 | 值 |
|------|-----|
| 路径 | `~/code/hot-sector-screener` |
| 角色 | 每日热点题材候选池（50-100 只 A 股） |
| Python | >=3.10 |
| CLI | `uv run hotsector ...` |
| 子模块 | `vendor/a-share-factor-core` |
| 输出目录 | `outputs/<YYYYMMDD>/` |
| 数据来源 | 同花顺热榜、东财概念、开盘啦概念成分、ETF 轮动信号 |
| 关键输出 | `candidate_universe.json`, `candidate_universe.csv` |

### 候选池输出格式

`candidate_universe.json` 中 `candidate_universe` 数组每条记录：

```json
{
  "ts_code": "300308.SZ",
  "name": "中际旭创",
  "relevance": 0.95,
  "source_topics": ["CPO光通信"]
}
```

### 转换为 cstree universe 格式

strategy-pipeline 的 `research_universe.by_date_file` 需要 `trade_date,symbol` 格式。
使用 `scripts/hotsector_to_cstree_universe.py` 转换：

```bash
python scripts/hotsector_to_cstree_universe.py \
  --input ~/code/hot-sector-screener/outputs/20260619/candidate_universe.csv \
  --trade-date 2026-06-19 \
  --out "$DATA_PLATFORM_ROOT/strategy_outputs/hot_sector_screener/by_date/cstree_universe.csv"
```

输出格式：

```csv
trade_date,symbol,selected
2026-06-19,300308.SZ,true
2026-06-19,688111.SH,true
```

在 cstree 配置中使用：

```yaml
research_universe:
  mode: pit
  by_date_file: strategy_outputs/hot_sector_screener/by_date/cstree_universe.csv
```

详细输出契约见 [hotsector 项目文档](https://github.com/runchengxie/hot-sector-screener/blob/main/docs/output-contract.md)（不在本仓库内）。

## a-share-factor-core

| 属性 | 值 |
|------|-----|
| 路径 | `~/code/a-share-factor-core` |
| 角色 | 共享技术因子、模型训练、组合构造、验证工具 |
| Python | >=3.10 |
| 消费者 | guan-etf-rotation-v3, hot-sector-screener |
| 集成方式 | 各消费者通过 `vendor/a-share-factor-core` git submodule + `[tool.uv.sources]` path 依赖 |

### 当前集成状态

两个策略仓库各自 vendor 同一份代码，通过 uv path source 引用：

```toml
# guan-etf-rotation-v3/pyproject.toml 和 hot-sector-screener/pyproject.toml
[tool.uv.sources]
a-share-factor-core = { path = "vendor/a-share-factor-core" }
```

在 <5 个消费者的规模下可控。

### 中期方向

当 a-share-factor-core 补足测试和版本号后，可改为 tagged release 依赖：

```toml
[tool.uv.sources]
a-share-factor-core = { git = "https://github.com/runchengxie/a-share-factor-core", tag = "v0.1.0" }
```

不进入 research-workspace 核心 release matrix。

## 接入适配脚本

| 脚本 | 方向 | 用途 |
|------|------|------|
| `scripts/publish_etf_industry_signal.py` | ETF → 数据平台 | 复制 ETF 行业信号到标准位置 |
| `scripts/hotsector_to_cstree_universe.py` | hotsector → cstree | 转换候选池为 cstree by_date 格式 |

脚本规则与 workspace 其他顶层脚本一致：
- 不 import 子模块 Python 包
- 通过文件和 CLI 交接
- 不维护子模块内部配置

## 为什么不作为 workspace submodule

1. research-workspace 已有的五段核心架构（数据→alpha→组合回测→策略编排→执行）边界清晰，硬门禁测试覆盖完整。
2. 两个策略项目体量和成熟度不同，强制纳入 core release matrix 会拖慢 CI 和版本锁定。
3. 核心链路已通过 `signals.parquet`、`positions_by_rebalance.csv` 和 `targets.json` 标准化。策略卫星的角色是可选输入源，核心组件仍是五段主链路。
4. 应先验证 candidate universe 作为 cstree research_universe 后的 OOS 表现，再评估提升为 optional submodule。
