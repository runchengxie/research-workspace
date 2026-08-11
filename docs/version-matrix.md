# 版本矩阵

本页记录工作区版本组合。真正锁定版本的是 Git 子模块指针。本页只保存当前检出状态和人工验证结论。

## 当前检出状态

先用脚本生成当前状态：

```bash
python scripts/print_version_matrix.py
```

不要手工维护当前输出的静态表。提交后它会立即变旧。需要现场状态时运行脚本，
需要可审计状态时看下方已验证组合。

如果脚本报告 `not initialized`，先运行：

```bash
git submodule update --init --recursive
```

普通 zip 或 source 快照没有 `.git` 元数据，不能生成 commit matrix。这种场景只适合阅读顶层文档，不能作为版本锁定或完整链接测试依据。

## 已验证组合

`framework-adapters-2026-07` 已标记为终止的历史候选。相关候选没有形成当前 owner-native
`main` 上可验证的发布组合。历史清单见
[framework-adapter-release.yml](framework-adapter-release.yml)，当前功能状态见
[framework-support-matrix.md](framework-support-matrix.md)。

| 日期 | 顶层仓库提交 | market-data-platform | alpha-research | portfolio-backtester | research-apps | strategy-pipeline | quant-execution-engine | 验证状态 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-08-11 | 本次提交 | `127897e` | `9003743` | `fc6a5d6` | `519fec3` | `ded1df5` | `bfe1ab2` | D11-H5 升级为五个互斥 4 股子组合，完整目标固定 20 只等权。每日仅刷新一个子组合，单日最多替换 4 只。消费端兼容读取 v1，生产发布切换到 v2 | strategy-app PR #9/#10 全门禁通过。strategy-pipeline PR #45 的 1171 项 fast tests、lint、format、typecheck 和 maintainability 通过。真实 2026-08-10→2026-08-11 隔离回放得到 20 只、单股 5%、本次 2 进 2 出、单边换手 10%。 |
| 2026-08-04 | `53286e4` | `351e097` | `3dbc124` | `23f883e` | `e14be1f` | `d470c64` | `bfe1ab2` | 完成日频清洗内存优化、D11-H5 研究影子发布入口、可移植复现包、可选 TuShare 分钟包和正式年度风格图。六个子模块均只保留 `main`，本地与远端已同步 | market-data-platform 完整门禁 702 项测试通过。strategy-pipeline 完整门禁 1194 项通过、1 项跳过，隔离 wheel 验证 281 个模块和 6 个 owner pin。顶层质量门禁、密钥扫描和 227 项测试通过。 |
| 2026-07-28 | `05361c2` | `6a72435` | `91726a7` | `a596b8c` | `51ec0c0` | `96328e5` | `0cb17c1` | 六个子模块同步至各仓 `main` 的最新重构提交：TuShare 原生分钟数据基线、daily-watch20 复杂度预算保持、策略管线 CLI 拆包、执行引擎 smoke harness 拆包、组合回测错峰目标预算保持、研究应用去重 shim。顶层 gitlink 随之更新 | 顶层 `178 passed`、hard quality gate、命名空间契约、契约 smoke 与 workspace doctor（errors=0，3 个既有且预算内 warning）通过。`docs/evidence/maintainability/baseline-20260719-ty.json` |
| 2026-07-28 | `de9bb09` | `20ab25b` | `22e16b0` | `37995d0` | `0bccff2` | `4d07453` | `abe6f89` | 六个子模块完成模块拆分（re-export 外壳 + _api/_core 或 _partNN 单元），导入与隔离 wheel smoke 全绿。strategy-pipeline 修复拆分引入的循环导入、CLI `__main__` guard 与 monkeypatch 测试目标。复杂度预算随拆分下降，ratchet 基线同步下调。顶层 gitlink 随之更新 | 各子模块 delegated full profile 通过。strategy-pipeline 隔离 wheel smoke 270 模块、5 个 owner pin 已验证。顶层 hard quality gate、workspace doctor 与契约 smoke 通过。`docs/evidence/maintainability/baseline-20260719-ty.json` |
| 2026-07-20 | `781195a` | `79b63a0` | `b06760d` | `b2f5c2c` | `cdf35e2` | `7727535` | `30a4703` | DailyWatch20 生产候选池统一升级为 `ths_hot_strict_v2`：前 20 名完整、20 名后最多一个缺口、无并列或重复，保留原始排名且禁止全市场补股。真实 20260717 源记录 `missing_ranks=[53]`、`rank_coverage_status=degraded`，下游依赖 pin 已级联并推送 | 顶层 `177 passed`、hard quality、命名空间、7 项契约 smoke 与 workspace doctor（0 error，3 个既有且预算内 warning）通过。市场数据平台（MDP） `654 passed, 1 skipped`，alpha `248 passed`，research-apps `109 passed`，Strategy `1092 passed, 1 skipped`，隔离 wheel 205 模块和 5 个 owner pin。真实 504 日隔离重放生成 A4+B16，正涨池 40、eligible 交集 36，选中原始 rank 54 且无 rank 53。10:55 的正式补发被 `09:15` 发布窗正确拒绝，canonical 未被越权改写。market-intel `70f77aa` 的根仓 627 项测试及 strict-v2 client/freshness 门禁通过。`docs/evidence/maintainability/baseline-20260719-ty.json` |
| 2026-07-20 | `150391a` | `7ee07ba` | `d9af097` | `b2f5c2c` | `8e1eb7a` | `b8a45cc` | `30a4703` | 数据平台配额 correctness 与质量重构已收口。alpha、research-apps 和 Strategy 的 Git 依赖统一到已验证的最新 `main`，六个子模块提交均已推送并与远端 `main` 同步 | 顶层 `177 passed`、hard quality gate、命名空间契约、契约 smoke 和 workspace doctor 通过。market-data `651 passed, 1 skipped`。alpha `248 passed`。research-apps `109 passed`，隔离 wheel smoke 通过。Strategy `1081 passed, 1 skipped`，隔离 wheel 验证 205 个模块和 5 个 owner pin。未变更的 portfolio 与 qexec 沿用同提交的 2026-07-19 门禁证据。`docs/evidence/maintainability/baseline-20260719-ty.json` |
| 2026-07-19 | `603073c` | `1f97002` | `445debd` | `b2f5c2c` | `afc9a2e` | `b3d1b20` | `30a4703` | 数据平台新增共享配额的手动日间分钟补数入口。六个子模块提交均已推送并与远端 `main` 同步 | 顶层 `177 passed`、hard quality gate 和 workspace doctor 通过。market-data `622 passed, 1 skipped`。alpha `248 passed`。portfolio `313 passed`。research-apps `109 passed`。Strategy `1081 passed, 1 skipped`。qexec 单元门禁 `254 passed, 2 skipped`，扩展档位 `17 passed, 3 skipped`。`docs/evidence/maintainability/baseline-20260719-ty.json` |
| 2026-07-19 | `f282763` | `dffb15f` | `445debd` | `b2f5c2c` | `afc9a2e` | `b3d1b20` | `30a4703` | 活跃类型门禁统一为 `ty`。六个子模块迁移提交已推送并与远端 `main` 同步。MDP 工作区另有三项未纳入本组合的 systemd 改动，已原样保留 | 顶层 clean-clone `177 passed` 和 hard quality gate。market-data `621 passed, 1 skipped`。alpha `248 passed`。portfolio `313 passed`。research-apps `109 passed`。Strategy `1081 passed, 1 skipped`，并完成 205 模块隔离 wheel 安装。qexec 单元门禁 `254 passed, 2 skipped`，扩展档位 `17 passed, 3 skipped`。`docs/evidence/maintainability/baseline-20260719-ty.json` |
| 2026-07-19 | `86d2a2d` | `fbc7fe0` | `c6d49f8` | `e6af7b9` | `461d202` | `a32dbe6` | `1f07ba0` | 六个子模块的文档、框架支持状态和本地门禁已复核。所有仓库只保留本地 `main`，子模块提交已推送并与远端同步 | 顶层 `178 passed` 和 hard quality gate 通过。market-data `622 passed, 1 skipped`。alpha `247 passed`。portfolio `312 passed`。research-apps `109 passed`。Strategy `1090 passed, 1 skipped`，并完成 205 模块隔离 wheel 安装。qexec 单元门禁 `253 passed, 2 skipped`，扩展档位 `17 passed, 3 skipped`。`docs/framework-support-matrix.md`。`docs/evidence/maintainability/baseline-20260719.json` |
| 2026-07-19 | `c945ac8` | `ea29fed` | `6c739f0` | `4296018` | `f34ad95` | `8d29531` | `0735df6` | 六个子模块均只保留 `main`，本地与远端同步。GitHub Actions 已禁用，以本地 pre-push/full gate 为发布门禁 | 顶层 `176 passed`。六个子模块 delegated full profile 共 `36` 条命令通过。`docs/research-app-ownership-ledger.yml`。ADR-0004。`docs/evidence/maintainability/baseline-20260714.json` |
| 2026-06-28 | `945ce43` | `f606f86` | `7af023f` | `7495902` | n/a | `91b4e0e` | `0617076` | 阶段 3 边界加固组合：产物（artifact）契约、外部策略 backtester smoke、alpha 无 backtester smoke、strategy-pipeline 本地 alpha/backtesting source 防回流、`export-targets` 执行隔离、策略卫星五段链路文档均已收口。顶层 workspace 测试和 hard quality gate 通过 | `uv run --with pytest python -m pytest tests -q` (`66 passed`)。`python scripts/run_quality_checks.py --profile hard`。`python scripts/workspace_doctor.py` (`errors=0 warnings=1`)。GitHub CodeQL `28325877208` |
| 2026-06-27 | stage-3 split branch local checkout | `fce11ef` | `c694b08` | `e05bde7` | n/a | `dd8d14f` | `00cfced` | `alpha-research` 和 `portfolio-backtester` 已拆为 workspace 子模块。新子模块 lint/type/import smoke 通过。`strategy-pipeline` 保留编排层并通过 lint/type/fast tests。顶层 workspace 测试和子模块检查通过。跨仓库 GitHub Actions 引导已补齐 split package checkout，并使用两个新私有仓库的只读部署 keys。跨仓库拉取请求（PR）已合并到 main | `python scripts/run_submodule_checks.py --profile full --submodule alpha-research --submodule portfolio-backtester`。`scripts/dev/run_tests.sh fast` in `strategy-pipeline`。`uv run --with pytest python -m pytest tests -q` |
| 2026-06-13 | `hk-freeze-20260613` -> `8d2f5fd` | `hk-freeze-20260613` -> `e802f12` | n/a | n/a | n/a | `hk-freeze-20260613` -> `b6e4cad` | `hk-freeze-20260613` -> `dc520cf` | 港股恢复专用 freeze tag 已推送。私有 legacy archive 暂存已从该 tag 组合重建并通过 gate。`hk-research-workspace-archive` 已创建为私有恢复专用 superproject。删除评审仍因审计等待而阻塞 | `docs/evidence/hk-private-archive-stage-20260613.json`。`docs/evidence/hk-research-workspace-archive-20260613.json`。`python scripts/hk_archive_gate.py --check --export-manifest /tmp/hk-quant-legacy-archive-export-20260613/archive-export-manifest.json --format json` |
| 2026-05-27 | `f38ce4c` | `a310a80` | n/a | n/a | n/a | `10ca23f` | `85ad0e7` | 部分验证 | 已验证研究系统导出目标持仓文件，以及执行引擎解析文件并生成离线调仓计划。模拟盘持续联调证据仍需补齐 |

