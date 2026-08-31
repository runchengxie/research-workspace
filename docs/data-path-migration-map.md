# 数据路径迁移映射

## 目的

本文件把当前实际存在的历史目录映射到统一生命周期术语。它首先是审计和迁移清单，
不是批量重命名授权。目录只有在引用、凭证、锁、运行状态和保留策略都核对完成后，
才可以迁移或删除。

状态含义：

- `已统一`：物理路径已经符合规范，继续使用。
- `兼容保留`：名称较旧，但仍被消费者使用，暂不改名。
- `拆分待审`：父目录混合了多个语义，必须按子目录或资产类型迁移。
- `归档保留`：已退出当前流程，保留归档清单和凭证。

## 数据平台映射

| 当前路径 | 规范语义 | 状态 | 处理原则 |
| --- | --- | --- | --- |
| `assets/tushare/` | `raw/` | 兼容保留 | 供应商原始数据，不做通用清理 |
| `assets/derived/` | `published/`，并由 `current/`、`rollback/` alias 指向版本 | 兼容保留 | 先构建、校验，再原子切换 alias |
| `assets/universe/staging/` | `staging/`，但属于审计快照 | 兼容保留 | 不能按名称删除，查看 inventory 和 receipt |
| `metadata/current_assets/` | `current/` | 兼容保留 | 这是当前读取契约，不能直接改名或删除 |
| `metadata/archive/` | `archive/` | 已统一 | 只保存元数据归档，不等同于永久保留 |
| `metadata/minute_*` | `staging/` 或 `receipts/` | 拆分待审 | 按计划、检查结果和运行凭证分别归类 |
| `metadata/industry-changes-backups/` | `archive/` | 拆分待审 | 只有确认有替代清单后才能缩短保留期 |
| `staging/` | `staging/` | 已统一 | 终态 receipt、替代版本和锁状态决定后续动作 |
| `reports/` | `reports/` | 已统一 | 保留验证和发布证据，按 retention 审查历史版本 |
| `runs/` | `runs/` | 已统一 | 运行完成后不可变，旧运行需单独做保留决定 |
| `experiments/` | `experiments/` | 已统一 | 固定时点研究快照，不能按普通缓存处理 |
| `research/` | `experiments/`、`features/`、`reports/`、`receipts/` | 拆分待审 | MDP 根目录仅剩兼容 symlink；watchlist20 研究集合已归入 `experiments/strategies/watchlist20/` |
| `strategy_inputs/` | `published/` 或 `features/` | 拆分待审 | 稳定策略输入已归位到 `published/strategies/`，其余按生产方和消费者确认 |
| `strategy_outputs/` | `runs/`、`features/`、`snapshots/`、`reports/`、`receipts/` | 拆分待审 | 稳定策略输出已归位到 `published/strategies/`，保留旧入口和 `latest` 兼容 symlink |
| `artifacts/` | 按子目录拆成 `runs/`、`reports/`、`snapshots/`、`cache/`、`receipts/` | 拆分待审 | 父目录是历史总称，必须逐子目录核对 manifest |

## 已确认的具体兼容项

| 历史名称或路径 | 规范解释 | 当前动作 |
| --- | --- | --- |
| `strategy_outputs/watchlist20/research/incumbent_challenger/` | `experiments/`、`runs/`、`reports/` 的研究集合 | 已迁入 `experiments/strategies/watchlist20/incumbent_challenger/`，旧路径保留 symlink |
| `challenger_entry*` | 上述研究集合的兼容 symlink | 保留，消费者迁移前不得删除 |
| `strategy-pipeline/artifacts/cache/` | `cache/` | 已归位到 `strategy-pipeline/cache/`，旧路径保留 symlink；只有证明可重建且无占用后才可清理 |
| `strategy-pipeline/artifacts/runs/` | `runs/` | 已归位到 `strategy-pipeline/runs/`，旧路径保留 symlink；按运行状态和 receipt 保留 |
| `strategy-pipeline/artifacts/reports/` | `reports/` | 已归位到 `strategy-pipeline/reports/`，旧路径保留 symlink；按报告引用和 retention 保留 |
| `strategy-pipeline/artifacts/snapshots/` | `snapshots/` | 已归位到 `strategy-pipeline/snapshots/`，旧路径保留 symlink；固定时点证据先核对引用 |
| `trading-research-dashboard/cache/` | `cache/` | 外部项目本地缓存，按 Dashboard 自身规则清理 |
| `archive/market-data-platform/staging/2026-08-31/` | `archive/` | 已归档的替换任务，保留 archive README 和 receipt |
| `sclt/archive/2026-08-30/` | `archive/` | 已迁出的研究产物归档，不进入 Git |

