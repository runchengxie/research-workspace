# 代码健康审计与优化空间（2026-07-31）

> status: reference
> owner: workspace
> last_verified: 2026-08-17
> source_of_truth: no
> superseded_by: maintainability-governance.md

本页是日期化审计快照，仓库名称、依赖关系和热点数量可能已经变化。当前状态以[维护性治理](maintainability-governance.md)、机器可读预算和[工作区路线图](roadmap.md)为准。

本文件记录对 research-workspace 超级项目（含六个子模块）的代码健康只读审计结论，作为后续优化决策的基线。审计方法为文件扫描、grep、AST 静态分析与 ruff 统计，未修改任何代码。

## 总体结论

项目架构方向健康：跨子模块依赖是单向无环图（research-apps → alpha-research → market-data-platform，strategy-pipeline → market-data-platform，其余子模块不反向依赖），无循环依赖，符合依赖倒置方向。PEP8 格式基线良好（各子模块均启用 ruff）。

主要优化空间集中在三点：物理文件过度拆分（market-data-platform 的 `_partNN` + facade 层）、少量超长单体文件（strategy-pipeline 与 portfolio-backtester）、以及 dev 治理脚本的跨仓库复制。lint 忽略项总量看似大，但经前几轮核查，绝大多数（facade F401、PLR0913）是刻意且合理的设计，不是债。

## 一、物理拆分过度（market-data-platform）

- 现状：`market-data-platform` 有 68 个 `_partNN` 物理拆分文件，合计约 26,705 行。最长 part 621 行（`_a_share_mins_partition.py`），多数 500+ 行。每个原模块被拆成多个 part，再由一个 facade 聚合文件用 `from ..._partNN import (...)` 重新导出。
- 背景：这是一次有意为之的架构拆分（文档说明为规避循环依赖），本身不是错误。但 68 个 part 文件加 28 个 facade 造成文件数爆炸，阅读与导航成本高。
- 配置事实：mdp 的 ruff `select` 未启用 C901（仅 mccabe `max-complexity=14`），所以「part 拆分规避 C901 门禁」的说法不准确。项目根本没开 C901 规则，真实情况是 mccabe 阈值 14 相对宽松（research-apps 为 10），部分函数级复杂度被阈值容纳。
- 优化空间：评估将 68 个 part 按逻辑内聚重新合并为合理粒度模块，撤掉对应的 facade/re-export 层。这是大工程，需逐模块验证对外契约不变，建议作为后续独立 worktree 推进，不在本轮执行。

## 二、超长单体文件

ruff C901 在六个子模块 `src/` 下均为 0 处超限（因 max-complexity 阈值宽松 + 物理拆分）。以下文件超过 700 行，但行数长不等于需要拆分。已逐一核查：`execution_sim/core.py` 虽 820 行却无任何类定义，全是模块级函数，且已把具体执行、报告、模型、容量逻辑委托给 `.orders`/`.reporting`/`.models`/`.capacity` 等子模块，自身只做三个 NAV 模拟路径（capacity / adjusted / ideal）的编排。这种「长但平」的编排模块职责单一，硬拆反而增加调用跳转、降低可读性，不建议拆分。strategy-pipeline 四个 780+ 行文件的拆分价值需另行逐文件评估。

| 子模块 | 文件 | 行数 |
| --- | --- | --- |
| portfolio-backtester | `execution_sim/core.py` | 820 |
| strategy-pipeline | `daily_watch20_pipeline.py` | 794 |
| strategy-pipeline | `pipeline/output_summary_sections.py` | 791 |
| strategy-pipeline | `pipeline/output_artifacts.py` | 785 |
| strategy-pipeline | `pipeline/config.py` | 749 |
| quant-execution-engine | `broker/_longport_client.py` | 725 |
| market-data-platform | `_campaign_run.py` | 703 |

其中 strategy-pipeline 四个 780+ 行文件的拆分价值最高，需逐文件评估。`execution_sim/core.py`（820 行）经核查为健康的编排模块，不建议拆分。

## 三、dev 治理脚本跨仓库复制

去重前必须先区分两种重复：真重复（同一契约的拷贝，修复一处应同步其他处）与同名异实现（只是文件名相同，职责与契约不同，强行合并反而制造耦合）。本次逐一核查后结论如下。

| 脚本 | 位置 | 一致性 | 判断 |
| --- | --- | --- | --- |
| `maintainability_metrics.py` | 六个子模块 `scripts/dev/` 各一份 | 分三族。A 族（alpha-research、portfolio-backtester、strategy-pipeline、quant-execution-engine）函数签名高度一致，属同一契约演化。B 族（market-data-platform）用参数计数加 baseline，独立实现。C 族（research-apps）调用 ruff 加 baseline，独立实现 | A 族四份是真重复，可抽成共享包。B 族与 C 族契约不同，不应合并 |
| `namespace_boundary.py` | strategy-pipeline / alpha-research / portfolio-backtester 各一份 | 待逐一比对 | 若契约相同再考虑收敛，目前不急于合并 |
| `run_tests.sh` | 三个子模块各一份 | 待比对 | 疑似复制，合并前先确认调用参数一致 |
| `export_repo_source.py` | quant-execution-engine / strategy-pipeline 各一份 | 内容近似 | 两份维护者辅助脚本，可合并 |

