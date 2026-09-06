# 架构迁移基线（2026-09-06）

## 记录范围

本记录冻结架构归集开始前的版本、职责、运行入口、数据边界和恢复方式。记录对象包括顶层
`research-workspace`、八个 git submodule 和兄弟系统 `market-intel`。

采集时间为 2026-09-06（Asia/Shanghai）。顶层版本和八个子模块版本来自当前提交的 Git
对象与 gitlink。`market-intel` 不属于本工作区 Git 图，因此表中版本是采集时只读查询到的
远端 `main`，不是 `research-workspace` 可恢复的 pin。其生产版本仍应以
`production/market-intel/current` 指向的 release manifest 为准。

当前迁移 worktree 位于分支 `feat/architecture-consolidation`，基线提交为
`f2ffa950bdda2175d01ec3b79856976804f5d0b3`。采集前顶层工作树干净，并跟踪
`github/main`。八个 submodule 均未初始化，`git submodule status --recursive` 中的前导
`-` 是本次基线的一部分，不表示 gitlink 缺失。

## 可恢复版本与职责表

| 仓库 | 当前提交 | Remote 与可见性 | Owner 与入口命令 | 生产方 → 消费方 | 真实数据与凭证 | 回滚方式 |
| --- | --- | --- | --- | --- | --- | --- |
| `research-workspace` | `f2ffa950bdda2175d01ec3b79856976804f5d0b3` | `github` / `origin`: `https://github.com/runchengxie/research-workspace.git`；public；owner `runchengxie` | 跨仓契约、gitlink、doctor 和质量门禁；`python scripts/workspace_doctor.py` | 契约、版本图和运行 manifest → 全部 owner 仓、发布流程和人工审计 | 不保存大型数据、provider/broker 凭证或交易日志；只读取外部 `DATA_PLATFORM_ROOT` | 检出该提交，执行 `git submodule sync --recursive` 和 `git submodule update --init --recursive`；production 回滚则把 `current` 原子切回已知良好 release |
| `market-data-platform` | `0f1c4ce2554ad4961a8f130ce953b5d18ea52a0d`（gitlink） | `origin`: `https://github.com/runchengxie/market-data-platform.git`；private；owner `runchengxie` | 数据资产生产、质量检查、发布和读取；`uv run --locked --extra dev marketdata --help` | current manifest、dataset registry、版本化数据和 research features → 深度学习、alpha、策略应用、pipeline、人工审计 | 使用真实 A 股数据根目录；provider token 和原始数据仅在运行环境，不入 Git | 恢复顶层 gitlink 后运行 submodule update；数据发布回滚使用保留版本及 `current` / `rollback` alias，不改写原始资产 |
| `deep-learning-tick-data-prediction` | `2dd47012487c6fcdb66ef3ca4d4fbf7ca585d203`（gitlink） | `origin`: `https://github.com/runchengxie/deep-learning-tick-data-prediction.git`；public；owner `runchengxie` | L2 事件流审计、训练和预测；`uv run --locked --extra dev python -c 'import ticknet.eventstream; import ticknet.research.prediction_contract'` | L2 预测 artifact → `alpha-research`，再进入组合评估 | 真实 L2 数据、模型 checkpoint 和训练产物在外部数据/运行目录；所需 provider 凭证不入 Git | 恢复对应 gitlink；预测与模型产物按其 commit、数据版本和 receipt 重放，不从 Git 恢复数据本体 |
| `alpha-research` | `631ee150d5125917baebbbb31a673696d1d29230`（gitlink） | `origin`: `https://github.com/runchengxie/alpha-research.git`；public；owner `runchengxie` | 特征、模型、研究评估和信号；`uv run --locked --extra dev python -c 'import alpha_research.cpcv; import alpha_research.signal_artifact'` | `signals.parquet`、metadata 和诊断 → `portfolio-backtester`、`strategy-app`、`strategy-pipeline` | 消费外部真实数据并生成研究 artifact；不保存 provider/broker 凭证 | 恢复对应 gitlink；按 producer commit、数据引用和 artifact envelope 重放信号，旧产物按 receipt 校验 |
| `portfolio-backtester` | `91a4fa4f1d57c074c991546c381a3d90a3b6adfb`（gitlink） | `origin`: `https://github.com/runchengxie/portfolio-backtester.git`；public；owner `runchengxie` | 组合构造、成本、容量、风险和报告；`uv run --locked --extra dev python -c 'import portfolio_backtester.engine; import portfolio_backtester.metrics'` | 持仓、回测和风险 receipt → owner adapter、`strategy-app`、`strategy-pipeline`、人工评审 | 消费真实数据和信号；不持有 provider 或 broker 凭证 | 恢复对应 gitlink；使用保存的输入 hash、配置和持仓 envelope 重放，发布侧回切上一组 workspace release |
| `strategy-research` | `087b5dfdabed70a629ff6ed44fc52609fe966c5f`（gitlink） | `origin`: `https://github.com/runchengxie/strategy-research.git`；private；owner `runchengxie` | 策略身份、投资假设、生命周期和证据导航；`uv run --locked --extra dev python -c 'import style_factors'` | catalog、规格、评审结论和证据导航 → `strategy-app`、`strategy-pipeline`、人工评审 | 保存可审计规格和小型证据，不保存大型真实数据或运行凭证 | 恢复对应 gitlink；策略生命周期按 catalog 和历史证据恢复，不通过移动代码推断状态 |
| `strategy-app` | `f6f58bf7bbd623318189ab4ab7acf49b331be4a2`（gitlink） | `origin`: `https://github.com/runchengxie/strategy-app.git`；private；owner `runchengxie` | 策略专用纯计算和冻结研究合同；`uv run --locked --extra dev python -c 'import strategy_app'` | 策略计算结果和 publication payload → `strategy-pipeline` | 消费真实数据和 owner artifact；不承担生产发布，不保存 provider/broker 凭证 | 恢复对应 gitlink和冻结合同版本；由 pipeline 回切上一 production release，历史 receipt schema 保持可读 |
| `strategy-pipeline` | `87175c67531f0be29f78aeb078046708dbf38ee4`（gitlink） | `origin`: `https://github.com/runchengxie/strategy-pipeline.git`；private；owner `runchengxie` | 运行编排、外部调用、原子发布和 target 交接；`uv run --locked --extra dev strategy --help` | run manifest、DailyWatch20 artifact、`targets.json` → `strategy-research`、`market-intel`、`quant-execution-engine` | 读取真实数据和运行 artifact；provider/外部模型凭证留在运行环境，不入 Git | 恢复对应 gitlink；把 workspace `current` 切回已知良好 release，并重新运行公开 CLI 与日报 smoke |
| `quant-execution-engine` | `2f0675a4b8946ff4134194e7dd12dc1169fd2be0`（gitlink） | `origin`: `https://github.com/runchengxie/quant-execution-engine.git`；public；owner `runchengxie` | 预演、风控、券商执行、对账和审计；`uv run --locked --group dev --extra cli qexec --help` | 订单、对账和 evidence bundle → 操作员与人工审计 | broker 凭证、模拟盘/实盘状态和交易日志只在执行环境；Git 只保存代码与契约 | 恢复对应 gitlink；先恢复 dry-run/paper 配置并核对 `targets.json` hash，真实执行仍需独立门禁和人工确认 |
| `market-intel` | `c8f24a544cdab620080ef45c3c1f174bd4fb94aa`（采集时远端 `main`，非 gitlink） | `origin`: `https://github.com/runchengxie/market-intel.git`；private；owner `runchengxie` | 市场上下文、面向人的报告、Dashboard、飞书投递和运行保障；`market-intel news-heat-export`，以及 production 的 morning/evening/weekly 脚本 | news-heat 输入 → `strategy watchlist20 run`；晨报、晚报和周报 → Dashboard、飞书和人工用户 | 使用真实市场上下文、owner 发布 artifact 和消息投递凭证；凭证留在独立运行环境 | 以 production manifest 确认目标提交，把 `production/market-intel/current` 原子切回保留 release，再同步 Hermes job workdir 并运行报告 smoke |