## 首批已执行迁移

2026 年 8 月 31 日，以下两个没有生产消费者精确引用的研究目录完成了物理迁移：

| 原路径 | 新路径 | 兼容入口 | 回执 |
| --- | --- | --- | --- |
| `research/multi_horizon_stateful_minute_gate_20260729/` | `experiments/multi_horizon_stateful_minute_gate_20260729/` | 原路径 symlink | `metadata/lifecycle/migrations/research-to-experiments-20260831.json` |
| `research/minute_strategy/tushare_sh_sz_last30m_reversal_20260729/` | `experiments/minute_strategy/tushare_sh_sz_last30m_reversal_20260729/` | 原路径 symlink | 同上 |

迁移前后文件数量、字节数和文件清单 SHA-256 一致，原路径仍可读取。回执中的
`deletion_authorized=false` 表示兼容入口和新目录都不能因本次迁移而删除。

`strategy_outputs/watchlist20/`、`strategy_outputs/d11_h5_shadow/`、
`strategy_inputs/watchlist20/` 和其他含有 `latest`、生产 receipt 或日报引用的目录仍保持
旧入口，但物理内容已经归位到 `published/strategies/`，待消费者完成新路径支持后再退役兼容
symlink。详细回执见 `metadata/lifecycle/migrations/stable-strategy-layout-20260831.json`。

## 迁移门禁

每次实际迁移都必须留下以下记录：

1. 原路径、目标路径、文件数量、字节数和校验摘要；
2. 对应 manifest、receipt、运行状态和数据 owner；
3. 代码、服务、cron、symlink 和文档引用扫描结果；
4. `current`、`latest`、`rollback` 和 successor 核对结果；
5. 失败时的回滚路径，以及迁移后的 retention 决定。

本轮已完成可安全归类的实体目录迁移；仍保留兼容 symlink，不删除任何大体积研究或运行结果。
后续涉及生产默认路径的代码和 cron 更新，必须先经过 shadow read 和日报 dry-run。

涉及日报和生产消费者的 breaking change 管理，见
[数据路径 breaking change 登记](data-path-breaking-change-register.md)。

## 当前审计清单

可重复生成的只读审计工具是：

```bash
python scripts/data_path_audit.py \
  --data-root /home/richard/data/market-data-platform \
  --output /home/richard/data/market-data-platform/metadata/lifecycle/path-audit-20260831.json
```

当前清单位于 `/home/richard/data/market-data-platform/metadata/lifecycle/path-audit-20260831.json`。
它记录顶层路径及混合目录直接子项的规范语义、状态、文件数量和字节数，并且不会跟随符号
链接或执行移动、删除和 alias 修改。当前扫描结果与数据根目录的总字节数一致，约为 513 GB；
这只是盘点结果，不是删除建议。

## 后续顺序

1. 先处理小型、已终态且有明确 receipt 的元数据目录；
2. 再为 `strategy_outputs`、`research` 和 `artifacts` 生成子项 manifest；
3. 为每个消费者增加新路径读取能力并保留兼容 alias；
4. 观察至少一个完整运行周期后，再归档旧路径；
5. 最后依据 retention 报告决定是否删除归档内容。
