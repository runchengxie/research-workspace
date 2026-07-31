# 子模块 noqa 清债计划

本计划处理六个子模块里 `# noqa` 注释的分布问题。2026-07-31 复核发现，此前列报的 noqa 总量（如 alpha-research 4244 条）几乎全部来自各子模块的 `.venv` 第三方包，并非项目自有代码。排除 `.venv`/`build`/`artifacts` 后，六个子模块自有代码实际只有约 1100 处 `# noqa`，且 1036 处集中在 `market-data-platform`。顶层工作区自身有 3 处 `# noqa`，门禁有效。子模块自有代码的 noqa 不多，但 `market-data-platform` 的 `F401` 偏多，可借清理顺带发现未使用导入与潜在 dead code。

## 与现有治理文件的关系

本计划与以下文件互补，不重叠：

- `maintainability-refactor-roadmap.yml`：用 ratchet-only 预算管体量热点（大文件、长函数、复杂度）。本计划不管体量，只清 `# noqa` 压制的 lint 告警。
- `submodule-refactor-plan.md` 与 `code-size-review.md`：管子模块巨型文件拆分，是 roadmap 文件拆分的落地设计。本计划不拆分文件。

两者是不同维度。本计划清理后若某文件因移除 dead import 而跌破大文件阈值，按 roadmap 规则在同一次提交下调对应 budget，不在本计划预改 roadmap 数字。

## 现状数据

各子模块自有代码 `# noqa` 真实数量（排除 `.venv`/`build`/`artifacts`，`find` + `grep` 实测，2026-07-31）：

| 子模块 | `# noqa` 真实量 | 主要规则 | 预推送门禁命令来源 |
| --- | --- | --- | --- |
| `market-data-platform` | 1036 | `F401`(951)、`PLR0913`(53)、`PLR0915`(10) | `scripts/submodule_checks.json` 的 `full` profile |
| `strategy-pipeline` | 38 | `F403`(35) | 仓库 `scripts/dev/run_tests.sh` |
| `alpha-research` | 9 | `RUF002`(5)、`F403`(2) | `scripts/submodule_checks.json` 的 `full` profile |
| `quant-execution-engine` | 10 | `E402`(6)、`F403`(2) | 同左 |
| `portfolio-backtester` | 7 | `F403`(3)、`F401`(3) | 同左 |
| `research-apps` | 0 | 无 | 仓库自有 `scripts/dev/check.py` |

规则类别分布（仅自有代码，排除 `.venv`）：

- `F401` 未使用导入：主要来自 `market-data-platform`（951），其余子模块极少。
- `F403` 星号导入：`strategy-pipeline`（35）、`alpha-research`（2）、`quant-execution-engine`（2）、`portfolio-backtester`（3）。
- `PLR0913`/`PLR0915` 参数/分支过多：`market-data-platform`（53+10），属设计类告警。
- `E402` 模块级导入不在文件顶部：`quant-execution-engine`（6，多为测试/脚本引导）。
- `RUF002` 非 ASCII 名称无备注：`alpha-research`（5）。

## 关键发现：此前列报被 `.venv` 夸大

初版计划用 `grep -rc 'noqa' <子模块>` 统计，把每个子模块 `.venv` 里第三方包（pluggy、pygments、`_pytest`、packaging 等）的大量 `# noqa` 也算进项目代码，得出 alpha-research 4244、research-apps 3108 等数字。排除 `.venv` 后，真实自有代码仅约 1100 处，且 `market-data-platform` 占九成以上。

因此原先"子模块底层几乎全靠 `# noqa` 压制门禁、新人不敢改"的判断不成立。子模块自有代码基本没有被 `# noqa` 淹没，门禁在子模块层是有效的。真正的 noqa 集中在 `market-data-platform` 的 `F401`，清债价值在于顺带暴露未使用导入与潜在 dead code，而非恢复门禁能力。

所有子模块 `pyproject.toml` 的 `select` 都没有启用 pydocstyle（D 类），但自有代码里也几乎没有 D 类 `# noqa`（初版看到的 D102/D205/D107 全部来自 `.venv`）。所以本计划不存在"幽灵债务批量删注释"的空间，几乎每条 noqa 都对应真实启用的规则。

## 清债三原则

1. 分批推进，每批只动一个子模块的一个规则类别，配套运行该子模块测试，避免一次性大改动难以回滚。
2. 先机械可修（`F401` 未使用导入），再处理需人工判断的（`F403` 星号导入、`PLR0913` 参数过多、`E402` 导入位置）。
3. 每批清理后必须让该子模块的预推送 `full` profile 通过，再提交。不要跳过仓库原有门禁。