## 恢复顺序

1. 检出顶层提交 `f2ffa950bdda2175d01ec3b79856976804f5d0b3`。
2. 运行 `git submodule sync --recursive`，再运行 `git submodule update --init --recursive`，恢复表中八个 gitlink。
3. 恢复外部 `DATA_PLATFORM_ROOT` 及其 current manifest、dataset registry、版本化资产和 receipt。Git 提交不能替代这一步。
4. 按数据平台、深度学习、alpha、组合、策略知识、策略应用、pipeline、执行引擎的顺序验证 owner 入口。
5. 单独从 `market-intel` 的 production revision manifest 恢复其 release。远端 `main` 值只证明采集时源码头，不证明当时生产部署版本。

## 基线命令结果

### Git 状态

```text
$ git submodule status --recursive
-631ee150d5125917baebbbb31a673696d1d29230 alpha-research
-2dd47012487c6fcdb66ef3ca4d4fbf7ca585d203 deep-learning-tick-data-prediction
-0f1c4ce2554ad4961a8f130ce953b5d18ea52a0d market-data-platform
-91a4fa4f1d57c074c991546c381a3d90a3b6adfb portfolio-backtester
-2f0675a4b8946ff4134194e7dd12dc1169fd2be0 quant-execution-engine
-f6f58bf7bbd623318189ab4ab7acf49b331be4a2 strategy-app
-87175c67531f0be29f78aeb078046708dbf38ee4 strategy-pipeline
-087b5dfdabed70a629ff6ed44fc52609fe966c5f strategy-research

$ git status --short --branch
## feat/architecture-consolidation...github/main
```