## 更新方法

生成当前版本矩阵：

```bash
python scripts/print_version_matrix.py
```

然后根据实际验证结果填写：

- 是否只验证了解析或预演流程。
- 是否验证了模拟盘端到端流程。
- 是否涉及实盘。实盘状态只能按人工监督下的真实结果填写。
- 子模块是否存在未提交改动。如存在，请标为本地工作状态，发布前先清理或提交。

## Owner-native 命名空间已合并组合

| 日期 | alpha-research | portfolio-backtester | strategy-pipeline | 状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| 2026-07-14 | `a5cfede` / 0.2.0 | `329f1fa` / 0.2.0 | `d0eb474` / 1.1.0 | 已合并并验证：实现全部位于 owner-native package。活跃 smoke、文档、runtime module 和 canonical 命令行（CLI）已切换到 owner 入口。`cstree` 仅由 strategy 在 1.x 提供限期兼容门面（facade）。alpha 215、portfolio 197、strategy 735（另 1 skipped）项测试通过，workspace 边界、hard quality 与 doctor 通过 | `docs/owner-native-namespace-release.json`、`docs/evidence/owner-native-namespace-integration-20260714.json`、ADR-0002、PR #6/#8/#20 |
| 2026-07-14 | `d8657fd` / 0.3.0 | `fb8fcc7` / 0.3.0 | `bdb9ff3` / 2.0.0 | workspace 2.0 已发布：删除 1.x 共享命名空间门面、旧 CLI 与环境变量兜底。运行时 logger、产物契约和活跃脚本统一为 owner-native 名称。三个仓库均完成 full gate、推送并与远端 `main` 同步。 | `docs/owner-native-namespace-release.json`、ADR-0002 |