## 规则分类与处理方式

### 第一类：机械可修（工具自动修，需复核）

- `F401` 未使用导入：ruff 自带 `--fix` 可移除。移除前要确认不是 re-export（有些 `__init__.py` 故意导出供外部 import）。对 `src/*/__init__.py` 的 `F401` 需人工核对再删。集中在 `market-data-platform`（951 条）。
- `E501` 行过长：优先用 `ruff format` 自动折行。当前自有代码里此类极少，只在 `.venv` 出现，项目代码无需处理。

### 第二类：需人工判断（逐文件处理，谨慎解除）

- `F403` 星号导入：改为显式导入列表，或保留并登记 `per-file-ignores`（参考 `quant-execution-engine` 的做法，写清原因和移除条件）。集中在 `strategy-pipeline`（35 条）。
- `PLR0913`/`PLR0915` 参数/分支过多：属于设计问题，不在清债范围，只处理对应的 `# noqa`，让告警浮现，后续单独做函数拆分。集中在 `market-data-platform`（63 条）。
- `E402` 模块级导入不在文件顶部：多为测试/脚本引导，确认后保留并登记 `per-file-ignores`。集中在 `quant-execution-engine`（6 条）。
- `RUF002` 非 ASCII 名称无备注：按仓库规范补备注或改名，集中在 `alpha-research`（5 条）。

## 分批路线

按工作量从大到小排序，聚焦真正有量的两个子模块。

### 批次 1：market-data-platform（1036 条，主战场）

- 先清 `F401`（951）：在子模块内运行 `uv run --locked ruff check --fix --select F401 .`，逐文件复核不是 re-export 后再提交。顺带暴露未使用导入与潜在 dead code，单独开清理提交。
- 再处理 `PLR0913`/`PLR0915`（63）：只解除 `# noqa` 让告警浮现，不在此批做函数拆分，拆分归 roadmap 设计类工作。
- 验证：`uv run --locked ruff check .` 与 `scripts/dev/check.py` 通过，跑该仓测试套件。

### 批次 2：strategy-pipeline（38 条）

- `F403`（35）星号导入：逐文件改为显式导入列表，对不便改的登记 `per-file-ignores`。
- 验证：仓库 `scripts/dev/run_tests.sh full` 通过。

### 批次 3：其余小量（alpha-research 9、quant-execution-engine 10、portfolio-backtester 7、research-apps 0）

- 合并处理：`RUF002`（alpha 5）补备注、`E402`（qexec 6）登记 `per-file-ignores`、`F403`/`F401` 零星项逐文件处理。
- 这些子模块量极小，可一次提交清完，不必单独排期。

## 与预推送门禁衔接

各子模块推送时运行 `scripts/submodule_checks.json` 登记的 `full` profile。清理过程中：

- 每批提交前在子模块内运行其 `full` profile 对应的命令（`uv run --locked ruff check .` 等），确保不引入新告警。
- 若清理导致某文件 `F401` 移除后暴露真正 dead code，单独开一个清理提交，不要混入门禁修复。
- `quant-execution-engine` 的 `per-file-ignores` 模式应作为其他子模块的范本：对确需保留的忽略项，登记原因、负责人和移除条件，避免散落 `# noqa`。

## 验证与回滚

- 每批用 `git diff --stat` 确认改动文件数可控，单批不超过一个子模块的一个规则类别。
- 清理后运行该子模块测试套件（命令见各子模块 `scripts/dev/` 或 `submodule_checks.json`）。
- 若 ruff 行为异常，单文件 `git checkout` 回滚，不整体 revert。
- 批次 1 完成后跑一次顶层 `python scripts/run_quality_checks.py --profile hard` 确认顶层不受影响。

## 不建议做的事

- 不要一次性全局删除所有 `# noqa`，会混入真实问题且难以 review。
- 不要为降低数量而扩大 `ignore` 或 `per-file-ignores` 的覆盖面，那只是把债藏得更深。
- 不要把 `PLR0913`/`C901` 等设计类告警用 `# noqa` 压回去，它们的浮现是清理的目的之一。
- 不要在未运行子模块测试的情况下提交清理结果。

## 进度记录

| 批次 | 子模块 | 规则类别 | 状态 | 削减条数 |
| --- | --- | --- | --- | --- |
| 1 | market-data-platform | F401/PLR0913 | 待开始 | |
| 2 | strategy-pipeline | F403 | 待开始 | |
| 3 | alpha-research / quant-execution-engine / portfolio-backtester / research-apps | RUF002/E402/F403/F401 | 待开始 | |