两条命令退出码均为 0。

### Workspace doctor

命令 `python scripts/workspace_doctor.py` 退出码为 1。失败发生在未初始化的子模块所需文件缺失，未修改环境或初始化子模块。错误摘要如下：

```text
[ERROR] submodule-init: market-data-platform is not initialized.
[ERROR] submodule-init: alpha-research is not initialized.
[ERROR] submodule-init: portfolio-backtester is not initialized.
[ERROR] submodule-init: strategy-pipeline is not initialized.
[ERROR] submodule-init: quant-execution-engine is not initialized.
[ERROR] submodule-init: strategy-app is not initialized.
[ERROR] submodule-init: deep-learning-tick-data-prediction is not initialized.
[ERROR] submodule-init: strategy-research is not initialized.
[ERROR] governance-script-lifecycle: Script lifecycle manifest drift: stale=alpha-research/scripts/dev/maintainability_metrics.py, alpha-research/scripts/dev/namespace_boundary.py, alpha-research/scripts/dev/run_tests.sh, market-data-platform/scripts/internal/archive/build_a_share_tushare_sw2021_industry_changes_20260603.py, portfolio-backtester/scripts/dev/maintainability_metrics.py, portfolio-backtester/scripts/dev/namespace_boundary.py, portfolio-backtester/scripts/dev/run_tests.sh, quant-execution-engine/project_tools/__init__.py, quant-execution-engine/project_tools/evidence_offline_chain.py, quant-execution-engine/project_tools/export_repo_source.py, quant-execution-engine/project_tools/package.sh, quant-execution-engine/project_tools/smoke_operator/__init__.py, quant-execution-engine/project_tools/smoke_operator/audit.py, quant-execution-engine/project_tools/smoke_operator/evidence.py, quant-execution-engine/project_tools/smoke_operator/parser.py, quant-execution-engine/project_tools/smoke_operator/state.py, quant-execution-engine/project_tools/smoke_operator/steps.py, quant-execution-engine/project_tools/smoke_operator/workflow.py, quant-execution-engine/project_tools/smoke_operator_harness.py, quant-execution-engine/project_tools/smoke_signal_harness.py, quant-execution-engine/project_tools/smoke_target_harness.py, strategy-research/src/style_factors/style_factor_attribution.py
[ERROR] governance-compatibility-facades: Compatibility facade governance drift: submodule source files are missing because all eight submodules are uninitialized.
[ERROR] governance-quality: Quality exclude register drift: Missing alpha-research/pyproject.toml; Missing market-data-platform/pyproject.toml; Missing portfolio-backtester/pyproject.toml; Missing quant-execution-engine/pyproject.toml; Missing strategy-app/pyproject.toml; Missing strategy-pipeline/pyproject.toml
[ERROR] governance-quality: Per-file ignore register drift: Missing alpha-research/pyproject.toml; Missing market-data-platform/pyproject.toml; Missing portfolio-backtester/pyproject.toml; Missing quant-execution-engine/pyproject.toml; Missing strategy-app/pyproject.toml; Missing strategy-pipeline/pyproject.toml
Summary: errors=12 warnings=4
```

`governance-compatibility-facades` 的完整原始行列出 40 个缺失或 stale 的子模块源码路径；共同原因是子模块未初始化。为避免在基线文档中维护第二份路径清单，本记录保留检查项、原因和命令汇总，精确路径可通过同一提交重跑该命令恢复。

### 契约 smoke

命令 `python src/research_contracts/smoke_contracts.py` 退出码为 1。原始失败如下：