`maintainability_metrics.py` 此前被记为「六个子模块各一份、独立演化复制」，后又被误判为「全部同名异实现、不应合并」。本轮逐一比对六份后确认是三族并存。A 族四份（alpha-research、portfolio-backtester、strategy-pipeline、quant-execution-engine）函数签名几乎一致，是同一契约的复制，修复一处不会传播到其他三份，属于真重复，值得抽成共享包。B 族（market-data-platform）与 C 族（research-apps）各自用不同算法与 baseline 契约，强行合并会破坏这两个子模块的门禁，应保留独立。真正值得收敛的是 A 族四份复制，以及 `export_repo_source.py` 这类内容近似、契约单一的辅助脚本。

对同名异实现保持各子模块独立，比强行抽象更安全。已有的治理理由已写在 `docs/quality-coverage-governance.yml` 的 `reason` 字段（新增「分类：临时债 / 永久设计」标记），便于新人判断每条忽略的性质。

## 四、lint 忽略项构成

| 子模块 | `# noqa` 处数 | 备注 |
| --- | --- | --- |
| market-data-platform | 106 | 28 处 facade F401（合理）、约 43 处 PLR0913（刻意设计，合理）。剩余约 35 处待复核 |
| strategy-pipeline | 76（对应 195 处被压制告警：182 PLR0913 + 12 PLR0912 + 1 PLR0915） | 真实复杂度被有意压制，值得重点复核是否有掩盖问题的 |
| quant-execution-engine | 10 | 较低，健康 |
| portfolio-backtester | 7 | 健康 |
| alpha-research | 4 | 健康 |
| research-apps | 3 | 健康（max-complexity=10，最严） |

说明：mdp 与 strategy-pipeline 的 noqa 数量偏高。其中 facade F401 与 PLR0913 已在前几轮评估为合理设计，不计入债。`strategy-pipeline` 的 195 处被压制复杂度告警是真实存在且被有意保留的，属于该仓库的业务复杂度，是否要消除需结合重构（见第二节）一并考虑。

## 五、一次性脚本

- `market-data-platform/scripts/internal/archive/build_a_share_tushare_sw2021_industry_changes_20260603.py`：文件头注释明确写「Archived one-off script. Do not use in production」，且注明已被 `marketdata tushare download-a-share-industry-membership` 取代。保留理由已由注释说明，可接受，但建议移出 `scripts/` 活跃目录以免被误当工具。
- `tushare_minute_backfill*.py`：命名像一次性回补，实际已被引用（常驻工具），非死代码。
- 未发现模块级未引用函数/类的确凿死代码（对最长文件做 AST 调用图分析，私有函数均被同文件调用）。

## 六、规范符合度

- PEP8 / 格式：各子模块启用 ruff（E/F/I/UP/B/C4/RET/RUF100 等），基线良好。
- Google Style（docstring）：抽查 facade 与 partition 文件均有规范 docstring，符合度较好。
- 高内聚低耦合：跨模块依赖方向健康、无环，符合。但 market-data-platform 的物理拆分粒度过细、超长单体文件职责偏重，单看模块内聚有改进空间。
- SOLID：无严重违反。`execution_sim/core.py` 虽长但属编排模块，单一职责（SRP）成立。主要偏离是「合理粒度」原则（文件过碎或过长的两端），集中于 market-data-platform 的 `_partNN` 过度拆分。

## 七、优化优先级建议

1. 【中】抽离共享 `scripts/dev/` 工具（maintainability_metrics / namespace_boundary / run_tests）为单一共享包，消除六加三份独立演化复制。收益高、风险低（纯工具，不影响业务逻辑）。
2. 【中】逐文件评估 strategy-pipeline 四个 780+ 行文件的拆分价值，`execution_sim/core.py` 已确认无需拆分。
3. 【低/大】评估 market-data-platform 的 `_partNN` + facade 重新合并，降低文件数爆炸。需逐模块保障对外契约不变，建议独立 worktree 推进。
4. 【低】移动 `market-data-platform/scripts/internal/archive/` 的 one-off 脚本出活跃目录。

## 八、团队友好性观察

项目目前几乎是个人项目，维护依赖个人对架构的记忆。具体体现：

- 大量 lint 忽略项（尤其是 facade F401 与 PLR0913）依赖维护者理解「为何忽略」才能安全改动，新人不读文档易误删有效忽略（前几轮已实测 RUF100 `--fix` 误伤有效 noqa 的风险）。
- 治理门槛高：superproject 有 FOUR-check pre-push 门禁、ratchet 预算、per-file-ignore 注册表等，新人需先理解整套治理文件才能提交。
- `_partNN` 拆分与 facade 层增加了「同一个逻辑分散在多个文件」的认知负担。

个人项目向团队项目演进时，这类摩擦很典型。若未来要团队化，优先级 1（共享工具）与文档可读性提升收益最大。
