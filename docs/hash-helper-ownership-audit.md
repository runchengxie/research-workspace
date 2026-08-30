# SHA-256 Helper Ownership Audit

审计结论：当前六个 helper 保持在各自仓库内是有意的。它们服务于不同的发布边界，直接共享实现会让运行时依赖跨越 alpha、回测、执行或数据仓库边界。

| Owner | Helper | Reason to remain local |
| --- | --- | --- |
| `research_contracts` | `src/research_contracts/file_receipts.py` | 顶层跨仓库契约和通用文件 receipt |
| `alpha-research` | `strategy-research/src/style_factors/robustness_sources.py` | 研究来源和稳健性产物的本地证据 |
| `market-data-platform` | `market-data-platform/src/market_data_platform/file_receipts.py` | 数据发布和分区文件 receipt |
| `portfolio-backtester` | `portfolio-backtester/src/portfolio_backtester/evidence_receipts.py` | 回测产物和组合证据 |
| `strategy-app` | `strategy-app/src/strategy_app/file_receipts.py` | 策略应用产物 |
| `quant-execution-engine` | `quant-execution-engine/src/quant_execution_engine/handoff_audit.py` | 执行交接审计 |

这些 helper 的共同算法都是 SHA-256，但输入路径、receipt schema、发布生命周期和依赖方向不同。它们不能因此被视为同一个 domain owner。当前测试会扫描登记的仓库目录，阻止未登记的同名 helper 增加。

## 变更规则

每个新增 helper 都必须先说明 owner、输入语义、输出 schema 和为什么不能调用已有 owner。只有在不改变运行时依赖边界、receipt schema 和发布生命周期的前提下，才可以提出共享实现。

本审计不包含直接调用 `hashlib.sha256` 但不提供跨文件 receipt helper 的密码学或数据内部哈希逻辑。此类代码仍需由所属仓库自己的安全和数据契约测试覆盖。