```text
[ERROR] artifact contract manifest: signals.parquet: missing entrypoint path alpha-research/src/alpha_research/signal_artifact.py; signals.meta.json: missing entrypoint path alpha-research/src/alpha_research/signal_artifact.py; positions_by_rebalance.csv: missing entrypoint path portfolio-backtester/src/portfolio_backtester/contracts.py; targets.json: missing entrypoint path strategy-pipeline/src/strategy_pipeline/control_plane/targets.py; targets.json: missing entrypoint path quant-execution-engine/src/quant_execution_engine/targets.py; targets.json: missing entrypoint path quant-execution-engine/src/quant_execution_engine/targets.py; watchlist_20.csv: missing entrypoint path strategy-app/src/strategy_app/daily_watch20/pipeline_publication.py; selection_receipt.json: missing entrypoint path strategy-app/src/strategy_app/daily_watch20/pipeline_publication.py; label_events.parquet: missing entrypoint path alpha-research/src/alpha_research/event_labeling.py; sample_weights.parquet: missing entrypoint path alpha-research/src/alpha_research/sample_weighting.py; sample_weights.receipt.json: missing entrypoint path alpha-research/src/alpha_research/sample_weighting.py; research_features.parquet: missing entrypoint path market-data-platform/src/market_data_platform/research_features.py; research_features.parquet: missing entrypoint path market-data-platform/src/market_data_platform/cli_research_features.py; sizing_receipt.json: missing entrypoint path portfolio-backtester/src/portfolio_backtester/evidence_receipts.py; sizing_receipt.json: missing entrypoint path portfolio-backtester/src/portfolio_backtester/afml_evidence.py; strategy_risk_report.json: missing entrypoint path portfolio-backtester/src/portfolio_backtester/strategy_risk.py; strategy_risk_report.json: missing entrypoint path portfolio-backtester/src/portfolio_backtester/afml_evidence.py; hrp_receipt.json: missing entrypoint path portfolio-backtester/src/portfolio_backtester/hrp.py; hrp_receipt.json: missing entrypoint path portfolio-backtester/src/portfolio_backtester/afml_evidence.py; afml_evidence_fragment.json: missing entrypoint path portfolio-backtester/src/portfolio_backtester/afml_evidence.py; research_protocol_report.json: missing entrypoint path alpha-research/src/alpha_research/research_protocols.py; execution_policy_receipt.json: missing entrypoint path quant-execution-engine/src/quant_execution_engine/execution_policy.py; handoff_audit_report.json: missing entrypoint path quant-execution-engine/src/quant_execution_engine/handoff_audit.py
[WARN] marketdata: marketdata CLI is unavailable
[WARN] strategy-pipeline export-targets help: public strategy-pipeline CLI is unavailable
[WARN] qexec rebalance help: qexec CLI is unavailable
Summary: errors=1 warnings=3
```

### 提交检查

命令 `python scripts/run_workspace_tests.py` 退出码为 1。精确失败为：

```text
WorkspaceSourceError: workspace integration tests require initialized source trees: market-data-platform/src, alpha-research/src, portfolio-backtester/src, strategy-app/src, strategy-pipeline/src
```

命令 `python scripts/run_quality_checks.py --profile hard` 退出码为 1。Ruff、格式、`ty`、
workspace architecture 和 secret scan 通过；以下 runner 项因未初始化的子模块源码失败：

```text
[ERROR] workspace-import-boundaries: /usr/bin/python <worktree>/scripts/workspace_import_boundaries.py --check
[ERROR] workspace-ownership-boundaries: /usr/bin/python <worktree>/scripts/workspace_ownership_boundaries.py --check
[ERROR] research-capability-registry: /usr/bin/python -m src.research_contracts.research_capability_registry
[ERROR] trial-ledger: /usr/bin/python <worktree>/strategy-research/tools/scripts/trial_ledger_check.py
```

其中 import/ownership 检查报告对应 owner 源码目录 `missing_source`；capability registry
报告 `strategy-research`、`alpha-research` 和 `portfolio-backtester` 的 source/evidence path 不存在；
trial ledger 的精确失败为：

```text
/usr/bin/python: can't open file '<worktree>/strategy-research/tools/scripts/trial_ledger_check.py': [Errno 2] No such file or directory
```

`<worktree>` 代表本记录开头指定的迁移 worktree，避免把机器绝对路径写入版本化证据。

## 事实来源与限制

- 版本与 remote：`git rev-parse HEAD`、`git ls-tree HEAD`、`.gitmodules` 和 `git remote -v`。
- 可见性：`docs/quality-governance.md`；`market-intel` 另以 `gh repo view` 只读确认。
- Owner、入口和交接：`AGENTS.md`、`ARCHITECTURE.md`、`scripts/submodule_checks.json`、`docs/contracts.md` 和 `docs/artifact-contracts.yml`。
- 数据、凭证和回滚：`README.md`、`.env.example`、`docs/bootstrap.md`、`docs/production-update.md` 和 `docs/market-intel-owner-boundary.md`。
- `market-intel` remote `main`：`git ls-remote https://github.com/runchengxie/market-intel.git HEAD refs/heads/main`。
- 本任务没有读取或修改主工作树、外部 submodule 工作树或 production release。没有初始化当前 worktree 的 submodule，因此无法把 owner 仓的工作树 dirty 状态加入本记录；可恢复事实是各 gitlink 和未初始化状态。
